/**
 * Unit tests for AuditLogsComponent
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, Subject, throwError } from 'rxjs';
import { AuditLogsComponent } from './audit-logs.component';
import { AuditLogEntry } from './models/audit-logs.models';
import { AuditLogsService } from './services/audit-logs.service';

describe('AuditLogsComponent', () => {
  let component: AuditLogsComponent;
  let fixture: ComponentFixture<AuditLogsComponent>;
  let mockAuditService: Partial<AuditLogsService>;
  let mockDialog: Partial<MatDialog>;
  let mockDialogRef: Partial<MatDialogRef<any>>;

  const mockLogEntry: AuditLogEntry = {
    id: '123e4567-e89b-12d3-a456-426614174000',
    event_time: '2025-10-27T12:00:00Z',
    actor_user_id: '123e4567-e89b-12d3-a456-426614174001',
    actor_username: 'testuser',
    actor_roles: ['admin'],
    action: 'GET /api/v1/use-cases',
    resource_type: 'http_request',
    resource_id: '/api/v1/use-cases',
    use_case_id: null,
    use_case_name: null,
    request_id: 'req-123',
    client_ip: '127.0.0.1',
    user_agent: 'Mozilla/5.0',
    success: true,
    details: { status_code: 200 },
    created_at: '2025-10-27T12:00:00Z',
  };

  beforeEach(async () => {
    const afterOpenedSubject = new Subject<void>();
    const afterClosedSubject = new Subject<any>();

    mockDialogRef = {
      close: jest.fn((result?: any) => {
        afterClosedSubject.next(result);
        afterClosedSubject.complete();
      }),
      afterOpened: afterOpenedSubject.asObservable(),
      afterClosed: afterClosedSubject.asObservable(),
      componentInstance: {} as any,
      disableClose: false,
      id: 'test-dialog-id',
    };

    mockAuditService = {
      listAuditLogs: jest.fn(),
      getStats: jest.fn(),
      getAuditLog: jest.fn(),
    };
    const openDialogsArray: any[] = [];
    mockDialog = {
      open: jest.fn((component: any, config?: any) => {
        openDialogsArray.push(mockDialogRef);
        return mockDialogRef;
      }),
      _openDialogs: openDialogsArray,
      openDialogs: openDialogsArray,
    } as any;

    await TestBed.configureTestingModule({
      imports: [AuditLogsComponent, NoopAnimationsModule],
      providers: [
        { provide: AuditLogsService, useValue: mockAuditService },
        { provide: MatDialog, useValue: mockDialog },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AuditLogsComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit', () => {
    it('should load logs and stats on initialization', () => {
      (mockAuditService.listAuditLogs as jest.Mock).mockReturnValue(
        of({
          total: 1,
          page: 1,
          page_size: 50,
          total_pages: 1,
          logs: [mockLogEntry],
        })
      );
      (mockAuditService.getStats as jest.Mock).mockReturnValue(
        of({
          total_events: 1,
          success_count: 1,
          failure_count: 0,
          unique_users: 1,
          unique_resource_types: 1,
          date_range_start: '2025-10-01T00:00:00Z',
          date_range_end: '2025-10-27T23:59:59Z',
          top_actions: [],
          top_resource_types: [],
        })
      );

      component.ngOnInit();

      expect(mockAuditService.listAuditLogs).toHaveBeenCalled();
      expect(mockAuditService.getStats).toHaveBeenCalled();
    });
  });

  describe('loadLogs', () => {
    it('should load logs successfully', () => {
      (mockAuditService.listAuditLogs as jest.Mock).mockReturnValue(
        of({
          total: 1,
          page: 1,
          page_size: 50,
          total_pages: 1,
          logs: [mockLogEntry],
        })
      );

      component.loadLogs();

      expect(component.isLoading).toBe(false);
      expect(component.logs.length).toBe(1);
      expect(component.totalLogs).toBe(1);
      expect(component.error).toBeNull();
    });

    it('should handle load errors', () => {
      (mockAuditService.listAuditLogs as jest.Mock).mockReturnValue(
        throwError(() => new Error('Load failed'))
      );

      component.loadLogs();

      expect(component.isLoading).toBe(false);
      expect(component.error).toBe('Failed to load audit logs');
    });
  });

  describe('filtering', () => {
    it('should update filters and reload on search', () => {
      (mockAuditService.listAuditLogs as jest.Mock).mockReturnValue(
        of({
          total: 0,
          page: 1,
          page_size: 50,
          total_pages: 0,
          logs: [],
        })
      );

      component.onSearch('test query');

      expect(component.filters.search).toBe('test query');
      expect(component.filters.page).toBe(1);
      expect(mockAuditService.listAuditLogs).toHaveBeenCalled();
    });

    it('should reset page on filter change', () => {
      (mockAuditService.listAuditLogs as jest.Mock).mockReturnValue(
        of({
          total: 0,
          page: 1,
          page_size: 50,
          total_pages: 0,
          logs: [],
        })
      );
      (mockAuditService.getStats as jest.Mock).mockReturnValue(
        of({
          total_events: 0,
          success_count: 0,
          failure_count: 0,
          unique_users: 0,
          unique_resource_types: 0,
          date_range_start: null,
          date_range_end: null,
          top_actions: [],
          top_resource_types: [],
        })
      );

      component.filters.page = 5;
      component.onFilterChange();

      expect(component.filters.page).toBe(1);
    });

    it('should clear all filters', () => {
      (mockAuditService.listAuditLogs as jest.Mock).mockReturnValue(
        of({
          total: 0,
          page: 1,
          page_size: 50,
          total_pages: 0,
          logs: [],
        })
      );
      (mockAuditService.getStats as jest.Mock).mockReturnValue(
        of({
          total_events: 0,
          success_count: 0,
          failure_count: 0,
          unique_users: 0,
          unique_resource_types: 0,
          date_range_start: null,
          date_range_end: null,
          top_actions: [],
          top_resource_types: [],
        })
      );

      component.filters.search = 'test';
      component.filters.action = 'POST';
      component.clearFilters();

      expect(component.filters.search).toBe('');
      expect(component.filters.action).toBe('');
    });
  });

  describe('pagination', () => {
    it('should handle page change', () => {
      (mockAuditService.listAuditLogs as jest.Mock).mockReturnValue(
        of({
          total: 100,
          page: 2,
          page_size: 25,
          total_pages: 4,
          logs: [],
        })
      );

      const pageEvent = {
        pageIndex: 1,
        pageSize: 25,
        length: 100,
      };

      component.onPageChange(pageEvent);

      expect(component.filters.page).toBe(2);
      expect(component.filters.page_size).toBe(25);
    });
  });

  describe('helper methods', () => {
    it('should format dates correctly', () => {
      const result = component.formatDate('2025-10-27T12:00:00Z');
      expect(result).toBeTruthy();
    });

    it('should return correct status colors', () => {
      expect(component.getStatusColor(true)).toBe('primary');
      expect(component.getStatusColor(false)).toBe('warn');
    });

    it('should return correct status icons', () => {
      expect(component.getStatusIcon(true)).toBe('check_circle');
      expect(component.getStatusIcon(false)).toBe('error');
    });

    it('should calculate success rate', () => {
      component.stats = {
        total_events: 100,
        success_count: 95,
        failure_count: 5,
        unique_users: 10,
        unique_resource_types: 5,
        date_range_start: null,
        date_range_end: null,
        top_actions: [],
        top_resource_types: [],
      };

      expect(component.getSuccessRate()).toBe(95);
    });

    it('should handle zero events for success rate', () => {
      component.stats = {
        total_events: 0,
        success_count: 0,
        failure_count: 0,
        unique_users: 0,
        unique_resource_types: 0,
        date_range_start: null,
        date_range_end: null,
        top_actions: [],
        top_resource_types: [],
      };

      expect(component.getSuccessRate()).toBe(0);
    });
  });

  describe('dialog', () => {
    it('should open details dialog', () => {
      const dialogSpy = jest
        .spyOn(component['dialog'], 'open')
        .mockReturnValue(mockDialogRef as any);

      component.openDetailsDialog(mockLogEntry);

      expect(dialogSpy).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          width: '800px',
          data: { log: mockLogEntry },
        })
      );

      dialogSpy.mockRestore();
    });
  });
});
