/**
 * Dynamic Form Component
 *
 * Main container for dynamic forms generated from use case template configs.
 * Manages form state, validation, and submission.
 */

import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
} from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import {
  InputField,
  TemplateConfig,
} from '../../../api/models/use-case.models';
import { DynamicFormService } from '../services/dynamic-form.service';
import { DynamicFieldComponent } from './dynamic-field.component';

@Component({
  selector: 'app-dynamic-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    DynamicFieldComponent,
  ],
  template: `
    <div class="dynamic-form-container">
      <form [formGroup]="form" (ngSubmit)="onSubmit()" *ngIf="form">
        <!-- Form Title (optional) -->
        <div *ngIf="title" class="mb-4">
          <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
          <p *ngIf="description" class="mt-1 text-sm text-gray-600">
            {{ description }}
          </p>
        </div>

        <!-- Dynamic Fields -->
        <div class="space-y-4">
          <app-dynamic-field
            *ngFor="let field of fields; trackBy: trackByFieldName"
            [field]="field"
            [control]="getFormControl(field.name)"
          >
          </app-dynamic-field>
        </div>

        <!-- Form Actions -->
        <div class="mt-6 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <!-- Form Status Indicator -->
            <mat-icon
              *ngIf="form.valid && form.dirty"
              class="text-green-600"
              matTooltip="Form is valid"
            >
              check_circle
            </mat-icon>
            <mat-icon
              *ngIf="form.invalid && form.dirty"
              class="text-red-600"
              matTooltip="Form has errors"
            >
              error
            </mat-icon>
            <span
              *ngIf="form.dirty"
              class="text-sm"
              [class.text-green-600]="form.valid"
              [class.text-red-600]="form.invalid"
            >
              {{ form.valid ? 'Ready to submit' : 'Please fix errors' }}
            </span>
          </div>

          <div class="flex items-center space-x-3">
            <!-- Reset Button -->
            <button
              mat-stroked-button
              type="button"
              (click)="onReset()"
              [disabled]="isSubmitting || !form.dirty"
            >
              <mat-icon>refresh</mat-icon>
              Reset
            </button>

            <!-- Submit Button -->
            <button
              mat-raised-button
              color="primary"
              type="submit"
              [disabled]="form.invalid || isSubmitting"
            >
              <mat-spinner
                *ngIf="isSubmitting"
                diameter="20"
                class="inline-block mr-2"
              >
              </mat-spinner>
              <mat-icon *ngIf="!isSubmitting">send</mat-icon>
              {{ submitButtonText }}
            </button>
          </div>
        </div>

        <!-- Validation Errors Summary (optional) -->
        <div
          *ngIf="showErrorSummary && form.invalid && form.dirty"
          class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg"
        >
          <div class="flex items-start">
            <mat-icon class="text-red-600 mt-0.5">error_outline</mat-icon>
            <div class="ml-3 flex-1">
              <h4 class="text-sm font-medium text-red-800">
                Please fix the following errors:
              </h4>
              <ul class="mt-2 text-sm text-red-700 list-disc list-inside">
                <li *ngFor="let error of getFormErrors()">{{ error }}</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Examples (optional) -->
        <div
          *ngIf="
            showExamples &&
            templateConfig.examples &&
            templateConfig.examples.length > 0
          "
          class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg"
        >
          <div class="flex items-start">
            <mat-icon class="text-blue-600 mt-0.5">lightbulb</mat-icon>
            <div class="ml-3 flex-1">
              <h4 class="text-sm font-medium text-blue-800">Examples:</h4>
              <div class="mt-2 space-y-2">
                <button
                  *ngFor="let example of templateConfig.examples; let i = index"
                  mat-button
                  type="button"
                  class="w-full text-left"
                  (click)="loadExample(example)"
                >
                  <div class="text-sm">
                    <div class="font-medium text-blue-900">
                      {{ example.title }}
                    </div>
                    <div class="text-blue-700">{{ example.description }}</div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </form>

      <!-- Loading State -->
      <div *ngIf="!form" class="flex items-center justify-center py-12">
        <mat-spinner diameter="40"></mat-spinner>
      </div>
    </div>
  `,
  styles: [
    `
      .dynamic-form-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 1rem;
      }

      .space-y-4 > * + * {
        margin-top: 1rem;
      }

      .space-x-2 > * + * {
        margin-left: 0.5rem;
      }

      .space-x-3 > * + * {
        margin-left: 0.75rem;
      }

      .mt-1 {
        margin-top: 0.25rem;
      }

      .mt-2 {
        margin-top: 0.5rem;
      }

      .mt-4 {
        margin-top: 1rem;
      }

      .mt-6 {
        margin-top: 1.5rem;
      }

      .mb-4 {
        margin-bottom: 1rem;
      }

      .mr-2 {
        margin-right: 0.5rem;
      }

      .ml-3 {
        margin-left: 0.75rem;
      }

      .p-4 {
        padding: 1rem;
      }

      .text-sm {
        font-size: 0.875rem;
        line-height: 1.25rem;
      }

      .text-lg {
        font-size: 1.125rem;
        line-height: 1.75rem;
      }

      .font-medium {
        font-weight: 500;
      }

      .font-semibold {
        font-weight: 600;
      }

      .text-gray-600 {
        color: #4b5563;
      }

      .text-gray-900 {
        color: #111827;
      }

      .text-red-600 {
        color: #dc2626;
      }

      .text-red-700 {
        color: #b91c1c;
      }

      .text-red-800 {
        color: #991b1b;
      }

      .text-green-600 {
        color: #16a34a;
      }

      .text-blue-600 {
        color: #2563eb;
      }

      .text-blue-700 {
        color: #1d4ed8;
      }

      .text-blue-800 {
        color: #1e40af;
      }

      .text-blue-900 {
        color: #1e3a8a;
      }

      .bg-red-50 {
        background-color: #fef2f2;
      }

      .bg-blue-50 {
        background-color: #eff6ff;
      }

      .border {
        border-width: 1px;
      }

      .border-red-200 {
        border-color: #fecaca;
      }

      .border-blue-200 {
        border-color: #bfdbfe;
      }

      .rounded-lg {
        border-radius: 0.5rem;
      }

      .inline-block {
        display: inline-block;
      }

      .list-disc {
        list-style-type: disc;
      }

      .list-inside {
        list-style-position: inside;
      }
    `,
  ],
})
export class DynamicFormComponent implements OnInit, OnChanges {
  @Input() templateConfig!: TemplateConfig;
  @Input() title?: string;
  @Input() description?: string;
  @Input() submitButtonText = 'Submit';
  @Input() showExamples = true;
  @Input() showErrorSummary = true;
  @Input() initialValues?: Record<string, any>;

