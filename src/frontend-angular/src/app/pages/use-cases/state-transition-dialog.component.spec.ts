/**
 * State Transition Dialog Component Tests
 *
 * Tests lifecycle state transitions, validation rules, and user confirmation.
 * ADR-012 and ADR-018 compliant testing.
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Subject } from 'rxjs';

import {
  LifecycleState,
  UseCaseResponse,
} from '../../api/models/use-case-management.models';
import {
  StateTransitionDialogComponent,
  StateTransitionDialogData,
} from './state-transition-dialog.component';

describe('StateTransitionDialogComponent', () => {
  let component: StateTransitionDialogComponent;
  let fixture: ComponentFixture<StateTransitionDialogComponent>;
  let mockDialogRef: jest.Mocked<MatDialogRef<StateTransitionDialogComponent>>;

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

  const mockDialogData: StateTransitionDialogData = {
    useCase: mockUseCase,
    targetState: LifecycleState.REVIEW,
    allowedStates: [LifecycleState.REVIEW],
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
    } as any;

    await TestBed.configureTestingModule({
      imports: [
        StateTransitionDialogComponent,
        ReactiveFormsModule,
        MatDialogModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StateTransitionDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form with target state', () => {
    expect(component.form.get('targetState')?.value).toBe(
      LifecycleState.REVIEW
    );
  });

  describe('getStateIcon', () => {
    it('should return correct icons for all states', () => {
      expect(component.getStateIcon(LifecycleState.DRAFT)).toBe('square-pen');
      expect(component.getStateIcon(LifecycleState.REVIEW)).toBe(
        'message-square-text'
      );
      expect(component.getStateIcon(LifecycleState.PUBLISHED)).toBe('upload');
      expect(component.getStateIcon(LifecycleState.ARCHIVED)).toBe('archive');
    });
  });

  describe('getStateName', () => {
    it('should return correct names for all states', () => {
      expect(component.getStateName(LifecycleState.DRAFT)).toBe('Draft');
      expect(component.getStateName(LifecycleState.REVIEW)).toBe('Review');
      expect(component.getStateName(LifecycleState.PUBLISHED)).toBe(
        'Published'
      );
      expect(component.getStateName(LifecycleState.ARCHIVED)).toBe('Archived');
    });
  });

  describe('onConfirm', () => {
    it('should close dialog with result when valid', () => {
      component.form.patchValue({
        targetState: LifecycleState.REVIEW,
        notes: 'Test notes',
      });

      component.onConfirm();

      expect(mockDialogRef.close).toHaveBeenCalledWith({
        confirmed: true,
        targetState: LifecycleState.REVIEW,
        notes: 'Test notes',
      });
    });
  });

  describe('onCancel', () => {
    it('should close dialog with confirmed false', () => {
      component.onCancel();
      expect(mockDialogRef.close).toHaveBeenCalledWith({ confirmed: false });
    });
  });
});
