import { TestBed } from '@angular/core/testing';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import {
  InputField,
  TemplateConfig,
} from '../../../api/models/use-case.models';
import { DynamicFormService } from './dynamic-form.service';

describe('DynamicFormService - Proper Test', () => {
  let service: DynamicFormService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ReactiveFormsModule],
      providers: [DynamicFormService, FormBuilder],
    });
    service = TestBed.inject(DynamicFormService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
    expect(service.generateFormGroup).toBeDefined();
    expect(service.getErrorMessage).toBeDefined();
    expect(service.validateForm).toBeDefined();
    expect(service.markAllAsTouched).toBeDefined();
    expect(service.getFormValues).toBeDefined();
  });

  it('should generate a form group from template config', () => {
    const templateConfig: TemplateConfig = {
      input_fields: [
        {
          name: 'testField',
          type: 'text',
          label: 'Test Field',
          required: true,
        },
        {
          name: 'optionalField',
          type: 'text',
          label: 'Optional Field',
          required: false,
          default_value: 'default',
        },
      ],
      output_format: 'text',
    };

    const formGroup = service.generateFormGroup(templateConfig);

    expect(formGroup).toBeTruthy();
    expect(formGroup.get('testField')).toBeTruthy();
    expect(formGroup.get('optionalField')).toBeTruthy();
    expect(formGroup.get('optionalField')?.value).toBe('default');
  });

  it('should apply validation rules', () => {
    const templateConfig: TemplateConfig = {
      input_fields: [
        {
          name: 'validatedField',
          type: 'text',
          label: 'Validated Field',
          required: true,
          validation: {
            min_length: 3,
            max_length: 10,
            pattern: '^[a-zA-Z]+$',
          },
        },
      ],
      output_format: 'text',
    };

    const formGroup = service.generateFormGroup(templateConfig);
    const control = formGroup.get('validatedField');

    // Test required validation
    expect(control?.hasError('required')).toBeTruthy();

    // Test min length
    control?.setValue('ab');
    expect(control?.hasError('minlength')).toBeTruthy();

    // Test max length
    control?.setValue('abcdefghijk');
    expect(control?.hasError('maxlength')).toBeTruthy();

    // Test pattern
    control?.setValue('123');
    expect(control?.hasError('pattern')).toBeTruthy();

    // Valid value
    control?.setValue('abcde');
    expect(control?.valid).toBeTruthy();
  });

  it('should get error messages', () => {
    const field: InputField = {
      name: 'testField',
      type: 'text',
      label: 'Test Field',
      required: true,
      validation: {
        min_length: 3,
        max_length: 10,
      },
    };

    const errors = { required: true };
    const message = service.getErrorMessage(field, errors);
    expect(message).toBe('Test Field is required');

    const minLengthErrors = {
      minlength: { requiredLength: 3, actualLength: 2 },
    };
    const minLengthMessage = service.getErrorMessage(field, minLengthErrors);
    expect(minLengthMessage).toBe('Test Field must be at least 3 characters');
  });

  it('should validate form and return errors', () => {
    const templateConfig: TemplateConfig = {
      input_fields: [
        {
          name: 'requiredField',
          type: 'text',
          label: 'Required Field',
          required: true,
        },
      ],
      output_format: 'text',
    };

    const formGroup = service.generateFormGroup(templateConfig);
    const fields = templateConfig.input_fields;

    // Form should be invalid initially - need to mark as touched first
    formGroup.get('requiredField')?.markAsTouched();
    const errors = service.validateForm(formGroup, fields);
    expect(errors['requiredField']).toBeTruthy();

    // Set valid value
    formGroup.get('requiredField')?.setValue('valid value');
    formGroup.get('requiredField')?.markAsTouched();

    const errorsAfterValid = service.validateForm(formGroup, fields);
    expect(errorsAfterValid['requiredField']).toBeFalsy();
  });

  it('should mark all fields as touched', () => {
    const templateConfig: TemplateConfig = {
      input_fields: [
        {
          name: 'field1',
          type: 'text',
          label: 'Field 1',
          required: false,
        },
        {
          name: 'field2',
          type: 'text',
          label: 'Field 2',
          required: false,
        },
      ],
      output_format: 'text',
    };

    const formGroup = service.generateFormGroup(templateConfig);

    // Initially fields should not be touched
    expect(formGroup.get('field1')?.touched).toBeFalsy();
    expect(formGroup.get('field2')?.touched).toBeFalsy();

    service.markAllAsTouched(formGroup);

    // After marking all as touched
    expect(formGroup.get('field1')?.touched).toBeTruthy();
    expect(formGroup.get('field2')?.touched).toBeTruthy();
  });

  it('should get form values with proper type conversion', () => {
    const templateConfig: TemplateConfig = {
      input_fields: [
        {
          name: 'textField',
          type: 'text',
          label: 'Text Field',
          required: false,
        },
        {
          name: 'numberField',
          type: 'number',
          label: 'Number Field',
          required: false,
        },
        {
          name: 'booleanField',
          type: 'boolean',
          label: 'Boolean Field',
          required: false,
        },
      ],
      output_format: 'text',
    };

    const formGroup = service.generateFormGroup(templateConfig);

    formGroup.get('textField')?.setValue('test');
    formGroup.get('numberField')?.setValue('42');
    formGroup.get('booleanField')?.setValue('true');

    const values = service.getFormValues(
      formGroup,
      templateConfig.input_fields
    );

    expect(values['textField']).toBe('test');
    expect(values['numberField']).toBe(42); // Should be converted to number
    expect(values['booleanField']).toBe(true); // Should be converted to boolean
  });
});
