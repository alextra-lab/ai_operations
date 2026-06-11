/**
 * Configuration Editor Component
 *
 * Schema-driven form generator for configuration editing.
 * Generates Angular Reactive Forms from JSON Schema.
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { Subscription } from 'rxjs';

import { LucideAngularModule } from 'lucide-angular';
import { Model } from '../../../../../api/models/model-registry.models';
import { ModelRegistryService } from '../../../../../api/services/model-registry.service';
import {
  ConfigSchema,
  ConfigSection,
  SchemaProperty,
} from '../../models/system-config.models';
import { SystemConfigService } from '../../services/system-config.service';

@Component({
  selector: 'app-config-editor',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatChipsModule,
  ],
  templateUrl: './config-editor.component.html',
  styleUrls: ['./config-editor.component.scss'],
})
export class ConfigEditorComponent implements OnInit, OnChanges, OnDestroy {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  @Input() section!: ConfigSection;
  @Input() config: Record<string, unknown> | null = null;
  @Output() configChange = new EventEmitter<Record<string, unknown>>();

  form: FormGroup;
  schema: ConfigSchema | null = null;
  isLoading = false;

  private valueChangesSub?: Subscription;

  // Allowed file types per backend validator
  readonly allowedFileTypesOptions: string[] = [
    'pdf',
    'txt',
    'docx',
    'md',
    'csv',
    'json',
    'xml',
    'html',
  ];

  // Embedding models for dropdown
  embeddingModels: Model[] = [];
  selectedModelInvalid = false;

  constructor(
    private fb: FormBuilder,
    private configService: SystemConfigService,
    private modelRegistryService: ModelRegistryService
  ) {
    this.form = this.fb.group({});
  }

  ngOnInit(): void {
    this.loadSchema();
    this.loadEmbeddingModels();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (
      (changes['config'] || changes['section']) &&
      this.schema &&
      this.config
    ) {
      this.buildForm();
    }
  }

  ngOnDestroy(): void {
    this.valueChangesSub?.unsubscribe();
  }

  /**
   * Load JSON schema for section
   */
  loadSchema(): void {
    this.isLoading = true;

    this.configService.getConfigSchema(this.section).subscribe({
      next: (schema) => {
        this.schema = schema;
        this.isLoading = false;
        this.cdr.detectChanges();
        if (this.config) {
          this.buildForm();
        }
      },
      error: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  /**
   * Build reactive form from schema
   */
  buildForm(): void {
    if (!this.schema || !this.config) {
      return;
    }

    const formControls: Record<string, unknown> = {};

    Object.keys(this.schema.properties).forEach((key) => {
      const rawProperty = this.schema!.properties[key];
      const property = this.resolveSchemaProperty(rawProperty);
      const value = this.config![key];

      // Handle nested objects (like password_policy)
      if (property.type === 'object' && property.properties) {
        const nestedControls: Record<string, unknown> = {};
        Object.keys(property.properties).forEach((nestedKey) => {
          const nestedProp = property.properties![nestedKey];
          const nestedValue = (value as Record<string, unknown>)[nestedKey];
          nestedControls[nestedKey] = [
            nestedValue,
            this.getValidators(nestedProp),
          ];
        });
        formControls[key] = this.fb.group(nestedControls);
      } else {
        formControls[key] = [value, this.getValidators(property)];
      }
    });

    this.form = this.fb.group(formControls);

    // Clean up previous subscription
    this.valueChangesSub?.unsubscribe();

    // Emit changes
    this.valueChangesSub = this.form.valueChanges.subscribe(() => {
      if (this.form.valid) {
        this.configChange.emit(this.form.value);
      }
    });
  }

  onToggleArrayItem(fieldKey: string, item: string, checked: boolean): void {
    const control = this.form.get(fieldKey);
    if (!control) {
      return;
    }
    const currentValue = Array.isArray(control.value)
      ? (control.value as string[])
      : [];
    const next = [...currentValue];
    const index = next.indexOf(item);
    if (checked && index === -1) {
      next.push(item);
    } else if (!checked && index !== -1) {
      next.splice(index, 1);
    }
    control.setValue(next);
    control.markAsDirty();
    control.updateValueAndValidity();
  }

  isArrayItemSelected(fieldKey: string, item: string): boolean {
    const control = this.form.get(fieldKey);
    const currentValue = Array.isArray(control?.value)
      ? (control!.value as string[])
      : [];
    return currentValue.includes(item);
  }

  /**
   * Get validators for property
   */
  getValidators(property: SchemaProperty): ValidatorFn[] {
    const validators: ValidatorFn[] = [];

    if (property.type === 'integer' || property.type === 'number') {
      validators.push(Validators.required);
      if (property.minimum !== undefined) {
        validators.push(Validators.min(property.minimum));
      }
      if (property.maximum !== undefined) {
        validators.push(Validators.max(property.maximum));
      }
    }

    return validators;
  }

  /**
   * Get property from schema
   */
  getProperty(key: string): SchemaProperty | null {
    const raw = this.schema?.properties[key] || null;
    return this.resolveSchemaProperty(raw);
  }

  /**
   * Check if property is nested object
   */
  isNestedObject(key: string): boolean {
    const prop = this.getProperty(key);
    return !!(prop && prop.type === 'object' && prop.properties);
  }

  /**
   * Get nested properties
   */
  getNestedProperties(key: string): [string, SchemaProperty][] {
    const prop = this.getProperty(key);
    if (!prop?.properties) {
      return [];
    }
    return Object.entries(prop.properties);
  }

  /**
   * Get object keys for iteration
   */
  getKeys(obj: Record<string, unknown>): string[] {
    return Object.keys(obj);
  }

  /**
   * Get FormGroup for nested object
   */
  getNestedFormGroup(key: string): FormGroup {
    return this.form.get(key) as FormGroup;
  }

  /**
   * Load available embedding models
   */
  private loadEmbeddingModels(): void {
    this.modelRegistryService.getEmbeddingModels().subscribe({
      next: (models: Model[]) => {
        this.embeddingModels = models;
        this.validateCurrentEmbeddingModel();
      },
      error: (err: Error) => {
        console.error('Failed to load embedding models', err);
      },
    });
  }

  /**
   * Validate that current embedding model is available
   */
  private validateCurrentEmbeddingModel(): void {
    const control = this.form.get('default_embedding_model');
    if (!control) {
      return;
    }

    const currentValue = control.value;
    if (currentValue && this.embeddingModels.length > 0) {
      this.selectedModelInvalid = !this.embeddingModels.some(
        (m) => m.model_id === currentValue && m.is_available
      );
    }

    // Re-validate when value changes
    control.valueChanges.subscribe(() => {
      this.validateCurrentEmbeddingModel();
    });
  }

  /**
   * Resolve JSON Schema $ref to a concrete SchemaProperty using $defs
   */
  private resolveSchemaProperty(prop: SchemaProperty | null): SchemaProperty {
    if (!prop) {
      return { type: 'object' } as SchemaProperty;
    }
    if (prop.$ref && this.schema?.$defs) {
      const match = prop.$ref.match(/#\/\$defs\/(.+)$/);
      if (match) {
        const defName = match[1];
        const def = this.schema.$defs[defName] as SchemaProperty | undefined;
        if (def) {
          return def;
        }
      }
    }
    return prop;
  }
}
