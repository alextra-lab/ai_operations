/**
 * Usage By Tool Table Component Tests
 *
 * Unit tests for T6-F3 UsageByToolTableComponent.
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatIconModule } from '@angular/material/icon';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { ToolUsageSummary } from '../../models/tool-analytics.models';
import { UsageByToolTableComponent } from './usage-by-tool-table.component';

describe('UsageByToolTableComponent', () => {
  let component: UsageByToolTableComponent;
  let fixture: ComponentFixture<UsageByToolTableComponent>;

  const mockData: ToolUsageSummary[] = [
    {
      tool_id: 'tool-1',
      tool_name: 'Test Tool 1',
      total_calls: 100,
      successful_calls: 95,
      success_rate: 95.0,
      avg_duration_ms: 250,
      total_cost: 0.5,
    },
    {
      tool_id: 'tool-2',
      tool_name: 'Test Tool 2',
      total_calls: 50,
      successful_calls: 40,
      success_rate: 80.0,
      avg_duration_ms: 180,
      total_cost: 0.25,
    },
    {
      tool_id: 'tool-3',
      total_calls: 75,
      successful_calls: 70,
      success_rate: 93.3,
      avg_duration_ms: 300,
      total_cost: 0.35,
    },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        UsageByToolTableComponent,
        MatTableModule,
        MatSortModule,
        MatIconModule,
        MatTooltipModule,
        NoopAnimationsModule,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UsageByToolTableComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('with data', () => {
    beforeEach(() => {
      component.data = mockData;
      component.ngOnChanges({
        data: {
          currentValue: mockData,
          previousValue: [],
          firstChange: true,
          isFirstChange: () => true,
        },
      });
      fixture.detectChanges();
    });

    it('should display all tools in table', () => {
      const rows = fixture.nativeElement.querySelectorAll('tr.mat-mdc-row');
      expect(rows.length).toBe(3);
    });

    it('should display correct columns', () => {
      expect(component.displayedColumns).toEqual([
        'tool_name',
        'total_calls',
        'successful_calls',
        'success_rate',
        'avg_duration_ms',
        'total_cost',
      ]);
    });
  });

  describe('formatting methods', () => {
    it('should format numbers with locale', () => {
      expect(component.formatNumber(1000)).toBe('1,000');
      expect(component.formatNumber(100)).toBe('100');
    });

    it('should format percentage', () => {
      expect(component.formatPercent(95.0)).toBe('95.0%');
      expect(component.formatPercent(80.12345)).toBe('80.1%');
    });

    it('should format cost value', () => {
      expect(component.formatCostValue(0.5)).toBe('€0.5000');
      expect(component.formatCostValue(1.2345)).toBe('€1.2345');
    });

    it('should format duration in ms', () => {
      expect(component.formatDurationValue(250)).toBe('250ms');
    });

    it('should format duration in seconds', () => {
      expect(component.formatDurationValue(1500)).toBe('1.50s');
    });
  });

  describe('tool name display', () => {
    it('should use tool_name when available', () => {
      const item: ToolUsageSummary = {
        tool_id: 'tool-1',
        tool_name: 'Test Tool',
        total_calls: 100,
        successful_calls: 95,
        success_rate: 95.0,
        avg_duration_ms: 250,
        total_cost: 0.5,
      };
      expect(component.getToolName(item)).toBe('Test Tool');
    });

    it('should fall back to tool_id when no name', () => {
      const item: ToolUsageSummary = {
        tool_id: 'tool-1',
        total_calls: 100,
        successful_calls: 95,
        success_rate: 95.0,
        avg_duration_ms: 250,
        total_cost: 0.5,
      };
      expect(component.getToolName(item)).toBe('tool-1');
    });

    it('should truncate long tool IDs', () => {
      const longId = 'very-long-tool-id-12345678';
      expect(component.getToolIdShort(longId)).toBe('very-lon...');
    });

    it('should not truncate short tool IDs', () => {
      expect(component.getToolIdShort('tool-1')).toBe('tool-1');
    });
  });

  describe('success rate styling', () => {
    it('should return success-high for rates >= 95', () => {
      expect(component.getSuccessClass(95)).toBe('success-high');
      expect(component.getSuccessClass(100)).toBe('success-high');
    });

    it('should return success-medium for rates 90-95', () => {
      expect(component.getSuccessClass(90)).toBe('success-medium');
      expect(component.getSuccessClass(94.9)).toBe('success-medium');
    });

    it('should return success-low for rates < 90', () => {
      expect(component.getSuccessClass(80)).toBe('success-low');
      expect(component.getSuccessClass(50)).toBe('success-low');
    });
  });

  describe('sorting', () => {
    beforeEach(() => {
      component.data = mockData;
      component.ngOnChanges({
        data: {
          currentValue: mockData,
          previousValue: [],
          firstChange: true,
          isFirstChange: () => true,
        },
      });
    });

    it('should sort by total_calls ascending', () => {
      const sortState: Sort = { active: 'total_calls', direction: 'asc' };
      component.onSortChange(sortState);

      expect(component.dataSource.data[0].total_calls).toBe(50);
      expect(component.dataSource.data[2].total_calls).toBe(100);
    });

    it('should sort by total_calls descending', () => {
      const sortState: Sort = { active: 'total_calls', direction: 'desc' };
      component.onSortChange(sortState);

      expect(component.dataSource.data[0].total_calls).toBe(100);
      expect(component.dataSource.data[2].total_calls).toBe(50);
    });

    it('should sort by success_rate', () => {
      const sortState: Sort = { active: 'success_rate', direction: 'asc' };
      component.onSortChange(sortState);

      expect(component.dataSource.data[0].success_rate).toBe(80.0);
    });

    it('should reset sorting when direction is empty', () => {
      const sortState: Sort = { active: 'total_calls', direction: '' };
      component.onSortChange(sortState);

      // Should be back to original order
      expect(component.dataSource.data).toEqual(mockData);
    });
  });

  describe('empty state', () => {
    it('should show empty state when no data', () => {
      component.data = [];
      fixture.detectChanges();

      const emptyState = fixture.nativeElement.querySelector('.empty-state');
      expect(emptyState).toBeTruthy();
      expect(emptyState.textContent).toContain('No tool usage data available');
    });

    it('should hide table when no data', () => {
      component.data = [];
      fixture.detectChanges();

      const table = fixture.nativeElement.querySelector('table');
      expect(table).toBeFalsy();
    });
  });
});
