/**
 * Use Case List Component Tests
 *
 * Tests for CRUD operations, lifecycle transitions, and layout normalization.
 * ADR-012 and ADR-018 compliant testing.
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of } from 'rxjs';

import {
  LifecycleState,
  UseCaseResponse,
} from '../../api/models/use-case-management.models';
import { UseCaseManagementService } from '../../api/services/use-case-management.service';
import { UseCaseListComponent } from './use-case-list.component';

describe('UseCaseListComponent', () => {
  let component: UseCaseListComponent;
  let fixture: ComponentFixture<UseCaseListComponent>;
  let mockService: jest.Mocked<UseCaseManagementService>;
  let mockDialog: jest.Mocked<MatDialog>;
  let mockSnackBar: jest.Mocked<MatSnackBar>;
  let mockRouter: jest.Mocked<Router>;

  const mockUseCase: UseCaseResponse = {
    id: '123e4567-e89b-12d3-a456-426614174000',
    use_case_id: 'test-use-case',
    name: 'Test Use Case',
    description: 'Test description',
    category: 'security',
    intent_type: 'QUERY',
    version: 1,
    lifecycle_state: LifecycleState.DRAFT,
    is_active: false,
    config_json: { models: { llm: 'test-model' } },
    metadata_json: {},
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  beforeEach(async () => {
    mockService = {
      listUseCases: jest.fn().mockReturnValue(
        of({
          use_cases: [mockUseCase],
          total_count: 1,
        })
      ),
      getAllowedNextStates: jest.fn().mockReturnValue([LifecycleState.REVIEW]),
      getLifecycleStateName: jest.fn().mockReturnValue('Draft'),
      getLifecycleStateIcon: jest.fn().mockReturnValue('edit_note'),
      getLifecycleStateClass: jest.fn().mockReturnValue('bg-gray-100'),
      deleteUseCase: jest.fn(),
      cloneUseCase: jest.fn(),
      transitionState: jest.fn(),
    } as any;

    mockDialog = {
      open: jest.fn(),
    } as any;

    mockSnackBar = {
      open: jest.fn(),
    } as any;

    mockRouter = {
      navigate: jest.fn(),
    } as any;

    await TestBed.configureTestingModule({
      imports: [
        UseCaseListComponent,
        ReactiveFormsModule,
        MatDialogModule,
        MatSnackBarModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: UseCaseManagementService, useValue: mockService },
        { provide: MatDialog, useValue: mockDialog },
        { provide: MatSnackBar, useValue: mockSnackBar },
        { provide: Router, useValue: mockRouter },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UseCaseListComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load use cases on init', () => {
    fixture.detectChanges();
    expect(mockService.listUseCases).toHaveBeenCalled();
    expect(component.useCases.length).toBe(1);
  });

  describe('Lifecycle Management', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should check if use case can transition', () => {
      const canTransition = component.canTransition(mockUseCase);
      expect(canTransition).toBe(true);
      expect(mockService.getAllowedNextStates).toHaveBeenCalledWith(
        mockUseCase.lifecycle_state
      );
    });

    it('should get allowed next states', () => {
      const result = component.getAllowedNextStates(mockUseCase);
      expect(result).toEqual([LifecycleState.REVIEW]);
    });

    it('should transition via helper methods', () => {
      // Mock dialog to prevent actual opening
      const spy = jest
        .spyOn(component, 'transitionState')
        .mockImplementation(() => {});

      component.sendToReview(mockUseCase);
      expect(spy).toHaveBeenCalledWith(mockUseCase, LifecycleState.REVIEW);

      // publishUseCase should only work for review state, but method still exists
      // The actual validation happens in transitionState via getAllowedNextStates
      const reviewUseCase = {
        ...mockUseCase,
        lifecycle_state: LifecycleState.REVIEW,
      };
      mockService.getAllowedNextStates.mockReturnValue([
        LifecycleState.PUBLISHED,
        LifecycleState.DRAFT,
      ]);
      component.publishUseCase(reviewUseCase);
      expect(spy).toHaveBeenCalledWith(reviewUseCase, LifecycleState.PUBLISHED);

      const publishedUseCase = {
        ...mockUseCase,
        lifecycle_state: LifecycleState.PUBLISHED,
      };
      mockService.getAllowedNextStates.mockReturnValue([
        LifecycleState.ARCHIVED,
      ]);
      component.archiveUseCase(publishedUseCase);
      expect(spy).toHaveBeenCalledWith(
        publishedUseCase,
        LifecycleState.ARCHIVED
      );

      mockService.getAllowedNextStates.mockReturnValue([
        LifecycleState.PUBLISHED,
        LifecycleState.DRAFT,
      ]);
      component.returnToDraft(reviewUseCase);
      expect(spy).toHaveBeenCalledWith(reviewUseCase, LifecycleState.DRAFT);
    });
  });

  describe('Permission Checks', () => {
    it('should not allow deleting published use cases', () => {
      const publishedUseCase = {
        ...mockUseCase,
        lifecycle_state: LifecycleState.PUBLISHED,
      };
      expect(component.canDelete(publishedUseCase)).toBe(false);
    });

    it('should allow deleting draft use cases', () => {
      expect(component.canDelete(mockUseCase)).toBe(true);
    });
  });

  describe('Navigation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should navigate to create wizard', () => {
      component.createUseCase();
      expect(mockRouter.navigate).toHaveBeenCalledWith([
        '/dev/use-cases/wizard',
      ]);
    });

    it('should navigate to edit page', () => {
      component.editUseCase(mockUseCase);
      expect(mockRouter.navigate).toHaveBeenCalledWith([
        '/dev/use-cases/edit',
        mockUseCase.id, // Component uses id, not use_case_id
      ]);
    });
  });
});
