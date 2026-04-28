/**
 * Timeline Visualizer Component
 *
 * Renders events in a vertical timeline with severity indicators.
 * Supports sorting by timestamp and visual severity coding.
 */

import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { TimelineConfig } from '../../../models/output-format.model';

interface TimelineEvent {
  timestamp: string;
  description: string;
  severity?: string;
  details?: string;
  [key: string]: unknown;
}

@Component({
  selector: 'app-timeline-visualizer',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './timeline-visualizer.component.html',
  styleUrls: ['./timeline-visualizer.component.scss'],
})
export class TimelineVisualizerComponent implements OnInit {
  @Input() events: unknown[] = [];
  @Input() config!: TimelineConfig;
  @Input() title = '';

  sortedEvents: TimelineEvent[] = [];
  String = String; // Expose to template

  ngOnInit(): void {
    this.sortEvents();
  }

  /**
   * Sort events by timestamp
   */
  private sortEvents(): void {
    const typedEvents = this.events as TimelineEvent[];

    this.sortedEvents = [...typedEvents].sort((a, b) => {
      const timeA = this.getEventTime(a);
      const timeB = this.getEventTime(b);
      return timeA.getTime() - timeB.getTime();
    });
  }

  /**
   * Get timestamp from event
   */
  private getEventTime(event: TimelineEvent): Date {
    const timeField = this.config.time_field;
    const timestamp = event[timeField];
    return new Date(String(timestamp));
  }

  /**
   * Get event label
   */
  getEventLabel(event: TimelineEvent): string {
    const labelField = this.config.label_field;
    return String(event[labelField] || '');
  }

  /**
   * Get event details
   */
  getEventDetails(event: TimelineEvent): string {
    if (!this.config.details_field) {
      return '';
    }
    return String(event[this.config.details_field] || '');
  }

  /**
   * Get event severity
   */
  getEventSeverity(event: TimelineEvent): string {
    if (!this.config.severity_field) {
      return 'normal';
    }
    const severity = event[this.config.severity_field];
    return String(severity || 'normal').toLowerCase();
  }

  /**
   * Format timestamp for display
   */
  formatTime(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return timestamp;
    }
  }

  /**
   * Get icon for severity level
   */
  getSeverityIcon(severity: string): string {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      case 'low':
        return 'check_circle';
      default:
        return 'fiber_manual_record';
    }
  }
}
