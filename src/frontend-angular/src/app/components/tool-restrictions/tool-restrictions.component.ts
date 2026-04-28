/**
 * Tool Restrictions Component (ADR-057)
 *
 * Allows configuration of security-based tool restrictions for Use Cases.
 * Supports preset configurations and custom fine-grained control.
 */

import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  DataFlowDirection,
  DataSourceType,
  MaxDataSensitivity,
  NetworkAccessLevel,
  TOOL_RESTRICTION_PRESETS,
  ToolRestrictionPreset,
  ToolRestrictions,
} from '../../api/models/use-case-management.models';

@Component({
  selector: 'app-tool-restrictions',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatCheckboxModule,
    MatChipsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTooltipModule,
  ],
  templateUrl: './tool-restrictions.component.html',
  styleUrls: ['./tool-restrictions.component.scss'],
})
export class ToolRestrictionsComponent implements OnChanges {
  @Input() restrictions: ToolRestrictions | null = null;
  @Input() disabled = false;
  @Output() restrictionsChange = new EventEmitter<ToolRestrictions | null>();

  // State
  enabled = false;
  selectedPreset: ToolRestrictionPreset | 'none' = 'none';

  // Custom configuration state
  allowedDataSources = new Set<DataSourceType>(['internal', 'none']);
  allowedDataFlows = new Set<DataFlowDirection>(['ingress', 'none']);
  allowedNetworkLevels = new Set<NetworkAccessLevel>(['isolated', 'internal']);
  requiredSensitivity: MaxDataSensitivity = 'internal';

  // Options for selects
  dataSourceOptions: { value: DataSourceType; label: string; icon: string }[] =
    [
      { value: 'internal', label: 'Internal', icon: 'business' },
      { value: 'external', label: 'External', icon: 'public' },
      { value: 'none', label: 'None', icon: 'block' },
      { value: 'mixed', label: 'Mixed', icon: 'merge_type' },
    ];

  dataFlowOptions: {
    value: DataFlowDirection;
    label: string;
    icon: string;
  }[] = [
    { value: 'ingress', label: 'Ingress', icon: 'arrow_downward' },
    { value: 'egress', label: 'Egress', icon: 'arrow_upward' },
    { value: 'bidirectional', label: 'Bidirectional', icon: 'swap_vert' },
    { value: 'none', label: 'None', icon: 'block' },
  ];

  networkOptions: { value: NetworkAccessLevel; label: string; icon: string }[] =
    [
      { value: 'isolated', label: 'Isolated', icon: 'lock' },
      { value: 'internal', label: 'Internal', icon: 'vpn_key' },
      { value: 'external', label: 'External', icon: 'language' },
    ];

  sensitivityOptions: {
    value: MaxDataSensitivity;
    label: string;
    color: string;
  }[] = [
    { value: 'public', label: 'Public', color: '#9e9e9e' },
    { value: 'internal', label: 'Internal', color: '#2196f3' },
    { value: 'confidential', label: 'Confidential', color: '#ff9800' },
    { value: 'restricted', label: 'Restricted (PII)', color: '#f44336' },
  ];

