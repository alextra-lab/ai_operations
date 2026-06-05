/**
 * State Transition Confirmation Dialog Component
 *
 * Confirms lifecycle state transitions for Use Cases.
 * Validates transition rules and displays warnings/requirements.
 *
 * ADR-012 Compliant: Material components for UI primitives
 */

import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { LucideAngularModule } from 'lucide-angular';
import {
  LifecycleState,
  UseCaseResponse,
} from '../../api/models/use-case-management.models';

export interface StateTransitionDialogData {
  useCase: UseCaseResponse;
  targetState: string;
  allowedStates: string[];
}

export interface StateTransitionDialogResult {
  confirmed: boolean;
  targetState: string;
  notes?: string;
}

@Component({
  selector: 'app-state-transition-dialog',
  templateUrl: './state-transition-dialog.component.html',
  styleUrls: ['./state-transition-dialog.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
})
export class StateTransitionDialogComponent {
  form: FormGroup;
  LifecycleState = LifecycleState;

  constructor(
    private dialogRef: MatDialogRef<StateTransitionDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: StateTransitionDialogData,
    private fb: FormBuilder
  ) {
    this.form = this.fb.group({
      targetState: [data.targetState, Validators.required],
      notes: [''],
    });

    // Require notes for publishing
    if (data.targetState === LifecycleState.PUBLISHED) {
      this.form
        .get('notes')
        ?.setValidators([Validators.required, Validators.minLength(10)]);
    }
  }

  getStateIcon(state: string): string {
    const icons: Record<string, string> = {
      draft: 'square-pen',
      review: 'message-square-text',
      published: 'upload',
      archived: 'archive',
    };
    return icons[state] || 'circle-help';
  }

  getStateName(state: string): string {
    const names: Record<string, string> = {
      draft: 'Draft',
      review: 'Review',
      published: 'Published',
      archived: 'Archived',
    };
    return names[state] || state;
  }

  getStateColor(state: string): string {
    const colors: Record<string, string> = {
      draft: 'text-gray-600',
      review: 'text-yellow-600',
      published: 'text-green-600',
      archived: 'text-red-600',
    };
    return colors[state] || 'text-gray-600';
  }

  getWarningMessage(): string | null {
    const target = this.form.get('targetState')?.value;
    const current = this.data.useCase.lifecycle_state;

    if (current === 'published' && target === 'draft') {
      return 'This will unpublish the use case and make it unavailable for execution.';
    }
    if (target === 'archived') {
      return 'Archived use cases cannot be executed. You can restore them later.';
    }
    if (
      target === 'published' &&
      !this.data.useCase.config_json?.['models']?.['llm']
    ) {
      return 'This use case has incomplete configuration. Publishing may fail validation.';
    }
    return null;
  }

  getRequirementMessage(): string | null {
    const target = this.form.get('targetState')?.value;

    if (target === 'published') {
      return 'Publishing requires admin approval and complete configuration.';
    }
    if (target === 'review') {
      return 'Use case will be submitted for review by an administrator.';
    }
    return null;
  }

  onConfirm(): void {
    if (this.form.valid) {
      const result: StateTransitionDialogResult = {
        confirmed: true,
        targetState: this.form.get('targetState')?.value,
        notes: this.form.get('notes')?.value || undefined,
      };
      this.dialogRef.close(result);
    }
  }

  onCancel(): void {
    this.dialogRef.close({ confirmed: false });
  }
}
