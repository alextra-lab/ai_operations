import { ComponentFixture, TestBed } from '@angular/core/testing';
import { fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { InputField } from '../../api/models/use-case.models';
import { UserInteractionConfigComponent } from './user-interaction-config.component';

describe('UserInteractionConfigComponent', () => {
  let component: UserInteractionConfigComponent;
  let fixture: ComponentFixture<UserInteractionConfigComponent>;

  const inputFields: InputField[] = [
    { name: 'incident_id', type: 'text', label: 'Incident ID', required: true },
    { name: 'severity', type: 'text', label: 'Severity', required: true },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserInteractionConfigComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(UserInteractionConfigComponent);
    component = fixture.componentInstance;
    component.inputFields = [...inputFields];
    component.userPromptTemplate = {
      template: 'ID: {{incident_id}}, Severity: {{severity}}',
      variables: ['incident_id', 'severity'],
      fallback_mode: 'concatenate',
    };
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should compute sync status: synced when field and template match', () => {
    expect(component.syncStatus.length).toBe(2);
    const incident = component.syncStatus.find((s) => s.fieldName === 'incident_id');
    const severity = component.syncStatus.find((s) => s.fieldName === 'severity');
    expect(incident?.status).toBe('synced');
    expect(severity?.status).toBe('synced');
    expect(component.validationResult.isValid).toBe(true);
  });

  it('should report template_only error when template has unknown variable', () => {
    component.userPromptTemplate = {
      template: 'Note: {{analyst_notes}}',
      variables: ['analyst_notes'],
      fallback_mode: 'concatenate',
    };
    fixture.detectChanges();
    expect(component.syncStatus.some((s) => s.status === 'template_only')).toBe(true);
    expect(component.validationResult.isValid).toBe(false);
    expect(component.validationResult.errors.length).toBeGreaterThan(0);
  });

  it('should report field_only warning when field not in template', () => {
    component.userPromptTemplate = {
      template: '{{incident_id}}',
      variables: ['incident_id'],
      fallback_mode: 'concatenate',
    };
    fixture.detectChanges();
    const severityStatus = component.syncStatus.find((s) => s.fieldName === 'severity');
    expect(severityStatus?.status).toBe('field_only');
    expect(component.validationResult.warnings.length).toBe(1);
  });

  it('canGenerateTemplate should be true when template empty and fields exist', () => {
    component.userPromptTemplate = null;
    expect(component.canGenerateTemplate).toBe(true);
    component.inputFields = [];
    fixture.detectChanges();
    expect(component.canGenerateTemplate).toBe(false);
  });

  it('canGenerateTemplate should be false when template has content', () => {
    component.userPromptTemplate = {
      template: 'Some content',
      variables: [],
      fallback_mode: 'concatenate',
    };
    fixture.detectChanges();
    expect(component.canGenerateTemplate).toBe(false);
  });

  it('generateTemplate should emit template and switch to tab 1', () => {
    component.userPromptTemplate = null;
    const emitSpy = jest.spyOn(component.userPromptTemplateChange, 'emit');
    component.generateTemplate();
    expect(emitSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        template: expect.stringContaining('{{incident_id}}'),
        variables: ['incident_id', 'severity'],
        fallback_mode: 'concatenate',
      })
    );
    expect(component.selectedTabIndex()).toBe(1);
  });

  it('createFieldFromVariable should emit new field and switch to tab 0', () => {
    const emitSpy = jest.spyOn(component.inputFieldsChange, 'emit');
    component.createFieldFromVariable('analyst_notes');
    expect(emitSpy).toHaveBeenCalledWith(
      expect.arrayContaining([
        ...inputFields,
        expect.objectContaining({
          name: 'analyst_notes',
          type: 'text',
          label: 'Analyst Notes',
        }),
      ])
    );
    expect(component.selectedTabIndex()).toBe(0);
  });

  it('insertFieldIntoTemplate should append placeholder and switch to tab 1', () => {
    component.userPromptTemplate = {
      template: 'Existing',
      variables: [],
      fallback_mode: 'concatenate',
    };
    const emitSpy = jest.spyOn(component.userPromptTemplateChange, 'emit');
    component.insertFieldIntoTemplate('severity');
    expect(emitSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        template: 'Existing\n{{severity}}',
        variables: ['severity'],
      })
    );
    expect(component.selectedTabIndex()).toBe(1);
  });

  it('should emit validationChange when input fields change', fakeAsync(() => {
    const emitSpy = jest.spyOn(component.validationChange, 'emit');
    component.onInputFieldsChange([
      ...inputFields,
      { name: 'x', type: 'text', label: 'X', required: false },
    ]);
    tick(0);
    expect(emitSpy).toHaveBeenCalled();
  }));
});
