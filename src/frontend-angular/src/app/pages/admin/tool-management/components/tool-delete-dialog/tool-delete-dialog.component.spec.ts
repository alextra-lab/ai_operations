/**
 * Tool Delete Dialog Component Tests
 */

import {
  ComponentFixture,
  fakeAsync,
  flush,
  TestBed
} from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { ToolListItem } from '../../models/tool-management.models';
import { ToolAdminService } from '../../services/tool-admin.service';
import { ToolDeleteDialogComponent } from './tool-delete-dialog.component';

describe('ToolDeleteDialogComponent', () => {
  let component: ToolDeleteDialogComponent;
  let fixture: ComponentFixture<ToolDeleteDialogComponent>;
  let toolService: jest.Mocked<ToolAdminService>;
  let dialogRef: jest.Mocked<MatDialogRef<ToolDeleteDialogComponent>>;
  let snackBar: jest.Mocked<MatSnackBar>;

  const mockTool: ToolListItem = {
    id: 'uuid-1',
    tool_id: 'test-tool',
    name: 'Test Tool',
    description: 'Test description',
    category: 'database',
    provider: null,
    is_enabled: true,
    is_healthy: true,
    requires_authentication: false,
  };

  beforeEach(async () => {
    const toolServiceMock = {
      deleteTool: jest.fn(),
    };

    const dialogRefMock = {
      close: jest.fn(),
    };

    const snackBarMock = {
      open: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ToolDeleteDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: ToolAdminService, useValue: toolServiceMock },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MatSnackBar, useValue: snackBarMock },
        {
          provide: MAT_DIALOG_DATA,
          useValue: { tool: mockTool },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolDeleteDialogComponent);
    component = fixture.componentInstance;
    toolService = TestBed.inject(
      ToolAdminService
    ) as jest.Mocked<ToolAdminService>;
    dialogRef = TestBed.inject(MatDialogRef) as jest.Mocked<
      MatDialogRef<ToolDeleteDialogComponent>
    >;
    snackBar = TestBed.inject(MatSnackBar) as jest.Mocked<MatSnackBar>;
    // Ensure component uses the same snackBar mock
    (component as any).snackBar = snackBar;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('canDelete', () => {
    it('should return false when checkbox is not checked', () => {
      component.confirmCheckbox = false;
      component.confirmInput = 'test-tool';
      component.isDeleting = false;

      expect(component.canDelete).toBe(false);
    });

    it('should return false when input does not match tool_id', () => {
      component.confirmCheckbox = true;
      component.confirmInput = 'wrong-tool';
      component.isDeleting = false;

      expect(component.canDelete).toBe(false);
    });

    it('should return false when already deleting', () => {
      component.confirmCheckbox = true;
      component.confirmInput = 'test-tool';
      component.isDeleting = true;

      expect(component.canDelete).toBe(false);
    });

    it('should return true when all conditions are met', () => {
      component.confirmCheckbox = true;
      component.confirmInput = 'test-tool';
      component.isDeleting = false;

      expect(component.canDelete).toBe(true);
    });
  });

  describe('onDelete', () => {
    it('should not delete if canDelete is false', () => {
      component.confirmCheckbox = false;
      component.confirmInput = 'test-tool';

      component.onDelete();

      expect(toolService.deleteTool).not.toHaveBeenCalled();
    });

    it('should delete tool when confirmed', fakeAsync(() => {
      component.confirmCheckbox = true;
      component.confirmInput = 'test-tool';
      toolService.deleteTool.mockReturnValue(of(undefined));

      component.onDelete();
      flush();

      expect(component.isDeleting).toBe(true);
      expect(toolService.deleteTool).toHaveBeenCalledWith('uuid-1');
      expect(snackBar.open).toHaveBeenCalledWith(
        'Tool deleted successfully',
        'Close',
        { duration: 3000 }
      );
      expect(dialogRef.close).toHaveBeenCalledWith(true);
    }));

    it('should handle delete error', () => {
      component.confirmCheckbox = true;
      component.confirmInput = 'test-tool';
      const errorResponse = {
        error: { detail: 'Cannot delete tool in use' },
      };
      toolService.deleteTool.mockReturnValue(throwError(() => errorResponse));

      component.onDelete();

      expect(component.error).toBe('Cannot delete tool in use');
      expect(component.isDeleting).toBe(false);
      expect(dialogRef.close).not.toHaveBeenCalled();
    });

    it('should handle delete error without detail', () => {
      component.confirmCheckbox = true;
      component.confirmInput = 'test-tool';
      toolService.deleteTool.mockReturnValue(
        throwError(() => new Error('Network error'))
      );

      component.onDelete();

      expect(component.error).toBe('Failed to delete tool. Please try again.');
      expect(component.isDeleting).toBe(false);
    });
  });

  describe('onCancel', () => {
    it('should close dialog with false', () => {
      component.onCancel();

      expect(dialogRef.close).toHaveBeenCalledWith(false);
    });
  });
});
