/**
 * Provider Create Dialog Component
 *
 * Dialog for creating new Inference Gateway providers.
 */

import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  CreateProviderRequest,
  ProviderStatus,
  ProviderType,
} from '../../models/provider-management.models';
import { ProviderManagementService } from '../../services/provider-management.service';

@Component({
  selector: 'app-provider-create-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
  ],
  templateUrl: './provider-create-dialog.component.html',
  styleUrls: ['./provider-create-dialog.component.scss'],
})
export class ProviderCreateDialogComponent {
  form: FormGroup;
  isSubmitting = false;
  error: string | null = null;

  providerTypes: ProviderType[] = [
    'openai',
    'mistral',
    'anthropic',
    'local',
    'custom',
  ];
  statuses: ProviderStatus[] = ['active', 'disabled', 'error', 'testing'];

  constructor(
    private fb: FormBuilder,
    private providerService: ProviderManagementService,
    private dialogRef: MatDialogRef<ProviderCreateDialogComponent>
  ) {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(255)]],
      provider_type: ['openai', Validators.required],
      base_url: ['', [Validators.required, Validators.maxLength(500)]],
      api_key: [''],
      is_enabled: [true],
      status: ['testing', Validators.required],
      priority: [100, [Validators.required, Validators.min(0)]],
      health_check_url: [''],
    });
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.error = null;

    const request: CreateProviderRequest = {
      name: this.form.value.name,
      provider_type: this.form.value.provider_type,
      base_url: this.form.value.base_url,
      api_key: this.form.value.api_key || undefined,
      is_enabled: this.form.value.is_enabled,
      status: this.form.value.status,
      priority: this.form.value.priority,
      health_check_url: this.form.value.health_check_url || undefined,
    };

    this.providerService.createProvider(request).subscribe({
      next: () => {
        this.dialogRef.close(true);
      },
      error: (err) => {
        console.error('Error creating provider:', err);
        this.error =
          err.error?.detail || 'Failed to create provider. Please try again.';
        this.isSubmitting = false;
      },
    });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }
}
