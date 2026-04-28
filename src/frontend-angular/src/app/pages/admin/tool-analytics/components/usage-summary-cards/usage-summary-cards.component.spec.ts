/**
 * Usage Summary Cards Component Tests
 *
 * Unit tests for T6-F3 UsageSummaryCardsComponent.
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AggregateAnalytics } from '../../models/tool-analytics.models';
import { UsageSummaryCardsComponent } from './usage-summary-cards.component';

describe('UsageSummaryCardsComponent', () => {
  let component: UsageSummaryCardsComponent;
  let fixture: ComponentFixture<UsageSummaryCardsComponent>;

  const mockAggregates: AggregateAnalytics = {
    total_invocations: 1000,
    total_successful: 950,
    average_success_rate: 95.0,
    total_cost: 5.5,
    average_duration_ms: 250,
    most_used_tool: 'Test Tool',
    most_used_tool_calls: 500,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        UsageSummaryCardsComponent,
        MatCardModule,
        MatIconModule,
        MatTooltipModule,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UsageSummaryCardsComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('with data', () => {
    beforeEach(() => {
      component.aggregates = mockAggregates;
      fixture.detectChanges();
    });

    it('should display total invocations', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('1,000');
      expect(compiled.textContent).toContain('Total Invocations');
    });

    it('should display success rate', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('95.0%');
      expect(compiled.textContent).toContain('Avg Success Rate');
    });

    it('should display total cost', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('€5.5000');
      expect(compiled.textContent).toContain('Estimated Cost');
    });

    it('should display most used tool', () => {
      const compiled = fixture.nativeElement;
      expect(compiled.textContent).toContain('Test Tool');
      expect(compiled.textContent).toContain('Most Used Tool');
    });
  });

  describe('formatting methods', () => {
    it('should format numbers with locale', () => {
      expect(component.formatNumber(1000)).toBe('1,000');
      expect(component.formatNumber(1234567)).toBe('1,234,567');
    });

    it('should format percentage', () => {
      expect(component.formatPercent(95.0)).toBe('95.0%');
      expect(component.formatPercent(99.9)).toBe('99.9%');
    });

    it('should format cost value', () => {
      expect(component.formatCostValue(5.5)).toBe('€5.5000');
      expect(component.formatCostValue(0.001)).toBe('€0.0010');
    });

    it('should format duration value in milliseconds', () => {
      expect(component.formatDurationValue(250)).toBe('250ms');
      expect(component.formatDurationValue(500)).toBe('500ms');
    });

    it('should format duration value in seconds', () => {
      expect(component.formatDurationValue(1500)).toBe('1.50s');
      expect(component.formatDurationValue(2500)).toBe('2.50s');
    });
  });

  describe('success rate styling', () => {
    it('should return success-high for rates >= 95', () => {
      component.aggregates = { ...mockAggregates, average_success_rate: 95 };
      expect(component.getSuccessClass()).toBe('success-high');

      component.aggregates = { ...mockAggregates, average_success_rate: 99 };
      expect(component.getSuccessClass()).toBe('success-high');
    });

    it('should return success-medium for rates 90-95', () => {
      component.aggregates = { ...mockAggregates, average_success_rate: 92 };
      expect(component.getSuccessClass()).toBe('success-medium');

      component.aggregates = { ...mockAggregates, average_success_rate: 90 };
      expect(component.getSuccessClass()).toBe('success-medium');
    });

    it('should return success-low for rates < 90', () => {
      component.aggregates = { ...mockAggregates, average_success_rate: 85 };
      expect(component.getSuccessClass()).toBe('success-low');

      component.aggregates = { ...mockAggregates, average_success_rate: 50 };
      expect(component.getSuccessClass()).toBe('success-low');
    });

    it('should return empty string when no aggregates', () => {
      component.aggregates = null;
      expect(component.getSuccessClass()).toBe('');
    });
  });

  describe('most used tool display', () => {
    it('should truncate long tool names', () => {
      component.aggregates = {
        ...mockAggregates,
        most_used_tool:
          'This is a very long tool name that should be truncated',
      };
      expect(component.getMostUsedToolText().length).toBeLessThanOrEqual(20);
      expect(component.getMostUsedToolText()).toContain('...');
    });

    it('should not truncate short tool names', () => {
      component.aggregates = {
        ...mockAggregates,
        most_used_tool: 'Short Name',
      };
      expect(component.getMostUsedToolText()).toBe('Short Name');
    });

    it('should return N/A when no most used tool', () => {
      component.aggregates = { ...mockAggregates, most_used_tool: null };
      expect(component.getMostUsedToolText()).toBe('N/A');
    });

    it('should provide tooltip with full name and count', () => {
      component.aggregates = mockAggregates;
      expect(component.getMostUsedToolTooltip()).toBe('Test Tool (500 calls)');
    });

    it('should provide tooltip when no tool', () => {
      component.aggregates = { ...mockAggregates, most_used_tool: null };
      expect(component.getMostUsedToolTooltip()).toBe('No tools used');
    });
  });

  describe('empty state', () => {
    it('should show empty state when no aggregates', () => {
      component.aggregates = null;
      fixture.detectChanges();

      const compiled = fixture.nativeElement;
      expect(compiled.querySelector('.empty-state')).toBeTruthy();
      expect(compiled.textContent).toContain('No analytics data available');
    });

    it('should hide metrics grid when no aggregates', () => {
      component.aggregates = null;
      fixture.detectChanges();

      const compiled = fixture.nativeElement;
      expect(compiled.querySelector('.metrics-grid')).toBeFalsy();
    });
  });
});
