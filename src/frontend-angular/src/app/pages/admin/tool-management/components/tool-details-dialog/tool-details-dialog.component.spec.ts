/**
 * Tool Details Dialog Component Tests
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { Tool } from '../../models/tool-management.models';
import { ToolAdminService } from '../../services/tool-admin.service';
import { ToolDetailsDialogComponent } from './tool-details-dialog.component';

describe('ToolDetailsDialogComponent', () => {
  let component: ToolDetailsDialogComponent;
  let fixture: ComponentFixture<ToolDetailsDialogComponent>;
  let toolService: jest.Mocked<ToolAdminService>;
  let dialogRef: jest.Mocked<MatDialogRef<ToolDetailsDialogComponent>>;

  const mockTool: Tool = {
    id: 'uuid-1',
    tool_id: 'test-tool',
    name: 'Test Tool',
    description: 'Test description',
    category: 'database',
    provider: null,
    tool_purpose: 'orchestrator',
    service_location: 'orchestrator',
    mcp_server_type: 'http',
    mcp_command: null,
    mcp_endpoint: 'https://example.com',
    mcp_protocol_version: '2024-11-05',
    capabilities: { search: true },
    parameters_schema: { type: 'object' },
    requires_authentication: false,
    authentication_type: null,
    secret_name: null,
    config_options: null,
    timeout_seconds: 30,
    rate_limit_per_minute: null,
    max_concurrent_calls: 5,
    is_enabled: true,
    health_check_interval_seconds: 300,
    version: null,
    documentation_url: null,
    tags: ['test', 'database'],
    is_healthy: true,
    last_health_check: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    created_by: null,
    updated_by: null,
  };

  beforeEach(async () => {
    const toolServiceMock = {
      getTool: jest.fn(),
    };

    const dialogRefMock = {
      close: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ToolDetailsDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: ToolAdminService, useValue: toolServiceMock },
        { provide: MatDialogRef, useValue: dialogRefMock },
        {
          provide: MAT_DIALOG_DATA,
          useValue: { toolId: 'uuid-1' },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolDetailsDialogComponent);
    component = fixture.componentInstance;
    toolService = TestBed.inject(
      ToolAdminService
    ) as jest.Mocked<ToolAdminService>;
    dialogRef = TestBed.inject(MatDialogRef) as jest.Mocked<
      MatDialogRef<ToolDetailsDialogComponent>
    >;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit', () => {
    it('should load tool on init', () => {
      toolService.getTool.mockReturnValue(of(mockTool));

      component.ngOnInit();

      expect(toolService.getTool).toHaveBeenCalledWith('uuid-1');
      expect(component.tool).toEqual(mockTool);
      expect(component.isLoading).toBe(false);
    });

    it('should handle error loading tool', () => {
      toolService.getTool.mockReturnValue(
        throwError(() => new Error('Network error'))
      );

      component.ngOnInit();

      expect(component.error).toBe('Failed to load tool details');
      expect(component.isLoading).toBe(false);
    });
  });

  describe('loadTool', () => {
    it('should load tool successfully', () => {
      toolService.getTool.mockReturnValue(of(mockTool));
      component.isLoading = true;

      component.loadTool();

      expect(toolService.getTool).toHaveBeenCalledWith('uuid-1');
      expect(component.tool).toEqual(mockTool);
      expect(component.isLoading).toBe(false);
    });

    it('should handle error', () => {
      toolService.getTool.mockReturnValue(
        throwError(() => new Error('Network error'))
      );

      component.loadTool();

      expect(component.error).toBe('Failed to load tool details');
      expect(component.isLoading).toBe(false);
    });
  });

  describe('onClose', () => {
    it('should close dialog', () => {
      component.onClose();

      expect(dialogRef.close).toHaveBeenCalled();
    });
  });

  describe('onEdit', () => {
    it('should close dialog with edit flag', () => {
      component.onEdit();

      expect(dialogRef.close).toHaveBeenCalledWith({ edit: true });
    });
  });

  describe('getCapabilitiesJson', () => {
    it('should return formatted JSON for capabilities', () => {
      component.tool = mockTool;

      const result = component.getCapabilitiesJson();

      expect(result).toBe(JSON.stringify(mockTool.capabilities, null, 2));
    });

    it('should return empty object JSON when no capabilities', () => {
      component.tool = { ...mockTool, capabilities: null };

      const result = component.getCapabilitiesJson();

      expect(result).toBe('{}');
    });

    it('should return empty object JSON when tool is null', () => {
      component.tool = null;

      const result = component.getCapabilitiesJson();

      expect(result).toBe('{}');
    });
  });

  describe('getParametersJson', () => {
    it('should return formatted JSON for parameters', () => {
      component.tool = mockTool;

      const result = component.getParametersJson();

      expect(result).toBe(JSON.stringify(mockTool.parameters_schema, null, 2));
    });

    it('should return empty object JSON when no parameters', () => {
      component.tool = { ...mockTool, parameters_schema: null };

      const result = component.getParametersJson();

      expect(result).toBe('{}');
    });

    it('should return empty object JSON when tool is null', () => {
      component.tool = null;

      const result = component.getParametersJson();

      expect(result).toBe('{}');
    });
  });
});