  @Output() formSubmit = new EventEmitter<Record<string, any>>();
  @Output() formReset = new EventEmitter<void>();
  @Output() formChange = new EventEmitter<Record<string, any>>();

  form!: FormGroup;
  fields: InputField[] = [];
  isSubmitting = false;

  constructor(private dynamicFormService: DynamicFormService) {}

  ngOnInit(): void {
    this.initializeForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['templateConfig'] && !changes['templateConfig'].firstChange) {
      this.initializeForm();
    }
    if (changes['initialValues'] && !changes['initialValues'].firstChange) {
      this.loadInitialValues();
    }
  }

  /**
   * Initialize the form from template config
   */
  private initializeForm(): void {
    if (!this.templateConfig || !this.templateConfig.input_fields) {
      console.error('Template config or input_fields is missing');
      return;
    }

    this.fields = this.templateConfig.input_fields;
    this.form = this.dynamicFormService.generateFormGroup(this.templateConfig);

    // Load initial values if provided
    if (this.initialValues) {
      this.loadInitialValues();
    }

    // Subscribe to form changes
    this.form.valueChanges.subscribe((values) => {
      this.formChange.emit(values);
    });
  }

  /**
   * Load initial values into form
   */
  private loadInitialValues(): void {
    if (this.initialValues && this.form) {
      this.form.patchValue(this.initialValues);
    }
  }

  /**
   * Get form control by field name
   */
  getFormControl(fieldName: string): any {
    return this.form.get(fieldName);
  }

  /**
   * Track by function for ngFor optimization
   */
  trackByFieldName(index: number, field: InputField): string {
    return field.name;
  }

  /**
   * Get all form errors as array of strings
   */
  getFormErrors(): string[] {
    const errors = this.dynamicFormService.validateForm(this.form, this.fields);
    return Object.values(errors);
  }

  /**
   * Handle form submission
   */
  onSubmit(): void {
    if (this.form.invalid) {
      this.dynamicFormService.markAllAsTouched(this.form);
      return;
    }

    const values = this.dynamicFormService.getFormValues(
      this.form,
      this.fields
    );
    this.formSubmit.emit(values);
  }

  /**
   * Handle form reset
   */
  onReset(): void {
    this.form.reset();
    this.fields.forEach((field) => {
      const control = this.form.get(field.name);
      if (control && field.default_value !== undefined) {
        control.setValue(field.default_value);
      }
    });
    this.formReset.emit();
  }

  /**
   * Load example values into form
   */
  loadExample(example: any): void {
    if (example.inputs) {
      this.form.patchValue(example.inputs);
      this.form.markAsDirty();
    }
  }

  /**
   * Set submitting state (called by parent component)
   */
  setSubmittingState(isSubmitting: boolean): void {
    this.isSubmitting = isSubmitting;
  }
}