  presets = TOOL_RESTRICTION_PRESETS;
  presetKeys = Object.keys(
    TOOL_RESTRICTION_PRESETS
  ) as (keyof typeof TOOL_RESTRICTION_PRESETS)[];

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['restrictions']) {
      this.loadRestrictions(this.restrictions);
    }
  }

  private loadRestrictions(restrictions: ToolRestrictions | null): void {
    if (!restrictions) {
      this.enabled = false;
      this.selectedPreset = 'none';
      this.resetToDefaults();
      return;
    }

    this.enabled = true;

    // Check if matches a preset
    const matchedPreset = this.findMatchingPreset(restrictions);
    if (matchedPreset) {
      this.selectedPreset = matchedPreset;
    } else {
      this.selectedPreset = 'custom';
    }

    // Load custom values
    this.allowedDataSources = new Set(restrictions.allowed_data_sources);
    this.allowedDataFlows = new Set(restrictions.allowed_data_flows);
    this.allowedNetworkLevels = new Set(restrictions.allowed_network_levels);
    this.requiredSensitivity = restrictions.required_data_sensitivity;
  }

  private findMatchingPreset(
    restrictions: ToolRestrictions
  ): keyof typeof TOOL_RESTRICTION_PRESETS | null {
    for (const key of this.presetKeys) {
      const preset = this.presets[key].restrictions;
      if (
        this.arraysEqual(
          restrictions.allowed_data_sources,
          preset.allowed_data_sources
        ) &&
        this.arraysEqual(
          restrictions.allowed_data_flows,
          preset.allowed_data_flows
        ) &&
        this.arraysEqual(
          restrictions.allowed_network_levels,
          preset.allowed_network_levels
        ) &&
        restrictions.required_data_sensitivity ===
          preset.required_data_sensitivity
      ) {
        return key;
      }
    }
    return null;
  }

  private arraysEqual<T>(a: T[], b: T[]): boolean {
    if (a.length !== b.length) return false;
    const sortedA = [...a].sort();
    const sortedB = [...b].sort();
    return sortedA.every((val, i) => val === sortedB[i]);
  }

  private resetToDefaults(): void {
    this.allowedDataSources = new Set(['internal', 'none']);
    this.allowedDataFlows = new Set(['ingress', 'none']);
    this.allowedNetworkLevels = new Set(['isolated', 'internal']);
    this.requiredSensitivity = 'internal';
  }

  onEnabledChange(): void {
    if (!this.enabled) {
      this.restrictionsChange.emit(null);
    } else {
      this.emitCurrentRestrictions();
    }
  }

  onPresetChange(): void {
    if (this.selectedPreset === 'none') {
      this.enabled = false;
      this.restrictionsChange.emit(null);
      return;
    }

    if (this.selectedPreset === 'custom') {
      // Keep current values, just switch to custom mode
      return;
    }

    // Apply preset
    const preset =
      this.presets[this.selectedPreset as keyof typeof TOOL_RESTRICTION_PRESETS]
        .restrictions;
    this.allowedDataSources = new Set(preset.allowed_data_sources);
    this.allowedDataFlows = new Set(preset.allowed_data_flows);
    this.allowedNetworkLevels = new Set(preset.allowed_network_levels);
    this.requiredSensitivity = preset.required_data_sensitivity;

    this.emitCurrentRestrictions();
  }

  toggleDataSource(source: DataSourceType): void {
    if (this.allowedDataSources.has(source)) {
      this.allowedDataSources.delete(source);
    } else {
      this.allowedDataSources.add(source);
    }
    this.selectedPreset = 'custom';
    this.emitCurrentRestrictions();
  }

  toggleDataFlow(flow: DataFlowDirection): void {
    if (this.allowedDataFlows.has(flow)) {
      this.allowedDataFlows.delete(flow);
    } else {
      this.allowedDataFlows.add(flow);
    }
    this.selectedPreset = 'custom';
    this.emitCurrentRestrictions();
  }

  toggleNetworkLevel(level: NetworkAccessLevel): void {
    if (this.allowedNetworkLevels.has(level)) {
      this.allowedNetworkLevels.delete(level);
    } else {
      this.allowedNetworkLevels.add(level);
    }
    this.selectedPreset = 'custom';
    this.emitCurrentRestrictions();
  }

  onSensitivityChange(): void {
    this.selectedPreset = 'custom';
    this.emitCurrentRestrictions();
  }

  private emitCurrentRestrictions(): void {
    const restrictions: ToolRestrictions = {
      allowed_data_sources: Array.from(this.allowedDataSources),
      allowed_data_flows: Array.from(this.allowedDataFlows),
      allowed_network_levels: Array.from(this.allowedNetworkLevels),
      required_data_sensitivity: this.requiredSensitivity,
    };
    this.restrictionsChange.emit(restrictions);
  }

  isDataSourceSelected(source: DataSourceType): boolean {
    return this.allowedDataSources.has(source);
  }

  isDataFlowSelected(flow: DataFlowDirection): boolean {
    return this.allowedDataFlows.has(flow);
  }

  isNetworkLevelSelected(level: NetworkAccessLevel): boolean {
    return this.allowedNetworkLevels.has(level);
  }
}
