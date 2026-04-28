import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { InputField } from '../../../api/models/use-case.models';
import { DynamicFormService } from '../services/dynamic-form.service';
import { DynamicFormComponent } from './dynamic-form.component';

describe('DynamicFormComponent', () => {
  let component: DynamicFormComponent;
  let fixture: ComponentFixture<DynamicFormComponent>;
  let dynamicFormService: jest.Mocked<DynamicFormService>;

  beforeEach(async () => {
    const mockDynamicFormService = {
      generateFormGroup: jest.fn(),
      markAllAsTouched: jest.fn(),
      getFormValues: jest.fn((form, fields) => form.value),
    };

    await TestBed.configureTestingModule({
      imports: [
        ReactiveFormsModule,
        NoopAnimationsModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatExpansionModule,
        DynamicFormComponent,
      ],
      providers: [
        { provide: DynamicFormService, useValue: mockDynamicFormService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DynamicFormComponent);
    component = fixture.componentInstance;
    dynamicFormService = TestBed.inject(
      DynamicFormService
    ) as jest.Mocked<DynamicFormService>;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit', () => {
    it('should initialize form when templateConfig is provided', () => {
      const mockFormGroup = new FormGroup({
        testField: new FormControl(''),
      });
      const templateConfig = {
        input_fields: [
          {
            name: 'testField',
            type: 'text',
            label: 'Test Field',
            required: false,
          },
        ],
      } as any;

      component.templateConfig = templateConfig;
      jest
        .spyOn(dynamicFormService, 'generateFormGroup')
        .mockReturnValue(mockFormGroup);

      component.ngOnInit();

      expect(dynamicFormService.generateFormGroup).toHaveBeenCalledWith(
        templateConfig
      );
      expect(component.form).toBe(mockFormGroup);
    });
  });

  describe('ngOnChanges', () => {
    it('should reinitialize form when templateConfig changes', () => {
      const mockFormGroup = new FormGroup({
        testField: new FormControl(''),
      });
      const templateConfig = {
        input_fields: [
          {
            name: 'testField',
            type: 'text',
            label: 'Test Field',
            required: false,
          },
        ],
      } as any;

      component.templateConfig = templateConfig;
      jest
        .spyOn(dynamicFormService, 'generateFormGroup')
        .mockReturnValue(mockFormGroup);

      // Trigger ngOnChanges
      component.ngOnChanges({
        templateConfig: {
          currentValue: templateConfig,
          previousValue: null,
          firstChange: false,
          isFirstChange: () => false,
        },
      } as any);

      expect(dynamicFormService.generateFormGroup).toHaveBeenCalledWith(
        templateConfig
      );
      expect(component.form).toBe(mockFormGroup);
    });

    it('should not reinitialize form when templateConfig is unchanged', () => {
      const templateConfig = {
        input_fields: [],
      } as any;
      component.templateConfig = templateConfig;
      jest.spyOn(dynamicFormService, 'generateFormGroup').mockClear();

      component.ngOnChanges({
        initialValues: {
          currentValue: {},
          previousValue: {},
          firstChange: false,
          isFirstChange: () => false,
        },
      } as any);

      expect(dynamicFormService.generateFormGroup).not.toHaveBeenCalled();
    });
  });

  describe('onSubmit', () => {
    it('should emit formSubmitted when form is valid', () => {
      const fields: InputField[] = [
        {
          name: 'testField',
          type: 'text',
          label: 'Test Field',
          required: false,
        },
      ];

      const mockFormGroup = new FormGroup({
        testField: new FormControl('test value'),
      });
      // Mock the valid getter property
      Object.defineProperty(mockFormGroup, 'valid', {
        get: jest.fn(() => true),
        configurable: true,
      });
      jest.spyOn(component.formSubmit, 'emit');
      jest.spyOn(dynamicFormService, 'getFormValues').mockReturnValue({
        testField: 'test value',
      });

      component.fields = fields;
      component.form = mockFormGroup;

      component.onSubmit();

      expect(component.formSubmit.emit).toHaveBeenCalledWith({
        testField: 'test value',
      });
    });

    it('should mark form as touched and log error when form is invalid', () => {
      const fields: InputField[] = [
        {
          name: 'testField',
          type: 'text',
          label: 'Test Field',
          required: true,
        },
      ];

      const testControl = new FormControl('', { validators: [] });
      testControl.setErrors({ required: true });
      const mockFormGroup = new FormGroup({
        testField: testControl,
      });
      // Mock the valid getter property to return false
      Object.defineProperty(mockFormGroup, 'valid', {
        get: jest.fn(() => false),
        configurable: true,
      });
      jest.spyOn(dynamicFormService, 'markAllAsTouched');
      jest.spyOn(component.formSubmit, 'emit');

      component.fields = fields;
      component.form = mockFormGroup;

      component.onSubmit();

      expect(dynamicFormService.markAllAsTouched).toHaveBeenCalledWith(
        mockFormGroup
      );
      expect(component.formSubmit.emit).not.toHaveBeenCalled();
    });
  });

  describe('form value changes', () => {
    it('should emit formChanged when form values change', (done) => {
      const fields: InputField[] = [
        {
          name: 'testField',
          type: 'text',
          label: 'Test Field',
          required: false,
        },
      ];

      const mockFormGroup = new FormGroup({
        testField: new FormControl('initial value'),
      });
      jest.spyOn(component.formChange, 'emit');
      jest
        .spyOn(dynamicFormService, 'generateFormGroup')
        .mockReturnValue(mockFormGroup);

      component.templateConfig = { input_fields: fields, examples: [] };
      component.ngOnInit();

      // Trigger value change
      mockFormGroup.patchValue({ testField: 'new value' });

      // Wait for async valueChanges to fire
      setTimeout(() => {
        expect(component.formChange.emit).toHaveBeenCalledWith({
          testField: 'new value',
        });
        done();
      }, 0);
    });
  });

  describe('input properties', () => {
    it('should have default empty inputFields array', () => {
      expect(component.fields).toEqual([]);
    });

    it('should have formSubmit EventEmitter', () => {
      expect(component.formSubmit).toBeTruthy();
    });

    it('should have formChange EventEmitter', () => {
      expect(component.formChange).toBeTruthy();
    });
  });
});
