import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { InputField } from '../../api/models/use-case.models';
import { InputFieldBuilderComponent } from './input-field-builder.component';

describe('InputFieldBuilderComponent', () => {
  let component: InputFieldBuilderComponent;
  let fixture: ComponentFixture<InputFieldBuilderComponent>;

  const mockFields: InputField[] = [
    {
      name: 'query',
      type: 'textarea',
      label: 'Query',
      required: true,
    },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InputFieldBuilderComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(InputFieldBuilderComponent);
    component = fixture.componentInstance;
    component.fields = [...mockFields];
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should add field and emit', () => {
    const emitSpy = jest.spyOn(component.fieldsChange, 'emit');
    component.addField();
    expect(emitSpy).toHaveBeenCalled();
    expect(emitSpy.mock.calls[0][0].length).toBe(2);
  });

  it('should remove field and emit', () => {
    const emitSpy = jest.spyOn(component.fieldsChange, 'emit');
    component.removeField(0);
    expect(emitSpy).toHaveBeenCalledWith([]);
  });
});
