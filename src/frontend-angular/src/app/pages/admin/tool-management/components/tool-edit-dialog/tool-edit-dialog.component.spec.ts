/**
 * Tool Edit Dialog Component Tests
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormBuilder } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { Tool, ToolUpdateRequest } from '../../models/tool-management.models';
import { ToolAdminService } from '../../services/tool-admin.service';
import { ToolEditDialogComponent } from './tool-edit-dialog.component';

describe('ToolEditDialogComponent', () => {
  let component: ToolEditDialogComponent;
  let fixture: ComponentFixture<ToolEditDialogComponent>;
  let toolService: jest.Mocked<ToolAdminService>;
  let dialogRef: jest.Mocked<MatDialogRef<ToolEditDialogComponent>>;

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
    capabilities: null,
    parameters_schema: null,
    requires_authentication: false,
    authentication_type: null,
    secret_name: null,
    config_options: null,
    timeout_seconds: 30,
    rate_limit_per_minute: 60,
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
      updateTool: jest.fn(),
    };

    const dialogRefMock = {
      close: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ToolEditDialogComponent, NoopAnimationsModule],
      providers: [
        FormBuilder,
        { provide: ToolAdminService, useValue: toolServiceMock },
        { provide: MatDialogRef, useValue: dialogRefMock },
        {
          provide: MAT_DIALOG_DATA,
          useValue: { toolId: 'uuid-1' },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolEditDialogComponent);
    component = fixture.componentInstance;
    toolService = TestBed.inject(
      ToolAdminService
    ) as jest.Mocked<ToolAdminService>;
    dialogRef = TestBed.inject(MatDialogRef) as jest.Mocked<
      MatDialogRef<ToolEditDialogComponent>
    >;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit', () => {
    it('should load tool and populate form on init', () => {
      toolService.getTool.mockReturnValue(of(mockTool));

      component.ngOnInit();

      // Observable completes synchronously with of()
      expect(toolService.getTool).toHaveBeenCalledWith('uuid-1');
      expect(component.tool).toEqual(mockTool);
      expect(component.form.value.name).toBe('Test Tool');
      expect(component.form.value.description).toBe('Test description');
      expect(component.form.value.timeout_seconds).toBe(30);
      expect(component.form.value.tags).toEqual(['test', 'database']);
      expect(component.tagsInput).toBe('test, database');
      expect(component.isLoading).toBe(false);
    });

    it('should handle error loading tool', () => {
      toolService.getTool.mockReturnValue(
        throwError(() => new Error('Network error'))
      );

      component.ngOnInit();

      expect(component.error).toBe('Failed to load tool');
      expect(component.isLoading).toBe(false);
    });
  });

  describe('loadTool', () => {
    it('should load tool and populate form', () => {
      toolService.getTool.mockReturnValue(of(mockTool));

      component.loadTool();

      // Observable completes synchronously with of()
      expect(toolService.getTool).toHaveBeenCalledWith('uuid-1');
      expect(component.tool).toEqual(mockTool);
      expect(component.form.value.name).toBe('Test Tool');
      expect(component.isLoading).toBe(false);
    });

    it('should handle null description', () => {
      const toolWithoutDesc = { ...mockTool, description: null };
      toolService.getTool.mockReturnValue(of(toolWithoutDesc));

      component.loadTool();

      expect(component.form.value.description).toBe('');
    });

    it('should handle empty tags', () => {
      const toolWithoutTags = { ...mockTool, tags: null };
      toolService.getTool.mockReturnValue(of(toolWithoutTags));

      component.loadTool();

      expect(component.form.value.tags).toEqual([]);
      expect(component.tagsInput).toBe('');
    });

    it('should handle error', () => {
      toolService.getTool.mockReturnValue(
        throwError(() => new Error('Network error'))
      );

      component.loadTool();

      expect(component.error).toBe('Failed to load tool');
      expect(component.isLoading).toBe(false);
    });
  });

  describe('onTagsInputChange', () => {
    it('should parse tags from input', () => {
      component.tagsInput = 'tag1, tag2, tag3';
      component.onTagsInputChange();

      expect(component.form.value.tags).toEqual(['tag1', 'tag2', 'tag3']);
    });

    it('should handle empty tags', () => {
      component.tagsInput = '';
      component.onTagsInputChange();

      expect(component.form.value.tags).toEqual([]);
    });

    it('should trim whitespace from tags', () => {
      component.tagsInput = ' tag1 , tag2 , tag3 ';
      component.onTagsInputChange();

      expect(component.form.value.tags).toEqual(['tag1', 'tag2', 'tag3']);
    });

    it('should filter out empty tags', () => {
      component.tagsInput = 'tag1, , tag2, , tag3';
      component.onTagsInputChange();

      expect(component.form.value.tags).toEqual(['tag1', 'tag2', 'tag3']);
    });
  });

  describe('onSubmit', () => {
    beforeEach(() => {
      toolService.getTool.mockReturnValue(of(mockTool));
      component.ngOnInit();
    });

    it('should not submit if form is invalid', () => {
      component.form.patchValue({ name: '' });
      component.form.markAllAsTouched();

      component.onSubmit();

      expect(toolService.updateTool).not.toHaveBeenCalled();
    });

    it('should submit valid form', () => {
      const updateRequest: ToolUpdateRequest = {
        name: 'Updated Tool',
        description: 'Updated description',
        timeout_seconds: 60,
        rate_limit_per_minute: 120,
        tags: ['updated', 'tags'],
      };
      toolService.updateTool.mockReturnValue(of(mockTool));

      component.form.patchValue(updateRequest);
      component.onSubmit();

      expect(component.isSubmitting).toBe(true);
      expect(toolService.updateTool).toHaveBeenCalledWith(
        'uuid-1',
        updateRequest
      );
      expect(dialogRef.close).toHaveBeenCalledWith(true);
    });

    it('should convert empty description to null', () => {
      toolService.updateTool.mockReturnValue(of(mockTool));

      component.form.patchValue({
        name: 'Updated Tool',
        description: '',
      });
      component.onSubmit();

      const callArgs = toolService.updateTool.mock.calls[0];
      expect(callArgs[1].description).toBeNull();
    });

    it('should convert null rate_limit_per_minute', () => {
      toolService.updateTool.mockReturnValue(of(mockTool));

      component.form.patchValue({
        name: 'Updated Tool',
        rate_limit_per_minute: null,
      });
      component.onSubmit();

      const callArgs = toolService.updateTool.mock.calls[0];
      expect(callArgs[1].rate_limit_per_minute).toBeNull();
    });

    it('should handle update error', () => {
      const errorResponse = {
        error: { detail: 'Validation error' },
      };
      toolService.updateTool.mockReturnValue(throwError(() => errorResponse));

      component.onSubmit();

      expect(component.error).toBe('Validation error');
      expect(component.isSubmitting).toBe(false);
    });

    it('should handle update error without detail', () => {
      toolService.updateTool.mockReturnValue(
        throwError(() => new Error('Network error'))
      );

      component.onSubmit();

      expect(component.error).toBe('Failed to update tool. Please try again.');
      expect(component.isSubmitting).toBe(false);
    });
  });

  describe('onCancel', () => {
    it('should close dialog with false', () => {
      component.onCancel();

      expect(dialogRef.close).toHaveBeenCalledWith(false);
    });
  });

  describe('form validation', () => {
    it('should require name', () => {
      component.form.patchValue({ name: '' });
      expect(component.form.controls.name.invalid).toBe(true);
    });

    it('should enforce max length for name', () => {
      component.form.patchValue({ name: 'a'.repeat(256) });
      expect(component.form.controls.name.invalid).toBe(true);
    });

    it('should require timeout_seconds', () => {
      component.form.patchValue({ timeout_seconds: null });
      expect(component.form.controls.timeout_seconds.invalid).toBe(true);
    });

    it('should enforce min timeout_seconds', () => {
      component.form.patchValue({ timeout_seconds: 0 });
      expect(component.form.controls.timeout_seconds.invalid).toBe(true);
    });

    it('should enforce max timeout_seconds', () => {
      component.form.patchValue({ timeout_seconds: 301 });
      expect(component.form.controls.timeout_seconds.invalid).toBe(true);
    });

    it('should enforce min rate_limit_per_minute', () => {
      component.form.patchValue({ rate_limit_per_minute: 0 });
      expect(component.form.controls.rate_limit_per_minute.invalid).toBe(true);
    });

    it('should enforce min health_check_interval_seconds', () => {
      component.form.patchValue({ health_check_interval_seconds: 59 });
      expect(
        component.form.controls.health_check_interval_seconds.invalid
      ).toBe(true);
    });
  });
});
