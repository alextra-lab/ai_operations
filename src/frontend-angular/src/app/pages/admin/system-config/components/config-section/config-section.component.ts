/**
 * Configuration Section Component
 *
 * Expandable panel for a single configuration section.
 * Contains ConfigEditorComponent for editing.
 */

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { LucideAngularModule } from 'lucide-angular';
import {
  ConfigSection,
  ConfigSectionMetadata,
} from '../../models/system-config.models';
import { SystemConfigService } from '../../services/system-config.service';
import { ConfigEditorComponent } from '../config-editor/config-editor.component';

@Component({
  selector: 'app-config-section',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatExpansionModule,
    MatProgressSpinnerModule,
    ConfigEditorComponent,
  ],
  templateUrl: './config-section.component.html',
  styleUrls: ['./config-section.component.scss'],
})
export class ConfigSectionComponent implements OnInit {
  @Input() section!: ConfigSection;
  @Input() metadata!: ConfigSectionMetadata;
  @Input() config: Record<string, unknown> | null = null;
  @Output() configChange = new EventEmitter<Record<string, unknown>>();

  isExpanded = false;
  isLoading = false;
  error: string | null = null;

  constructor(private configService: SystemConfigService) {}

  ngOnInit(): void {
    // Configuration is passed from parent
  }

  /**
   * Handle configuration change from editor
   */
  onConfigChange(newConfig: Record<string, unknown>): void {
    this.configChange.emit(newConfig);
  }

  /**
   * Toggle panel expansion
   */
  togglePanel(): void {
    this.isExpanded = !this.isExpanded;
  }
}
