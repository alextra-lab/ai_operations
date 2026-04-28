/**
 * ParameterConfigPanelComponent
 *
 * Reusable configuration panel for query parameters.
 *
 * Features:
 * - Collapsible Material expansion panel
 * - Model selector (LLM + embedding)
 * - Sampling preset selector (ADR-023)
 * - RAG parameters (top_k, similarity_threshold, collections)
 * - Advanced vector DB settings
 * - Form validation with real-time feedback
 * - High-entropy warning
 *
 * Usage:
 * ```html
 * <app-parameter-config-panel
 *   [initialConfig]="config"
 *   [mode]="'rag'"
 *   [showAdvanced]="true"
 *   (configChanged)="onConfigChange($event)"
 *   (execute)="onExecute()">
 * </app-parameter-config-panel>
 * ```
 *
 * Related: P4-TOOLS-01, ADR-023, ADR-045
 */

import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output,
} from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

// Angular Material imports
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';

// RxJS imports
import { debounceTime, Observable, Subject, takeUntil } from 'rxjs';

// Internal imports
import { CollectionListResponse } from '../../api/models/collection.models';
import { Model } from '../../api/models/model-registry.models';
import {
  getPresetValues,
  isHighEntropyConfig,
  QueryConfig,
  SamplingPreset,
} from '../../api/models/query-config.models';
import { CollectionService } from '../../api/services/collection.service';
import { ModelRegistryService } from '../../api/services/model-registry.service';

const STORAGE_KEY_EXPANDED = 'paramConfigExpanded';

