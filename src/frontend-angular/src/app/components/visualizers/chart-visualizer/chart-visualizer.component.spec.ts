/**
 * Unit Tests for Chart Visualizer Component
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ChartConfig } from '../../../models/output-format.model';
import { ChartVisualizerComponent } from './chart-visualizer.component';

describe('ChartVisualizerComponent', () => {
  let component: ChartVisualizerComponent;
  let fixture: ComponentFixture<ChartVisualizerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChartVisualizerComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ChartVisualizerComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should parse array data correctly', () => {
    const testData = [
      { label: 'A', value: 10 },
      { label: 'B', value: 20 },
      { label: 'C', value: 30 },
    ];

    const testConfig: ChartConfig = {
      chart_type: 'bar',
    };

    component.data = testData;
    component.config = testConfig;

    const parsed = component['parseData'](testData);
    expect(parsed.labels).toEqual(['A', 'B', 'C']);
    expect(parsed.datasets[0]).toEqual([10, 20, 30]);
  });

  it('should generate colors for data', () => {
    const colors = component['generateColors'](5);
    expect(colors.length).toBe(5);
    expect(colors[0]).toBe('#2196F3');
  });

  it('should handle empty data', () => {
    const parsed = component['parseData']([]);
    expect(parsed.labels).toEqual([]);
    expect(parsed.datasets[0]).toEqual([]);
  });
});
