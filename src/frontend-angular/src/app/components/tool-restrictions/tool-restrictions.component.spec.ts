/**
 * Tool Restrictions Component Tests (ADR-057)
 *
 * Tests for the security-based tool restrictions configuration component.
 */

import { SimpleChange } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import {
  TOOL_RESTRICTION_PRESETS,
  ToolRestrictions,
} from '../../api/models/use-case-management.models';
import { ToolRestrictionsComponent } from './tool-restrictions.component';

describe('ToolRestrictionsComponent', () => {
  let component: ToolRestrictionsComponent;
  let fixture: ComponentFixture<ToolRestrictionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ToolRestrictionsComponent, FormsModule, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolRestrictionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('initialization', () => {
    it('should start with restrictions disabled', () => {
      expect(component.enabled).toBe(false);
      expect(component.selectedPreset).toBe('none');
    });

    it('should have default data source options', () => {
      expect(component.dataSourceOptions).toHaveLength(4);
      expect(component.dataSourceOptions.map((o) => o.value)).toEqual([
        'internal',
        'external',
        'none',
        'mixed',
      ]);
    });

    it('should have default data flow options', () => {
      expect(component.dataFlowOptions).toHaveLength(4);
      expect(component.dataFlowOptions.map((o) => o.value)).toEqual([
        'ingress',
        'egress',
        'bidirectional',
        'none',
      ]);
    });

    it('should have default network options', () => {
      expect(component.networkOptions).toHaveLength(3);
      expect(component.networkOptions.map((o) => o.value)).toEqual([
        'isolated',
        'internal',
        'external',
      ]);
    });

    it('should have default sensitivity options', () => {
      expect(component.sensitivityOptions).toHaveLength(4);
      expect(component.sensitivityOptions.map((o) => o.value)).toEqual([
        'public',
        'internal',
        'confidential',
        'restricted',
      ]);
    });
  });

  describe('ngOnChanges', () => {
    it('should load restrictions when input changes', () => {
      const restrictions: ToolRestrictions = {
        allowed_data_sources: ['internal', 'external'],
        allowed_data_flows: ['ingress', 'egress'],
        allowed_network_levels: ['internal', 'external'],
        required_data_sensitivity: 'confidential',
      };

      component.restrictions = restrictions;
      component.ngOnChanges({
        restrictions: new SimpleChange(null, restrictions, true),
      });

      expect(component.enabled).toBe(true);
      expect(component.allowedDataSources).toEqual(
        new Set(['internal', 'external'])
      );
      expect(component.allowedDataFlows).toEqual(
        new Set(['ingress', 'egress'])
      );
      expect(component.allowedNetworkLevels).toEqual(
        new Set(['internal', 'external'])
      );
      expect(component.requiredSensitivity).toBe('confidential');
    });

    it('should reset to defaults when restrictions is null', () => {
      // First set some restrictions
      component.restrictions = {
        allowed_data_sources: ['external'],
        allowed_data_flows: ['egress'],
        allowed_network_levels: ['external'],
        required_data_sensitivity: 'restricted',
      };
      component.ngOnChanges({
        restrictions: new SimpleChange(null, component.restrictions, true),
      });

      // Then set to null
      component.restrictions = null;
      component.ngOnChanges({
        restrictions: new SimpleChange({}, null, false),
      });

      expect(component.enabled).toBe(false);
      expect(component.selectedPreset).toBe('none');
    });

    it('should detect high_security preset', () => {
      const restrictions = TOOL_RESTRICTION_PRESETS.high_security.restrictions;
      component.restrictions = restrictions;
      component.ngOnChanges({
        restrictions: new SimpleChange(null, restrictions, true),
      });

      expect(component.selectedPreset).toBe('high_security');
    });

    it('should detect internal_only preset', () => {
      const restrictions = TOOL_RESTRICTION_PRESETS.internal_only.restrictions;
      component.restrictions = restrictions;
      component.ngOnChanges({
        restrictions: new SimpleChange(null, restrictions, true),
      });

      expect(component.selectedPreset).toBe('internal_only');
    });

    it('should detect custom configuration', () => {
      const restrictions: ToolRestrictions = {
        allowed_data_sources: ['internal'],
        allowed_data_flows: ['egress'],
        allowed_network_levels: ['isolated'],
        required_data_sensitivity: 'public',
      };

      component.restrictions = restrictions;
      component.ngOnChanges({
        restrictions: new SimpleChange(null, restrictions, true),
      });

      expect(component.selectedPreset).toBe('custom');
    });
  });

  describe('onEnabledChange', () => {
    it('should emit null when disabled', () => {
      const emitSpy = jest.spyOn(component.restrictionsChange, 'emit');
      component.enabled = false;
      component.onEnabledChange();

      expect(emitSpy).toHaveBeenCalledWith(null);
    });

    it('should emit current restrictions when enabled', () => {
      const emitSpy = jest.spyOn(component.restrictionsChange, 'emit');
      component.enabled = true;
      component.onEnabledChange();

      expect(emitSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          allowed_data_sources: expect.any(Array),
          allowed_data_flows: expect.any(Array),
          allowed_network_levels: expect.any(Array),
          required_data_sensitivity: expect.any(String),
        })
      );
    });
  });

  describe('onPresetChange', () => {
    it('should emit null when preset is none', () => {
      const emitSpy = jest.spyOn(component.restrictionsChange, 'emit');
      component.selectedPreset = 'none';
      component.onPresetChange();

      expect(component.enabled).toBe(false);
      expect(emitSpy).toHaveBeenCalledWith(null);
    });

    it('should apply high_security preset', () => {
      const emitSpy = jest.spyOn(component.restrictionsChange, 'emit');
      component.selectedPreset = 'high_security';
      component.onPresetChange();

      expect(component.allowedDataSources).toEqual(
        new Set(['internal', 'none'])
      );
      expect(component.allowedDataFlows).toEqual(new Set(['ingress', 'none']));
      expect(component.allowedNetworkLevels).toEqual(
        new Set(['isolated', 'internal'])
      );
      expect(component.requiredSensitivity).toBe('restricted');
      expect(emitSpy).toHaveBeenCalled();
    });

    it('should apply research_open preset', () => {
      component.selectedPreset = 'research_open';
      component.onPresetChange();

      expect(component.allowedDataSources).toEqual(
        new Set(['internal', 'external', 'none', 'mixed'])
      );
      expect(component.allowedDataFlows).toEqual(
        new Set(['ingress', 'bidirectional', 'none'])
      );
      expect(component.requiredSensitivity).toBe('public');
    });

    it('should not change values when preset is custom', () => {
      // Set initial values
      component.allowedDataSources = new Set(['external']);
      component.allowedDataFlows = new Set(['egress']);

      component.selectedPreset = 'custom';
      component.onPresetChange();

      // Values should remain unchanged
      expect(component.allowedDataSources).toEqual(new Set(['external']));
      expect(component.allowedDataFlows).toEqual(new Set(['egress']));
    });
  });

  describe('toggle methods', () => {
    it('should toggle data source and emit', () => {
      const emitSpy = jest.spyOn(component.restrictionsChange, 'emit');
      const initialHasExternal = component.allowedDataSources.has('external');

      component.toggleDataSource('external');

      expect(component.allowedDataSources.has('external')).toBe(
        !initialHasExternal
      );
      expect(component.selectedPreset).toBe('custom');
      expect(emitSpy).toHaveBeenCalled();
    });

    it('should toggle data flow and emit', () => {
      const emitSpy = jest.spyOn(component.restrictionsChange, 'emit');
      const initialHasEgress = component.allowedDataFlows.has('egress');

      component.toggleDataFlow('egress');

      expect(component.allowedDataFlows.has('egress')).toBe(!initialHasEgress);
      expect(component.selectedPreset).toBe('custom');
      expect(emitSpy).toHaveBeenCalled();
    });

    it('should toggle network level and emit', () => {
      const emitSpy = jest.spyOn(component.restrictionsChange, 'emit');
      const initialHasExternal = component.allowedNetworkLevels.has('external');

      component.toggleNetworkLevel('external');

      expect(component.allowedNetworkLevels.has('external')).toBe(
        !initialHasExternal
      );
      expect(component.selectedPreset).toBe('custom');
      expect(emitSpy).toHaveBeenCalled();
    });
  });

  describe('onSensitivityChange', () => {
    it('should set preset to custom and emit', () => {
      const emitSpy = jest.spyOn(component.restrictionsChange, 'emit');
      component.selectedPreset = 'high_security';
      component.requiredSensitivity = 'public';

      component.onSensitivityChange();

      expect(component.selectedPreset).toBe('custom');
      expect(emitSpy).toHaveBeenCalled();
    });
  });

  describe('selection helpers', () => {
    it('should correctly report data source selection', () => {
      component.allowedDataSources = new Set(['internal', 'external']);

      expect(component.isDataSourceSelected('internal')).toBe(true);
      expect(component.isDataSourceSelected('external')).toBe(true);
      expect(component.isDataSourceSelected('none')).toBe(false);
      expect(component.isDataSourceSelected('mixed')).toBe(false);
    });

    it('should correctly report data flow selection', () => {
      component.allowedDataFlows = new Set(['ingress']);

      expect(component.isDataFlowSelected('ingress')).toBe(true);
      expect(component.isDataFlowSelected('egress')).toBe(false);
      expect(component.isDataFlowSelected('bidirectional')).toBe(false);
      expect(component.isDataFlowSelected('none')).toBe(false);
    });

    it('should correctly report network level selection', () => {
      component.allowedNetworkLevels = new Set(['isolated', 'internal']);

      expect(component.isNetworkLevelSelected('isolated')).toBe(true);
      expect(component.isNetworkLevelSelected('internal')).toBe(true);
      expect(component.isNetworkLevelSelected('external')).toBe(false);
    });
  });

  describe('disabled state', () => {
    it('should respect disabled input', () => {
      component.disabled = true;
      fixture.detectChanges();

      expect(component.disabled).toBe(true);
    });
  });

  describe('preset detection', () => {
    it('should correctly identify all presets', () => {
      const presetKeys = Object.keys(
        TOOL_RESTRICTION_PRESETS
      ) as (keyof typeof TOOL_RESTRICTION_PRESETS)[];

      for (const key of presetKeys) {
        const restrictions = TOOL_RESTRICTION_PRESETS[key].restrictions;
        component.restrictions = restrictions;
        component.ngOnChanges({
          restrictions: new SimpleChange(null, restrictions, true),
        });

        expect(component.selectedPreset).toBe(key);
      }
    });
  });
});
