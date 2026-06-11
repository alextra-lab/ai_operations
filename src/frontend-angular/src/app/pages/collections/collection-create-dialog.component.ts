/**
 * Collection Create Dialog Component
 *
 * Dialog for creating a new document collection with embedding model selection.
 * Validates collection name format and provides model recommendations.
 *
 * Reference: P2-F3-ENHANCED-Collection-Management.md - Task 2.2
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { CollectionCreate } from '../../api/models/collection.models';
import { Model } from '../../api/models/model-registry.models';
import { CollectionService } from '../../api/services/collection.service';
import { ModelRegistryService } from '../../api/services/model-registry.service';
import { SystemConfigService } from '../admin/system-config/services/system-config.service';

@Component({
  selector: 'app-collection-create-dialog',
  templateUrl: './collection-create-dialog.component.html',
  styleUrls: ['./collection-create-dialog.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatRadioModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTooltipModule,
  ],
})
export class CollectionCreateDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  createForm: FormGroup;
  isSubmitting = false;
  isLoadingModels = true;
  errorMessage = '';

  // Available embedding models (built-in + remotes)
  embeddingModels: Model[] = [];
  selectedModel: Model | null = null;

  constructor(
    private fb: FormBuilder,
    private collectionService: CollectionService,
    private modelRegistryService: ModelRegistryService,
    private systemConfigService: SystemConfigService,
    private dialogRef: MatDialogRef<CollectionCreateDialogComponent>
  ) {
    this.createForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(3)]],
      description: [''],
      embedding_model: ['', Validators.required],
      // Preflight configuration (P4-DOC-07)
      auto_chunk_enabled: [true],
      preflight_sample_tokens: [10000],
      showAdvancedSettings: [false],
    });
  }

  ngOnInit(): void {
    // Load available embedding models
    this.loadEmbeddingModels();

    // Validate name on change
    this.createForm.get('name')?.valueChanges.subscribe((value) => {
      if (value) {
        const validation = this.collectionService.validateCollectionName(value);
        if (!validation.valid) {
          this.createForm.get('name')?.setErrors({ invalid: validation.error });
        }
      }
    });

    // Track selected model changes
    this.createForm
      .get('embedding_model')
      ?.valueChanges.subscribe((modelId) => {
        this.selectedModel =
          this.embeddingModels.find((m) => m.model_id === modelId) || null;
      });
  }

  /**
   * Load available embedding models and set default from system config
   */
  private loadEmbeddingModels(): void {
    this.isLoadingModels = true;

    // Load embedding models and system config in parallel
    this.modelRegistryService.getEmbeddingModels().subscribe({
      next: (models) => {
        this.embeddingModels = models;

        // Get default from system config
        this.systemConfigService.getConfig().subscribe({
          next: (config) => {
            const defaultModel = config.corpus?.default_embedding_model;
            if (defaultModel) {
              // Pre-select the default model
              this.createForm.patchValue({ embedding_model: defaultModel });
            } else if (models.length > 0) {
              // Fallback to first available model
              this.createForm.patchValue({
                embedding_model: models[0].model_id,
              });
            }
            this.isLoadingModels = false;
            queueMicrotask(() => this.cdr.detectChanges());
          },
          error: () => {
            // Fallback to first available model if config fails
            if (models.length > 0) {
              this.createForm.patchValue({
                embedding_model: models[0].model_id,
              });
            }
            this.isLoadingModels = false;
            queueMicrotask(() => this.cdr.detectChanges());
          },
        });
      },
      error: (err) => {
        console.error('Failed to load embedding models', err);
        this.errorMessage =
          'Failed to load embedding models. Please try again.';
        this.isLoadingModels = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
    });
  }

  /**
   * Get embedding provider from model based on provider_type
   *
   * Per ADR-050:
   * - provider_type='openai' means OpenAI-compatible API (LMStudio, Ollama, vLLM, OpenAI)
   * - provider_type='local' means Python in-process (SentenceTransformer)
   */
  private getEmbeddingProvider(model: Model): 'openai' | 'local' {
    // Use provider_type to determine the API protocol
    const providerType = (model.provider_type || '').toLowerCase();

    // Map provider_type to embedding_provider for schema validation
    // Backend accepts: 'openai', 'local', 'azure', 'cohere'
    if (providerType === 'openai' || providerType === 'azure') {
      return 'openai';
    }
    // Default to 'local' for local provider_type
    return 'local';
  }

  /**
   * Submit form and create collection
   */
  onSubmit(): void {
    if (this.createForm.invalid || this.isSubmitting || !this.selectedModel) {
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    const formValue = this.createForm.value;
    const collectionData: CollectionCreate = {
      name: formValue.name.toLowerCase().trim(),
      description: formValue.description?.trim() || undefined,
      // Use selected embedding model
      embedding_model: this.selectedModel.model_id,
      embedding_provider: this.getEmbeddingProvider(this.selectedModel),
      embedding_dimensions: this.selectedModel.embedding_dimensions || 384,
      // Auto-chunking configuration (P4-DOC-07)
      auto_chunk_enabled: formValue.auto_chunk_enabled ?? true,
      preflight_sample_tokens: formValue.preflight_sample_tokens ?? 10000,
    };

    this.collectionService.createCollection(collectionData).subscribe({
      next: (collection) => {
        this.dialogRef.close(collection);
      },
      error: (error) => {
        console.error('Collection creation error:', error);
        this.errorMessage =
          error.error?.detail || error.message || 'Failed to create collection';
        this.isSubmitting = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
    });
  }

  /**
   * Cancel and close dialog
   */
  onCancel(): void {
    this.dialogRef.close();
  }
}
