import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { InputField } from '../../api/models/use-case.models';
import { InputFieldEditorComponent } from './input-field-editor.component';

describe('InputFieldEditorComponent', () => {
  let component: InputFieldEditorComponent;
  let fixture: ComponentFixture<InputFieldEditorComponent>;

  const mockField: InputField = {
    name: 'query',
    type: 'textarea',
    label: 'Query',
    required: true,
    placeholder: 'Enter query',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InputFieldEditorComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(InputFieldEditorComponent);
    component = fixture.componentInstance;
    component.field = mockField;
    component.ngOnChanges({
      field: {
        currentValue: mockField,
        firstChange: true,
        previousValue: undefined,
        isFirstChange: () => true,
      },
    });
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should build form from field input', () => {
    expect(component.form).toBeDefined();
    expect(component.form.get('name')?.value).toBe('query');
    expect(component.form.get('type')?.value).toBe('textarea');
  });
});
