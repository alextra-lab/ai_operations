import { ComponentFixture, TestBed } from '@angular/core/testing';

import { InputField } from '../../api/models/use-case.models';
import { UserPromptTemplateEditorComponent } from './user-prompt-template-editor.component';

describe('UserPromptTemplateEditorComponent', () => {
  let component: UserPromptTemplateEditorComponent;
  let fixture: ComponentFixture<UserPromptTemplateEditorComponent>;

  const inputFields: InputField[] = [
    {
      name: 'incident_id',
      type: 'text',
      label: 'Incident ID',
      required: true,
    },
    {
      name: 'severity',
      type: 'select',
      label: 'Severity',
      required: true,
      options: [{ value: 'high', label: 'High' }],
    },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserPromptTemplateEditorComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(UserPromptTemplateEditorComponent);
    component = fixture.componentInstance;
    component.inputFields = inputFields;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should expose variable chips from input fields', () => {
    expect(component.variableChips).toHaveLength(2);
    expect(component.variableChips.map((c) => c.name)).toEqual([
      'incident_id',
      'severity',
    ]);
    expect(component.variableChips[0].placeholder).toBe('{{incident_id}}');
  });

  it('should emit null when template is empty', () => {
    const emitSpy = jest.spyOn(component.valueChange, 'emit');
    component.onTemplateInput('');
    expect(emitSpy).toHaveBeenCalledWith(null);
  });

  it('should emit config with extracted variables when template has placeholders', () => {
    const emitSpy = jest.spyOn(component.valueChange, 'emit');
    component.value = {
      template: '',
      variables: [],
      fallback_mode: 'concatenate',
    };
    component.onTemplateInput('Analyze {{incident_id}} with {{severity}}.');
    expect(emitSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        template: 'Analyze {{incident_id}} with {{severity}}.',
        variables: expect.arrayContaining(['incident_id', 'severity']),
        fallback_mode: 'concatenate',
      })
    );
  });

  it('should toggle preview', () => {
    expect(component.showPreview()).toBe(false);
    component.togglePreview();
    expect(component.showPreview()).toBe(true);
    component.togglePreview();
    expect(component.showPreview()).toBe(false);
  });
});
