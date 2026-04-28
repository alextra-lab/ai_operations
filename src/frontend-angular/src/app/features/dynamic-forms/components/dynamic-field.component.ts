/**
 * Dynamic Field Component
 *
 * Renders different field types based on configuration.
 * Handles text, textarea, select, multiselect, number, boolean, and file inputs.
 */

import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { InputField } from '../../../api/models/use-case.models';
import { DynamicFormService } from '../services/dynamic-form.service';

@Component({
  selector: 'app-dynamic-field',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatTooltipModule,
    MatIconModule,
  ],
  template: `
    <div class="dynamic-field" [ngSwitch]="field.type">
      <!-- Text Input -->
      <mat-form-field
        *ngSwitchCase="'text'"
        class="w-full"
        appearance="outline"
      >
        <mat-label>{{ field.label }}</mat-label>
        <input
          matInput
          [formControl]="control"
          [placeholder]="field.placeholder || ''"
          [required]="field.required"
          type="text"
        />
        <mat-icon
          matSuffix
          *ngIf="field.description"
          [matTooltip]="field.description"
          class="text-gray-500 cursor-help"
        >
          help_outline
        </mat-icon>
        <mat-error *ngIf="control.errors">
          {{ getErrorMessage() }}
        </mat-error>
        <mat-hint *ngIf="field.description && !control.errors">
          {{ field.description }}
        </mat-hint>
      </mat-form-field>

      <!-- Textarea Input -->
      <mat-form-field
        *ngSwitchCase="'textarea'"
        class="w-full"
        appearance="outline"
      >
        <mat-label>{{ field.label }}</mat-label>
        <textarea
          matInput
          [formControl]="control"
          [placeholder]="field.placeholder || ''"
          [required]="field.required"
          rows="4"
          cdkTextareaAutosize
          cdkAutosizeMinRows="4"
          cdkAutosizeMaxRows="12"
        >
        </textarea>
        <mat-icon
          matSuffix
          *ngIf="field.description"
          [matTooltip]="field.description"
          class="text-gray-500 cursor-help"
        >
          help_outline
        </mat-icon>
        <mat-error *ngIf="control.errors">
          {{ getErrorMessage() }}
        </mat-error>
        <mat-hint *ngIf="field.description && !control.errors">
          {{ field.description }}
        </mat-hint>
      </mat-form-field>

      <!-- Select Dropdown -->
      <mat-form-field
        *ngSwitchCase="'select'"
        class="w-full"
        appearance="outline"
      >
        <mat-label>{{ field.label }}</mat-label>
        <mat-select [formControl]="control" [required]="field.required">
          <mat-option
            *ngFor="let option of field.options"
            [value]="option.value"
          >
            {{ option.label }}
          </mat-option>
        </mat-select>
        <mat-icon
          matSuffix
          *ngIf="field.description"
          [matTooltip]="field.description"
          class="text-gray-500 cursor-help"
        >
          help_outline
        </mat-icon>
        <mat-error *ngIf="control.errors">
          {{ getErrorMessage() }}
        </mat-error>
        <mat-hint *ngIf="field.description && !control.errors">
          {{ field.description }}
        </mat-hint>
      </mat-form-field>

      <!-- Multi-Select Dropdown -->
      <mat-form-field
        *ngSwitchCase="'multiselect'"
        class="w-full"
        appearance="outline"
      >
        <mat-label>{{ field.label }}</mat-label>
        <mat-select
          [formControl]="control"
          [required]="field.required"
          multiple
        >
          <mat-option
            *ngFor="let option of field.options"
            [value]="option.value"
          >
            {{ option.label }}
          </mat-option>
        </mat-select>
        <mat-icon
          matSuffix
          *ngIf="field.description"
          [matTooltip]="field.description"
          class="text-gray-500 cursor-help"
        >
          help_outline
        </mat-icon>
        <mat-error *ngIf="control.errors">
          {{ getErrorMessage() }}
        </mat-error>
        <mat-hint *ngIf="field.description && !control.errors">
          {{ field.description }}
        </mat-hint>
      </mat-form-field>

      <!-- Number Input -->
      <mat-form-field
        *ngSwitchCase="'number'"
        class="w-full"
        appearance="outline"
      >
        <mat-label>{{ field.label }}</mat-label>
        <input
          matInput
          [formControl]="control"
          [placeholder]="field.placeholder || ''"
          [required]="field.required"
          type="number"
          [attr.min]="field.validation?.min_value ?? null"
          [attr.max]="field.validation?.max_value ?? null"
        />
        <mat-icon
          matSuffix
          *ngIf="field.description"
          [matTooltip]="field.description"
          class="text-gray-500 cursor-help"
        >
          help_outline
        </mat-icon>
        <mat-error *ngIf="control.errors">
          {{ getErrorMessage() }}
        </mat-error>
        <mat-hint *ngIf="field.description && !control.errors">
          {{ field.description }}
        </mat-hint>
      </mat-form-field>

      <!-- Boolean Checkbox -->
      <div *ngSwitchCase="'boolean'" class="flex items-center py-2">
        <mat-checkbox [formControl]="control">
          {{ field.label }}
        </mat-checkbox>
        <mat-icon
          *ngIf="field.description"
          [matTooltip]="field.description"
          class="ml-2 text-gray-500 cursor-help text-sm"
        >
          help_outline
        </mat-icon>
      </div>

      <!-- File Upload (Placeholder) -->
      <div *ngSwitchCase="'file'" class="file-upload-field">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ field.label }}
          <span *ngIf="field.required" class="text-red-500">*</span>
        </label>
        <div class="flex items-center justify-center w-full">
          <label
            class="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100"
          >
            <div class="flex flex-col items-center justify-center pt-5 pb-6">
              <mat-icon class="text-gray-400 mb-2">cloud_upload</mat-icon>
              <p class="mb-2 text-sm text-gray-500">
                <span class="font-semibold">Click to upload</span> or drag and
                drop
              </p>
              <p class="text-xs text-gray-500">
                {{ field.placeholder || 'Any file type' }}
              </p>
            </div>
            <input
              type="file"
              class="hidden"
              [required]="field.required"
              (change)="onFileSelected($event)"
            />
          </label>
        </div>
        <p *ngIf="field.description" class="mt-2 text-sm text-gray-500">
          {{ field.description }}
        </p>
        <p
          *ngIf="control.errors && control.touched"
          class="mt-1 text-sm text-red-600"
        >
          {{ getErrorMessage() }}
        </p>
      </div>

      <!-- Unsupported field type -->
      <div
        *ngSwitchDefault
        class="p-4 bg-yellow-50 border border-yellow-200 rounded"
      >
        <mat-icon class="text-yellow-600">warning</mat-icon>
        <span class="ml-2 text-sm text-yellow-700">
          Unsupported field type: {{ field.type }}
        </span>
      </div>
    </div>
  `,
  styles: [
    `
      .dynamic-field {
        margin-bottom: 1rem;
      }

      .file-upload-field {
        margin-bottom: 1rem;
      }

      mat-form-field {
        width: 100%;
      }

      .w-full {
        width: 100%;
      }

      .text-gray-500 {
        color: #6b7280;
      }

      .cursor-help {
        cursor: help;
      }
    `,
  ],
})
export class DynamicFieldComponent implements OnInit {
  @Input() field!: InputField;
  @Input() control!: FormControl;

  constructor(private dynamicFormService: DynamicFormService) {}

  ngOnInit(): void {
    if (!this.field || !this.control) {
      console.error('DynamicFieldComponent requires field and control inputs');
    }
  }

  /**
   * Get user-friendly error message
   */
  getErrorMessage(): string {
    if (!this.control.errors) {
      return '';
    }
    return this.dynamicFormService.getErrorMessage(
      this.field,
      this.control.errors
    );
  }

  /**
   * Handle file selection
   */
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.control.setValue(file);
      this.control.markAsTouched();
    }
  }
}
