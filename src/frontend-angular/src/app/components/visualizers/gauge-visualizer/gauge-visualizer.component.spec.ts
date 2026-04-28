/**
 * Unit Tests for Gauge Visualizer Component
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { GaugeConfig } from '../../../models/output-format.model';
import { GaugeVisualizerComponent } from './gauge-visualizer.component';

describe('GaugeVisualizerComponent', () => {
  let component: GaugeVisualizerComponent;
  let fixture: ComponentFixture<GaugeVisualizerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GaugeVisualizerComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(GaugeVisualizerComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should format value as percentage', () => {
    const testConfig: GaugeConfig = {
      min: 0,
      max: 1,
      format: 'percent',
      thresholds: [
        { value: 0.5, color: '#4caf50', label: 'Low' },
        { value: 1.0, color: '#f44336', label: 'High' },
      ],
    };

    component.value = 0.75;
    component.config = testConfig;

    const formatted = component['formatValue'](0.75);
    expect(formatted).toBe('75%');
  });

  it('should format value as number', () => {
    const testConfig: GaugeConfig = {
      min: 0,
      max: 10,
      format: 'number',
      thresholds: [],
    };

    component.config = testConfig;
    const formatted = component['formatValue'](7.5);
    expect(formatted).toBe('7.50');
  });

  it('should get correct threshold for value', () => {
    const testConfig: GaugeConfig = {
      min: 0,
      max: 1,
      thresholds: [
        { value: 0.3, color: '#4caf50', label: 'Low' },
        { value: 0.6, color: '#ff9800', label: 'Medium' },
        { value: 1.0, color: '#f44336', label: 'High' },
      ],
    };

    component.config = testConfig;

    const threshold = component['getThreshold'](0.7);
    expect(threshold?.label).toBe('Medium');
  });
});
