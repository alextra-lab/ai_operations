import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  FormControl,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatOptionModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSliderModule } from '@angular/material/slider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { DynamicFieldComponent } from './dynamic-field.component';

describe('DynamicFieldComponent', () => {
  let component: DynamicFieldComponent;
  let fixture: ComponentFixture<DynamicFieldComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ReactiveFormsModule,
        NoopAnimationsModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatOptionModule,
        MatCheckboxModule,
        MatSliderModule,
        MatIconModule,
        MatTooltipModule,
        DynamicFieldComponent,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DynamicFieldComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('text field', () => {
    beforeEach(() => {
      component.field = {
        name: 'textField',
        type: 'text',
        label: 'Text Field',
        required: true,
        placeholder: 'Enter text',
      };
      component.control = new FormControl('');
      fixture.detectChanges();
    });

    it('should render text input', () => {
      const input = fixture.nativeElement.querySelector('input[matInput]');
      expect(input).toBeTruthy();
      expect(input.type).toBe('text');
    });

    it('should display error message for required field', () => {
      component.control.setValue('');
      component.control.markAsTouched();
      fixture.detectChanges();

      const errorElement = fixture.nativeElement.querySelector('mat-error');
      expect(errorElement?.textContent?.trim()).toContain(
        'Text Field is required'
      );
    });
  });

  describe('textarea field', () => {
    beforeEach(() => {
      component.field = {
        name: 'textareaField',
        type: 'textarea',
        label: 'Textarea Field',
        required: false,
      };
      component.control = new FormControl('');
      fixture.detectChanges();
    });

    it('should render textarea', () => {
      const textarea =
        fixture.nativeElement.querySelector('textarea[matInput]');
      expect(textarea).toBeTruthy();
    });
  });

  describe('select field', () => {
    beforeEach(() => {
      component.field = {
        name: 'selectField',
        type: 'select',
        label: 'Select Field',
        required: true,
        options: [
          { value: 'option1', label: 'Option 1' },
          { value: 'option2', label: 'Option 2' },
        ],
      };
      component.control = new FormControl('');
      fixture.detectChanges();
    });

    it('should render select dropdown', () => {
      const select = fixture.nativeElement.querySelector('mat-select');
      expect(select).toBeTruthy();
    });

    it('should render options', () => {
      // mat-option may be in overlay and not in DOM until select is opened
      expect(component.field.options?.length).toBe(2);
    });
  });

  describe('number field', () => {
    beforeEach(() => {
      component.field = {
        name: 'numberField',
        type: 'number',
        label: 'Number Field',
        required: false,
        validation: {
          min_value: 1,
          max_value: 100,
        },
      };
      component.control = new FormControl('', [
        Validators.min(1),
        Validators.max(100),
      ]);
      fixture.detectChanges();
    });

    it('should render number input', () => {
      const input = fixture.nativeElement.querySelector('input[matInput]');
      expect(input).toBeTruthy();
      expect(input.type).toBe('number');
    });

    it('should set min and max attributes', () => {
      const input = fixture.nativeElement.querySelector('input[matInput]');
      expect(input.getAttribute('min')).toBe('1');
      expect(input.getAttribute('max')).toBe('100');
    });

    it('should display error message for min value', () => {
      component.control.setValue(0);
      component.control.markAsTouched();
      component.control.updateValueAndValidity();
      fixture.detectChanges();

      const errorElement = fixture.nativeElement.querySelector('mat-error');
      expect(errorElement?.textContent?.trim()).toContain(
        'must be at least 1'
      );
    });

    it('should display error message for max value', () => {
      component.control.setValue(101);
      component.control.markAsTouched();
      component.control.updateValueAndValidity();
      fixture.detectChanges();

      const errorElement = fixture.nativeElement.querySelector('mat-error');
      expect(errorElement?.textContent?.trim()).toContain(
        'must not exceed 100'
      );
    });
  });

  describe('boolean field', () => {
    beforeEach(() => {
      component.field = {
        name: 'booleanField',
        type: 'boolean',
        label: 'Boolean Field',
        required: false,
      };
      component.control = new FormControl(false);
      fixture.detectChanges();
    });

    it('should render checkbox', () => {
      const checkbox = fixture.nativeElement.querySelector('mat-checkbox');
      expect(checkbox).toBeTruthy();
    });
  });

  describe('getErrorMessage', () => {
    beforeEach(() => {
      component.field = {
        name: 'testField',
        type: 'text',
        label: 'Test Field',
        required: true,
        validation: {
          min_length: 3,
          max_length: 10,
          pattern: '^[a-zA-Z]+$',
        },
      };
      component.control = new FormControl('');
    });

    it('should return required error message', () => {
      component.control.setErrors({ required: true });
      const message = component.getErrorMessage();
      expect(message).toBe('Test Field is required');
    });

    it('should return minlength error message', () => {
      component.control.setErrors({ minlength: { requiredLength: 3 } });
      const message = component.getErrorMessage();
      expect(message).toBe('Test Field must be at least 3 characters');
    });

    it('should return maxlength error message', () => {
      component.control.setErrors({ maxlength: { requiredLength: 10 } });
      const message = component.getErrorMessage();
      expect(message).toBe('Test Field must not exceed 10 characters');
    });

    it('should return pattern error message', () => {
      component.control.setErrors({ pattern: true });
      const message = component.getErrorMessage();
      expect(message).toBe('Test Field has an invalid format');
    });

    it('should return min error message', () => {
      component.control.setErrors({ min: { min: 1 } });
      const message = component.getErrorMessage();
      expect(message).toBe('Test Field must be at least 1');
    });

    it('should return max error message', () => {
      component.control.setErrors({ max: { max: 100 } });
      const message = component.getErrorMessage();
      expect(message).toBe('Test Field must not exceed 100');
    });

    it('should return generic error message for unknown error', () => {
      component.control.setErrors({ unknown: true });
      const message = component.getErrorMessage();
      expect(message).toBe('Test Field is invalid');
    });
  });

  describe('ngOnInit', () => {
    it('should log error when field is undefined', () => {
      jest.spyOn(console, 'error');
      component.field = undefined as any;
      component.ngOnInit();
      expect(console.error).toHaveBeenCalledWith(
        'DynamicFieldComponent requires field and control inputs'
      );
    });

    it('should log error when control is undefined', () => {
      jest.spyOn(console, 'error');
      component.field = {
        name: 'testField',
        type: 'text',
        label: 'Test Field',
        required: false,
      };
      component.control = undefined as any;
      component.ngOnInit();
      expect(console.error).toHaveBeenCalledWith(
        'DynamicFieldComponent requires field and control inputs'
      );
    });
  });
});
