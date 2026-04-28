/**
 * Dynamic Form Service
 *
 * Generates Angular Reactive Forms from Use Case Template configurations.
 * Supports all field types, validation rules, and conditional logic.
 */

import { Injectable } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormControl,
  FormGroup,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import {
  InputField,
  TemplateConfig,
} from '../../../api/models/use-case.models';

@Injectable({
  providedIn: 'root',
})
export class DynamicFormService {
  constructor(private fb: FormBuilder) {}

  /**
   * Generate a FormGroup from template configuration
   */
  generateFormGroup(templateConfig: TemplateConfig): FormGroup {
    const group: Record<string, FormControl> = {};

    templateConfig.input_fields.forEach((field) => {
      const validators = this.createValidators(field);
      const initialValue =
        field.default_value ?? this.getDefaultValueForType(field.type);

      group[field.name] = new FormControl(initialValue, validators);
    });

    return this.fb.group(group);
  }

  /**
   * Create validators for a field based on its configuration
   */
  private createValidators(field: InputField): ValidatorFn[] {
    const validators: ValidatorFn[] = [];

    // Required validator
    if (field.required) {
      validators.push(Validators.required);
    }

    // Field-specific validation
    if (field.validation) {
      const validation = field.validation;

      // Length validators
      if (validation.min_length !== undefined) {
        validators.push(Validators.minLength(validation.min_length));
      }
      if (validation.max_length !== undefined) {
        validators.push(Validators.maxLength(validation.max_length));
      }

      // Value range validators (for numbers)
      if (validation.min_value !== undefined) {
        validators.push(Validators.min(validation.min_value));
      }
      if (validation.max_value !== undefined) {
        validators.push(Validators.max(validation.max_value));
      }

      // Pattern validator (regex)
      if (validation.pattern) {
        validators.push(Validators.pattern(validation.pattern));
      }

      // Custom validator
      if (validation.custom_validator) {
        const customValidator = this.getCustomValidator(
          validation.custom_validator
        );
        if (customValidator) {
          validators.push(customValidator);
        }
      }
    }

    return validators;
  }

  /**
   * Get default value for field type
   */
  private getDefaultValueForType(type: string): any {
    switch (type) {
      case 'text':
      case 'textarea':
        return '';
      case 'number':
        return 0;
      case 'boolean':
        return false;
      case 'select':
      case 'multiselect':
        return null;
      case 'file':
        return null;
      default:
        return null;
    }
  }

  /**
   * Get custom validator by name
   * Extensible system for adding custom validation logic
   */
  private getCustomValidator(validatorName: string): ValidatorFn | null {
    const customValidators: Record<string, ValidatorFn> = {
      email: this.emailValidator,
      url: this.urlValidator,
      ipv4: this.ipv4Validator,
      ipv6: this.ipv6Validator,
      domain: this.domainValidator,
      hash_sha256: this.sha256Validator,
      hash_md5: this.md5Validator,
    };

    return customValidators[validatorName] || null;
  }

  // ============================================================================
  // Custom Validators
  // ============================================================================

  private emailValidator(control: AbstractControl): ValidationErrors | null {
    if (!control.value) {
      return null; // Don't validate empty values (use 'required' validator for that)
    }
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailPattern.test(control.value) ? null : { email: true };
  }

  private urlValidator(control: AbstractControl): ValidationErrors | null {
    if (!control.value) {
      return null;
    }
    try {
      new URL(control.value);
      return null;
    } catch {
      return { url: true };
    }
  }

  private ipv4Validator(control: AbstractControl): ValidationErrors | null {
    if (!control.value) {
      return null;
    }
    const ipv4Pattern =
      /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    return ipv4Pattern.test(control.value) ? null : { ipv4: true };
  }

  private ipv6Validator(control: AbstractControl): ValidationErrors | null {
    if (!control.value) {
      return null;
    }
    const ipv6Pattern = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::1|::)$/;
    return ipv6Pattern.test(control.value) ? null : { ipv6: true };
  }

  private domainValidator(control: AbstractControl): ValidationErrors | null {
    if (!control.value) {
      return null;
    }
    const domainPattern = /^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$/;
    return domainPattern.test(control.value) ? null : { domain: true };
  }

  private sha256Validator(control: AbstractControl): ValidationErrors | null {
    if (!control.value) {
      return null;
    }
    const sha256Pattern = /^[a-fA-F0-9]{64}$/;
    return sha256Pattern.test(control.value) ? null : { hash_sha256: true };
  }

  private md5Validator(control: AbstractControl): ValidationErrors | null {
    if (!control.value) {
      return null;
    }
    const md5Pattern = /^[a-fA-F0-9]{32}$/;
    return md5Pattern.test(control.value) ? null : { hash_md5: true };
  }

  /**
   * Get user-friendly error message for validation error
   */
  getErrorMessage(field: InputField, errors: ValidationErrors): string {
    if (!errors) {
      return '';
    }

    const fieldLabel = field.label || field.name;

    if (errors['required']) {
      return `${fieldLabel} is required`;
    }
    if (errors['minlength']) {
      return `${fieldLabel} must be at least ${errors['minlength'].requiredLength} characters`;
    }
    if (errors['maxlength']) {
      return `${fieldLabel} must not exceed ${errors['maxlength'].requiredLength} characters`;
    }
    if (errors['min']) {
      return `${fieldLabel} must be at least ${errors['min'].min}`;
    }
    if (errors['max']) {
      return `${fieldLabel} must not exceed ${errors['max'].max}`;
    }
    if (errors['pattern']) {
      return `${fieldLabel} has an invalid format`;
    }
    if (errors['email']) {
      return `${fieldLabel} must be a valid email address`;
    }
    if (errors['url']) {
      return `${fieldLabel} must be a valid URL`;
    }
    if (errors['ipv4']) {
      return `${fieldLabel} must be a valid IPv4 address`;
    }
    if (errors['ipv6']) {
      return `${fieldLabel} must be a valid IPv6 address`;
    }
    if (errors['domain']) {
      return `${fieldLabel} must be a valid domain name`;
    }
    if (errors['hash_sha256']) {
      return `${fieldLabel} must be a valid SHA-256 hash (64 hex characters)`;
    }
    if (errors['hash_md5']) {
      return `${fieldLabel} must be a valid MD5 hash (32 hex characters)`;
    }

    // Generic error message for unknown errors
    return `${fieldLabel} is invalid`;
  }

  /**
   * Validate entire form and return all errors
   */
  validateForm(form: FormGroup, fields: InputField[]): Record<string, string> {
    const errors: Record<string, string> = {};

    fields.forEach((field) => {
      const control = form.get(field.name);
      if (control && control.errors && (control.dirty || control.touched)) {
        errors[field.name] = this.getErrorMessage(field, control.errors);
      }
    });

    return errors;
  }

  /**
   * Mark all fields as touched to trigger validation display
   */
  markAllAsTouched(form: FormGroup): void {
    Object.keys(form.controls).forEach((key) => {
      const control = form.get(key);
      control?.markAsTouched();
    });
  }

  /**
   * Get form values with proper type conversions
   */
  getFormValues(form: FormGroup, fields: InputField[]): Record<string, any> {
    const values: Record<string, any> = {};

    fields.forEach((field) => {
      const control = form.get(field.name);
      if (control) {
        let value = control.value;

        // Type conversions
        if (field.type === 'number' && typeof value === 'string') {
          value = parseFloat(value);
        }
        if (field.type === 'boolean' && typeof value === 'string') {
          value = value === 'true';
        }

        values[field.name] = value;
      }
    });

    return values;
  }
}
