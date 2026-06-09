import { ComponentFixture, TestBed } from '@angular/core/testing';

import type { FieldSyncStatus } from '../user-interaction-config/user-interaction-config.component';
import { FieldTemplateSyncStatusComponent } from './field-template-sync-status.component';

describe('FieldTemplateSyncStatusComponent', () => {
  let component: FieldTemplateSyncStatusComponent;
  let fixture: ComponentFixture<FieldTemplateSyncStatusComponent>;

  const statuses: FieldSyncStatus[] = [
    { fieldName: 'a', status: 'synced', message: 'Defined and used' },
    { fieldName: 'b', status: 'field_only', message: 'Defined but NOT used' },
    { fieldName: 'c', status: 'template_only', message: 'NO field defined' },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FieldTemplateSyncStatusComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(FieldTemplateSyncStatusComponent);
    component = fixture.componentInstance;
    component.statuses = statuses;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should split statuses into synced, warning, error', () => {
    expect(component.syncedItems).toHaveLength(1);
    expect(component.syncedItems[0].fieldName).toBe('a');
    expect(component.warningItems).toHaveLength(1);
    expect(component.warningItems[0].fieldName).toBe('b');
    expect(component.errorItems).toHaveLength(1);
    expect(component.errorItems[0].fieldName).toBe('c');
  });

  it('should have hasAnyItems true when statuses exist', () => {
    expect(component.hasAnyItems).toBe(true);
    component.statuses = [];
    expect(component.hasAnyItems).toBe(false);
  });

  it('should return correct icon and class per status', () => {
    expect(component.getIcon('synced')).toBe('circle-check');
    expect(component.getIcon('field_only')).toBe('triangle-alert');
    expect(component.getIcon('template_only')).toBe('circle-alert');
    expect(component.getIconClass('synced')).toBe('text-green-600');
    expect(component.getIconClass('field_only')).toBe('text-amber-600');
    expect(component.getIconClass('template_only')).toBe('text-red-600');
  });

  it('should emit createField when onCreateField called', () => {
    const emitSpy = jest.spyOn(component.createField, 'emit');
    component.onCreateField('new_var');
    expect(emitSpy).toHaveBeenCalledWith('new_var');
  });

  it('should emit insertIntoTemplate when onInsertIntoTemplate called', () => {
    const emitSpy = jest.spyOn(component.insertIntoTemplate, 'emit');
    component.onInsertIntoTemplate('field_name');
    expect(emitSpy).toHaveBeenCalledWith('field_name');
  });
});
