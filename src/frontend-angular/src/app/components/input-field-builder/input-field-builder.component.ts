/**
 * Input fields builder for the Use Case wizard Step 4.
 * Manages add/remove/reorder of input fields and emits the current list.
 */

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';

import { InputField } from '../../api/models/use-case.models';
import { InputFieldEditorComponent } from '../input-field-editor/input-field-editor.component';
import { LucideAngularModule } from 'lucide-angular';

const DEFAULT_FIELD: InputField = {
  name: 'query',
  type: 'textarea',
  label: 'Query',
  description: 'Enter your question or request',
  required: true,
  placeholder: 'What would you like to know?',
};

@Component({
  selector: 'app-input-field-builder',
  templateUrl: './input-field-builder.component.html',
  styleUrls: ['./input-field-builder.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatButtonModule,
    MatExpansionModule,
    InputFieldEditorComponent,
  ],
})
export class InputFieldBuilderComponent {
  @Input() fields: InputField[] = [];
  @Output() fieldsChange = new EventEmitter<InputField[]>();

  addField(): void {
    const name = this.nextFieldName();
    const newField: InputField = {
      ...DEFAULT_FIELD,
      name,
      label: name.replace(/_/g, ' '),
      placeholder: '',
    };
    const next = [...this.fields, newField];
    this.fieldsChange.emit(next);
  }

  removeField(index: number): void {
    const next = this.fields.filter((_, i) => i !== index);
    this.fieldsChange.emit(next);
  }

  moveField(from: number, to: number): void {
    if (to < 0 || to >= this.fields.length) return;
    const next = [...this.fields];
    const [removed] = next.splice(from, 1);
    next.splice(to, 0, removed);
    this.fieldsChange.emit(next);
  }

  onFieldChange(index: number, field: InputField): void {
    const next = [...this.fields];
    next[index] = field;
    this.fieldsChange.emit(next);
  }

  private nextFieldName(): string {
    const base = 'field';
    let n = 1;
    const names = new Set(this.fields.map((f) => f.name));
    while (names.has(`${base}_${n}`)) n++;
    return `${base}_${n}`;
  }
}