@Component({
  selector: 'app-parameter-config-panel',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTooltipModule,
  ],
  templateUrl: './parameter-config-panel.component.html',
  styleUrls: ['./parameter-config-panel.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ParameterConfigPanelComponent implements OnInit, OnDestroy {
  // ========================================================================
  // Inputs
  // ========================================================================

  @Input() initialConfig: QueryConfig | null = null;
  @Input() showAdvanced = false;
  @Input() mode: 'semantic' | 'rag' | 'usecase' = 'rag';

  // ========================================================================
  // Outputs
  // ========================================================================

  @Output() configChanged = new EventEmitter<QueryConfig>();
  @Output() execute = new EventEmitter<void>();

  // ========================================================================
  // Public Properties
  // ========================================================================

  configForm!: FormGroup;
  models$!: Observable<Model[]>;
  collections: string[] = [];
  samplingPresets = SamplingPreset;
  isExpanded = true;
  showHighEntropyWarning = false;

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private modelService: ModelRegistryService,
    private collectionService: CollectionService
  ) {}

  // ========================================================================
  // Lifecycle Hooks
  // ========================================================================

  ngOnInit(): void {
    this.createForm();
    this.loadModels();
    this.loadCollections();
    this.setupFormSubscriptions();
    this.loadExpandedState();

    if (this.initialConfig) {
      this.patchFormFromConfig(this.initialConfig);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========================================================================
  // Form Setup
  // ========================================================================

  private createForm(): void {
    this.configForm = this.fb.group({
      // Model configuration (LLM only, embedding is system-determined)
      llm_model: ['gpt-4o-mini', Validators.required],

      // Sampling configuration
      sampling_preset: [SamplingPreset.BALANCED],
      temperature: [
        { value: 0.65, disabled: true },
        [Validators.min(0), Validators.max(2)],
      ],
      max_tokens: [
        { value: 2048, disabled: true },
        [Validators.min(1), Validators.max(16384)],
      ],
      top_p: [
        { value: 0.95, disabled: true },
        [Validators.min(0), Validators.max(1)],
      ],

      // Retrieval configuration (same for semantic and RAG modes)
      vector_collections: [['documents'], Validators.required],
      top_k: [
        10,
        [Validators.required, Validators.min(1), Validators.max(100)],
      ],
      similarity_threshold: [
        0.6,
        [Validators.required, Validators.min(0), Validators.max(1)],
      ],
      hybrid_bm25: [false],

      // Advanced vector DB settings
      ef_search: [128, [Validators.min(1), Validators.max(512)]],
      score_normalization: [false],
    });
  }

  private setupFormSubscriptions(): void {
    // Emit changes with debounce
    this.configForm.valueChanges
      .pipe(debounceTime(300), takeUntil(this.destroy$))
      .subscribe(() => {
        if (this.configForm.valid) {
          this.emitConfig();
        }
      });

    // Watch sampling preset changes
    this.configForm
      .get('sampling_preset')
      ?.valueChanges.pipe(takeUntil(this.destroy$))
      .subscribe((preset) => {
        this.onSamplingPresetChange(preset);
      });

    // Watch for high-entropy configuration
    this.configForm.valueChanges
      .pipe(debounceTime(300), takeUntil(this.destroy$))
      .subscribe(() => {
        this.checkHighEntropy();
      });
  }

  // ========================================================================
  // Data Loading
  // ========================================================================

  private loadModels(): void {
    this.models$ = this.modelService.getLLMModels();
  }

  private loadCollections(): void {
    this.collectionService.listAvailableCollections().subscribe({
      next: (response: CollectionListResponse) => {
        this.collections = response.collections.map((c) => c.name);
      },
      error: (error: unknown) => {
        console.error('Failed to load collections:', error);
        this.collections = ['documents']; // Fallback
      },
    });
  }

  // ========================================================================
  // Config Management
  // ========================================================================

  private patchFormFromConfig(config: QueryConfig): void {
    this.configForm.patchValue(
      {
        llm_model: config.llm_model,
        sampling_preset: config.sampling.preset,
        temperature: config.sampling.temperature,
        max_tokens: config.sampling.max_tokens,
        top_p: config.sampling.top_p,
        vector_collections: config.rag.vector_collections,
        top_k: config.rag.top_k,
        similarity_threshold: config.rag.similarity_threshold,
        hybrid_bm25: config.rag.hybrid_bm25,
        ef_search: config.vector_db?.ef_search,
        score_normalization: config.vector_db?.score_normalization,
      },
      { emitEvent: false }
    );

    // Update preset-dependent fields
    this.onSamplingPresetChange(config.sampling.preset, false);
  }

  private emitConfig(): void {
    const formValue = this.configForm.getRawValue();

    const config: QueryConfig = {
      llm_model: formValue.llm_model,
      sampling: {
        preset: formValue.sampling_preset,
        temperature: formValue.temperature,
        max_tokens: formValue.max_tokens,
        top_p: formValue.top_p,
      },
      rag: {
        enabled: true, // Always enabled for retrieval
        vector_collections: formValue.vector_collections,
        top_k: formValue.top_k,
        similarity_threshold: formValue.similarity_threshold,
        hybrid_bm25: formValue.hybrid_bm25,
      },
      vector_db: {
        ef_search: formValue.ef_search,
        score_normalization: formValue.score_normalization,
      },
      query_type: this.mode,
    };

    this.configChanged.emit(config);
  }

  // ========================================================================
  // Sampling Preset Handling
  // ========================================================================

  private onSamplingPresetChange(
    preset: SamplingPreset,
    emitEvent = true
  ): void {
    if (preset === SamplingPreset.CUSTOM) {
      // Enable custom parameter fields
      this.configForm.get('temperature')?.enable({ emitEvent });
      this.configForm.get('top_p')?.enable({ emitEvent });
      this.configForm.get('max_tokens')?.enable({ emitEvent });
    } else {
      // Disable and set preset values
      const values = getPresetValues(preset);
      this.configForm.patchValue(values, { emitEvent: false });
      this.configForm.get('temperature')?.disable({ emitEvent });
      this.configForm.get('top_p')?.disable({ emitEvent });
      this.configForm.get('max_tokens')?.disable({ emitEvent });
    }
  }

  private checkHighEntropy(): void {
    const sampling = {
      preset: this.configForm.get('sampling_preset')?.value,
      temperature: this.configForm.get('temperature')?.value,
      top_p: this.configForm.get('top_p')?.value,
    };

    this.showHighEntropyWarning = isHighEntropyConfig(sampling);
  }

  // ========================================================================
  // UI Actions
  // ========================================================================

  toggleExpanded(): void {
    this.isExpanded = !this.isExpanded;
    this.saveExpandedState();
  }

  onExecute(): void {
    if (this.configForm.valid) {
      this.execute.emit();
    }
  }

  resetToDefaults(): void {
    this.createForm();
    this.setupFormSubscriptions();
    this.emitConfig();
  }

  // ========================================================================
  // LocalStorage
  // ========================================================================

  private loadExpandedState(): void {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_EXPANDED);
      if (saved !== null) {
        this.isExpanded = saved === 'true';
      }
    } catch (error) {
      console.warn('localStorage not available:', error);
    }
  }

  private saveExpandedState(): void {
    try {
      localStorage.setItem(STORAGE_KEY_EXPANDED, String(this.isExpanded));
    } catch (error) {
      console.warn('Failed to save state:', error);
    }
  }

  // ========================================================================
  // Template Helpers
  // ========================================================================

  get isCustomPreset(): boolean {
    return (
      this.configForm.get('sampling_preset')?.value === SamplingPreset.CUSTOM
    );
  }
}
