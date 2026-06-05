/**
 * Single input field editor for the Use Case wizard.
 * Used by InputFieldBuilderComponent to edit name, type, label, validation, options.
 */

import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
} from '@angular/core';
import { Subscription } from 'rxjs';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  FieldValidation,
  InputField,
  SelectOption,
} from '../../api/models/use-case.models';
import { LucideAngularModule } from 'lucide-angular';

const NAME_PATTERN = /^[a-z_][a-z0-9_]*$/;

@Component({
  selector: 'app-input-field-editor',
  templateUrl: './input-field-editor.component.html',
  styleUrls: ['./input-field-editor.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
  ],
})
export class InputFieldEditorComponent implements OnChanges, OnDestroy {
  @Input() field!: InputField;
  @Output() fieldChange = new EventEmitter<InputField>();
  @Output() remove = new EventEmitter<void>();
  @Output() moveUp = new EventEmitter<void>();
  @Output() moveDown = new EventEmitter<void>();

  showAdvancedValidation = false;
  form!: FormGroup;
  private valueSub: Subscription | null = null;

  fieldTypes = [
    { value: 'text', label: 'Text', icon: 'type' },
    { value: 'textarea', label: 'Text Area', icon: 'sticky-note' },
    { value: 'select', label: 'Dropdown', icon: 'circle-chevron-down' },
    { value: 'number', label: 'Number', icon: 'pin' },
    { value: 'checkbox', label: 'Checkbox', icon: 'square-check' },
    { value: 'date', label: 'Date', icon: 'calendar' },
  ];

  constructor(private fb: FormBuilder) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['field'] && this.field) {
      this.buildForm();
    }
  }

  ngOnDestroy(): void {
    this.valueSub?.unsubscribe();
  }

  private buildForm(): void {
    this.valueSub?.unsubscribe();
    const v = this.field.validation;
    this.form = this.fb.group({
      name: [
        this.field.name,
        [Validators.required, Validators.pattern(NAME_PATTERN)],
      ],
      type: [this.normalizeType(this.field.type), Validators.required],
      label: [this.field.label, Validators.required],
      description: [this.field.description ?? ''],
      required: [this.field.required],
      placeholder: [this.field.placeholder ?? ''],
      default_value: [this.field.default_value ?? ''],
      options: [this.field.options ?? []],
      validation: this.fb.group({
        min_length: [v?.min_length ?? null],
        max_length: [v?.max_length ?? null],
        min_value: [v?.min_value ?? null],
        max_value: [v?.max_value ?? null],
        pattern: [v?.pattern ?? ''],
        pattern_message: [v?.pattern_message ?? ''],
      }),
    });
    this.valueSub = this.form.valueChanges.subscribe(() => this.emitField());
  }

  private normalizeType(t: string): string {
    if (t === 'boolean') return 'checkbox';
    return ['text', 'textarea', 'select', 'number', 'checkbox', 'date'].includes(t)
      ? t
      : 'text';
  }

  private emitField(): void {
    if (!this.form.valid) return;
    const v = this.form.get('validation')?.value;
    const val: FieldValidation = {};
    if (v.min_length != null && v.min_length !== '') val.min_length = +v.min_length;
    if (v.max_length != null && v.max_length !== '') val.max_length = +v.max_length;
    if (v.min_value != null && v.min_value !== '') val.min_value = +v.min_value;
    if (v.max_value != null && v.max_value !== '') val.max_value = +v.max_value;
    if (v.pattern) val.pattern = v.pattern;
    if (v.pattern_message) val.pattern_message = v.pattern_message;

    const raw = this.form.get('default_value')?.value;
    let default_value: string | number | boolean | undefined = raw;
    if (this.form.get('type')?.value === 'number' && raw !== '' && raw != null) {
      default_value = Number(raw);
    }
    if (this.form.get('type')?.value === 'checkbox') {
      default_value = raw === true || raw === 'true';
    }

    this.fieldChange.emit({
      name: this.form.get('name')?.value?.trim(),
      type: this.form.get('type')?.value,
      label: this.form.get('label')?.value?.trim(),
      description: this.form.get('description')?.value?.trim() || undefined,
      required: !!this.form.get('required')?.value,
      placeholder: this.form.get('placeholder')?.value?.trim() || undefined,
      default_value: default_value === '' ? undefined : default_value,
      options: this.form.get('options')?.value ?? undefined,
      validation: Object.keys(val).length ? val : undefined,
    });
  }

  get options(): SelectOption[] {
    return this.form?.get('options')?.value ?? [];
  }

  addOption(): void {
    const opts = [...(this.form.get('options')?.value ?? [])];
    opts.push({ value: '', label: '' });
    this.form.get('options')?.setValue(opts);
  }

  removeOption(i: number): void {
    const opts = [...(this.form.get('options')?.value ?? [])];
    opts.splice(i, 1);
    this.form.get('options')?.setValue(opts);
  }

  onOptionChange(i: number, key: 'value' | 'label', value: string): void {
    const opts = [...(this.form.get('options')?.value ?? [])];
    if (opts[i]) opts[i] = { ...opts[i], [key]: value };
    this.form.get('options')?.setValue(opts);
  }

  get isSelect(): boolean {
    return this.form?.get('type')?.value === 'select';
  }
}
