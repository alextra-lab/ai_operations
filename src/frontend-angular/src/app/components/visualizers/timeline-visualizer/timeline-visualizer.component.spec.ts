/**
 * Unit Tests for Timeline Visualizer Component
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatIconModule } from '@angular/material/icon';
import { TimelineConfig } from '../../../models/output-format.model';
import { TimelineVisualizerComponent } from './timeline-visualizer.component';

describe('TimelineVisualizerComponent', () => {
  let component: TimelineVisualizerComponent;
  let fixture: ComponentFixture<TimelineVisualizerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TimelineVisualizerComponent, MatIconModule],
    }).compileComponents();

    fixture = TestBed.createComponent(TimelineVisualizerComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should sort events by timestamp', () => {
    const testEvents = [
      { timestamp: '2025-01-03T10:00:00Z', description: 'Event 3' },
      { timestamp: '2025-01-01T10:00:00Z', description: 'Event 1' },
      { timestamp: '2025-01-02T10:00:00Z', description: 'Event 2' },
    ];

    const testConfig: TimelineConfig = {
      time_field: 'timestamp',
      label_field: 'description',
    };

    component.events = testEvents;
    component.config = testConfig;
    component.ngOnInit();

    expect(component.sortedEvents[0].description).toBe('Event 1');
    expect(component.sortedEvents[2].description).toBe('Event 3');
  });

  it('should get event label', () => {
    const testConfig: TimelineConfig = {
      time_field: 'timestamp',
      label_field: 'description',
    };

    component.config = testConfig;

    interface TestEvent {
      description: string;
      timestamp: string;
    }
    const event: TestEvent = {
      description: 'Test Event',
      timestamp: '2025-01-01',
    };
    const label = component.getEventLabel(event);
    expect(label).toBe('Test Event');
  });

  it('should get event severity', () => {
    const testConfig: TimelineConfig = {
      time_field: 'timestamp',
      label_field: 'description',
      severity_field: 'severity',
    };

    component.config = testConfig;

    interface TestEventWithSeverity {
      severity: string;
      timestamp: string;
      description: string;
    }
    const event: TestEventWithSeverity = {
      severity: 'HIGH',
      timestamp: '',
      description: '',
    };
    const severity = component.getEventSeverity(event);
    expect(severity).toBe('high');
  });

  it('should format timestamp', () => {
    const formatted = component.formatTime('2025-01-15T14:30:00Z');
    expect(formatted).toContain('Jan');
    expect(formatted).toContain('15');
  });

  it('should get severity icon', () => {
    expect(component.getSeverityIcon('critical')).toBe('error');
    expect(component.getSeverityIcon('high')).toBe('warning');
    expect(component.getSeverityIcon('medium')).toBe('info');
    expect(component.getSeverityIcon('low')).toBe('check_circle');
  });
});
