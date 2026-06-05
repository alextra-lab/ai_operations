/**
 * Use Case Authoring Wizard Component
 *
 * ADR-065: Wizard steps reorganized to separate user-facing
 * configuration from engine configuration.
 *
 * Steps:
 * - Step 1: Identity (name, description, category, intent type)
 * - Step 2: Starting Point (blank / pattern / clone — create only)
 * - Step 3: User Experience (input fields, user prompt template,
 *           output format, schema, visualization)
 * - Step 4: AI Engine (prompts, model, sampling, RAG, tools,
 *           policies)
 * - Step 5: Review & Publish (summary, validation, lifecycle)
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import {
  FormArray,
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { Model } from '../../api/models/model-registry.models';
import {
  PATTERN_CATEGORIES,
  PromptPattern,
} from '../../api/models/prompt-patterns.models';
import {
  InputField,
  UserPromptTemplateConfig,
} from '../../api/models/use-case.models';
import {
  IntentType,
  LifecycleState,
  ToolRestrictions,
  UseCaseCreate,
  UseCaseResponse,
  UseCaseUpdate,
} from '../../api/models/use-case-management.models';
import {
  CategoryConfig,
  IntentTypeConfig,
} from '../../api/models/platform-config.models';
import { PlatformConfigService } from '../../api/services/platform-config.service';
import { CollectionService } from '../../api/services/collection.service';
import { ModelRegistryService } from '../../api/services/model-registry.service';
import { PromptPatternsService } from '../../api/services/prompt-patterns.service';
import { UseCaseManagementService } from '../../api/services/use-case-management.service';
import {
  SchemaPreset,
  SchemaEditorComponent,
} from '../../components/schema-editor/schema-editor.component';
import {
  DOMAIN_SCHEMA_PRESETS,
} from '../../constants/domain-schema-presets';
import { OutputTemplateSelectorComponent } from '../../components/output-template-selector/output-template-selector.component';
import {
  SyncValidationResult,
  UserInteractionConfigComponent,
} from '../../components/user-interaction-config/user-interaction-config.component';
import { ToolRestrictionsComponent } from '../../components/tool-restrictions/tool-restrictions.component';
import { ToolSelectorComponent } from '../../components/tool-selector/tool-selector.component';
import { OutputFormattingService } from '../../services/output-formatting.service';
import { TemplateRegistryService } from '../../services/template-registry.service';
import {
  CompatibilityResult,
  SchemaTemplateCompatibilityService,
} from '../../services/schema-template-compatibility.service';
import { FormattedOutput } from '../../models/output-format.model';
import { StructuredOutputRendererComponent } from '../../components/structured-output-renderer/structured-output-renderer.component';
import { CompatibilityStatus } from '../../components/schema-editor/schema-editor.component';
import { LucideAngularModule } from 'lucide-angular';

type StartingPoint = 'blank' | 'pattern' | 'clone';

const DEFAULT_QUERY_FIELD: InputField = {
  name: 'query',
  type: 'textarea',
  label: 'Query',
  description: 'Enter your question or request',
  required: true,
  placeholder: 'What would you like to know?',
};

@Component({
  selector: 'app-use-case-wizard',
  templateUrl: './use-case-wizard.component.html',
  styleUrls: ['./use-case-wizard.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatTooltipModule,
    OutputTemplateSelectorComponent,
    SchemaEditorComponent,
    StructuredOutputRendererComponent,
    ToolRestrictionsComponent,
    ToolSelectorComponent,
    UserInteractionConfigComponent,
  ],
})
export class UseCaseWizardComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // Mode
  isEditMode = false;
  isViewMode = false;
  useCaseId?: string;
  currentUseCase?: UseCaseResponse;

  // Wizard state
  currentStep = 1;
  // ADR-065: Identity, Starting Point, User Experience, AI Engine, Review & Publish
  totalSteps = 5;

  // Step 1 form
  basicInfoForm: FormGroup;

  // Step 2 state
  startingPoint: StartingPoint | null = null;
  selectedPattern: PromptPattern | null = null;
  selectedUseCase: UseCaseResponse | null = null;
  availableUseCases: UseCaseResponse[] = [];
  availablePatterns: PromptPattern[] = [];
  filteredPatterns: PromptPattern[] = [];
  patternSearchTerm = '';
  selectedCategory: string | null = null;

  // Step 3 state: User Experience (ADR-065)
  /** User prompt template ({{variable}} placeholders). Stored in config_json. */
  userPromptTemplate: UserPromptTemplateConfig | null = null;
  /** User input fields. Default one field for create; from config for edit. */
  inputFields: InputField[] = [];
  /** Output visualization preview. */
  showOutputPreview = false;
  /** Schema-template compatibility status (ADR-063). */
  schemaCompatibility: CompatibilityStatus | null = null;

  // Step 4 state: AI Engine (ADR-065)
  promptsForm: FormGroup;
  appliedPatternName: string | null = null;
  showPromptPreview = false;
  configForm: FormGroup;
  formattedPreview: FormattedOutput | null = null;
  isLoadingOutputPreview = false;

  // Options (ADR-067: loaded dynamically)
  categories: CategoryConfig[] = [];
  intentTypes: IntentTypeConfig[] = [];
  /** Track whether intent auto-preset has been user-overridden. */
  private intentAutoPresetApplied = false;

  // Model options (loaded from model registry)
  llmModels: Model[] = [];
  isLoadingModels = false;

  // System embedding model (read-only - displayed for info only)
  systemEmbeddingModel = 'text-embedding-3-small'; // TODO: Fetch from backend config

  // Output format options
  outputFormatOptions = [
    { value: 'text', label: 'Text', description: 'Plain text response' },
    { value: 'json', label: 'JSON', description: 'Structured JSON output' },
    { value: 'yaml', label: 'YAML', description: 'YAML formatted output' },
    {
      value: 'structured',
      label: 'Structured',
      description: 'Custom structured format',
    },
  ];

  validationModeOptions = [
    {
      value: 'best_effort',
      label: 'Best Effort',
      description: 'Validate but allow minor errors',
    },
    {
      value: 'strict',
      label: 'Strict',
      description: 'Enforce strict validation',
    },
  ];

  piiRedactionOptions = [
    { value: 'none', label: 'None', description: 'No PII redaction' },
    {
      value: 'anonymize',
      label: 'Anonymize',
      description: 'Replace PII with generic tokens',
    },
    { value: 'redact', label: 'Redact', description: 'Remove PII entirely' },
    { value: 'encrypt', label: 'Encrypt', description: 'Encrypt PII data' },
  ];

  // Vector collections (to be loaded from backend)
  availableCollections: string[] = [];
  private allCollectionsWithModels: {
    name: string;
    embedding_model: string;
  }[] = [];

  // Loading state
  isLoading = false;
  isCreating = false;

  // Step 5 state
  saveAsPublished = false; // Toggle for Draft vs. Publish (deprecated, kept for compatibility)
  targetLifecycleState: string = LifecycleState.DRAFT; // New: Lifecycle state selection
  showJsonPreview = false; // Toggle for full JSON config preview
  validationErrors: string[] = [];
  /** Sync validation from User Interaction panel (User Experience step). */
  userInteractionValidation: SyncValidationResult | null = null;
  LifecycleState = LifecycleState; // Expose enum to template

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private useCaseService: UseCaseManagementService,
    private patternService: PromptPatternsService,
    private modelRegistryService: ModelRegistryService,
    private collectionService: CollectionService,
    private snackBar: MatSnackBar,
    private templateRegistry: TemplateRegistryService,
    private outputFormatting: OutputFormattingService,
    private platformConfig: PlatformConfigService,
    private schemaCompat: SchemaTemplateCompatibilityService
  ) {
    this.basicInfoForm = this.fb.group({
      // Note: use_case_id is auto-generated from name (slug)
      name: ['', Validators.required],
      description: [''],
      category: ['GENERAL', Validators.required],
      intent_type: ['QUERY', Validators.required],
    });

    this.promptsForm = this.fb.group({
      system_prompt: [''],
      developer_prompt: [''],
      fewshots: this.fb.array([]),
    });

    this.configForm = this.fb.group({
      // Models
      llm_model: ['', Validators.required],
      // embedding_model removed - system-wide configuration

      // Sampling preset (ADR-023)
      sampling_preset: ['balanced', Validators.required],
      temperature: [null], // Derived from preset unless CUSTOM
      max_tokens: [null], // Derived from preset unless CUSTOM
      top_p: [null], // Derived from preset unless CUSTOM
      frequency_penalty: [0.0, [Validators.min(-2), Validators.max(2)]],
      presence_penalty: [0.0, [Validators.min(-2), Validators.max(2)]],

      // RAG settings
      rag_enabled: [true],
      rag_vector_collections: [['documents']],
      rag_top_k: [
        10,
        [Validators.required, Validators.min(1), Validators.max(100)],
      ],
      rag_similarity_threshold: [
        0.6,
        [Validators.required, Validators.min(0), Validators.max(1)],
      ],
      rag_hybrid_bm25: [false],

      // Output contract
      output_format: ['text', Validators.required],
      output_schema: [null],
      output_template_id: [null as string | null],
      validation_mode: ['best_effort', Validators.required],

      // Policies
      streaming_enabled: [true],
      streaming_default: [false],
      history_persistence: [true],
      pii_redaction: ['anonymize', Validators.required],

      // Tools
      tools_allowlist: [[]],
      // Tool restrictions (ADR-057) - managed separately via component
    });

    // ADR-057: Tool Restrictions state
    this.toolRestrictions = null;
  }

  // ADR-057: Tool Restrictions state
  toolRestrictions: ToolRestrictions | null = null;

  ngOnInit(): void {
    // ADR-067: Load dynamic categories and intent types
    this.loadPlatformConfig();

    // Check route to determine mode (view, edit, or create)
    const id = this.route.snapshot.paramMap.get('id');
    const url = this.router.url;

    if (id) {
      this.useCaseId = id;
      // Determine if view or edit mode based on URL path
      if (url.includes('/view/')) {
        this.isViewMode = true;
        this.isEditMode = false;
      } else if (url.includes('/edit/')) {
        this.isViewMode = false;
        this.isEditMode = true;
      } else {
        // Default to edit mode if path is ambiguous
        this.isViewMode = false;
        this.isEditMode = true;
      }
      // Load models first, then load use case data
      // This ensures models are available when populating the form
      this.loadAvailableModels();
      this.loadUseCaseForEdit();
    } else {
      // Create mode - no ID in route
      this.isViewMode = false;
      this.isEditMode = false;
      this.inputFields = [{ ...DEFAULT_QUERY_FIELD }];
      // Load available use cases for cloning (Step 2)
      this.loadAvailableUseCases();
      // Load available patterns (Step 2)
      this.loadAvailablePatterns();
      // Load available models (AI Engine step)
      this.loadAvailableModels();
    }

    // Set up sampling preset change listener (ADR-023)
    this.configForm
      .get('sampling_preset')
      ?.valueChanges.pipe(takeUntil(this.destroy$))
      .subscribe((preset: string) => {
        this.onSamplingPresetChange(preset);
      });

    // ADR-067: Auto-preset on intent type change
    this.basicInfoForm
      .get('intent_type')
      ?.valueChanges.pipe(takeUntil(this.destroy$))
      .subscribe((intentCode: string) => {
        this.onIntentTypeChange(intentCode);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load use case for editing
   */
  private loadUseCaseForEdit(): void {
    if (!this.useCaseId) return;

    this.isLoading = true;
    this.useCaseService
      .getUseCase(this.useCaseId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (useCase) => {
          this.currentUseCase = useCase;
          this.populateFormsForEdit(useCase);
          this.applyRefinedSchemaFromQueryParams();
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading AI operation:', error);
          this.showError('Failed to load AI operation: ' + error.message);
          this.isLoading = false;
        },
      });
  }

  /**
   * Apply refined schema and step from query params (Refine Schema from Output flow).
   * Called after populateFormsForEdit when navigating from execution with refinedSchema.
   */
  private applyRefinedSchemaFromQueryParams(): void {
    const refinedSchema = this.route.snapshot.queryParamMap.get('refinedSchema');
    const stepParam = this.route.snapshot.queryParamMap.get('step');

    if (refinedSchema?.trim()) {
      try {
        JSON.parse(refinedSchema);
        this.configForm.patchValue({
          output_schema: refinedSchema.trim(),
          output_format: 'json',
        });
        // Mark the output_schema control as dirty so the form knows it changed
        this.configForm.get('output_schema')?.markAsDirty();
        this.configForm.get('output_format')?.markAsDirty();
        this.updateSchemaCompatibility();

        console.log('[Wizard] Applied refined schema from query params:', {
          schemaLength: refinedSchema.trim().length,
          outputFormat: 'json',
          formValue: this.configForm.get('output_schema')?.value?.substring(0, 100),
        });

        // Scroll to Step 3 (User Experience) after a short delay for rendering
        setTimeout(() => {
          this.scrollToCurrentStep();
        }, 300);
      } catch {
        console.warn('Invalid refinedSchema in query params, ignoring');
      }
    }

    if (stepParam) {
      const step = parseInt(stepParam, 10);
      if (!isNaN(step) && step >= 1 && step <= 5) {
        this.currentStep = step;
      }
    }
  }

  /**
   * Scroll to the current step for better UX
   */
  private scrollToCurrentStep(): void {
    const stepElement = document.querySelector(`[data-step="${this.currentStep}"]`);
    if (stepElement) {
      stepElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  /**
   * Populate forms with existing use case data
   */
  private populateFormsForEdit(useCase: UseCaseResponse): void {
    // Populate basic info
    this.basicInfoForm.patchValue({
      name: useCase.name,
      description: useCase.description || '',
      category: useCase.category,
      intent_type: useCase.intent_type,
    });

    // Populate prompts if available
    // Prompts are stored in metadata_json but exposed as top-level 'prompts' field in UseCaseResponse
    if (useCase.prompts) {
      this.promptsForm.patchValue({
        system_prompt: useCase.prompts.system_prompt || '',
        developer_prompt: useCase.prompts.developer_prompt || '',
      });

      // Populate few-shot examples
      if (useCase.prompts.fewshots) {
        const fewshotsArray = this.promptsForm.get('fewshots') as FormArray;
        fewshotsArray.clear();
        useCase.prompts.fewshots.forEach(
          (fewshot: { user: string; assistant: string }) => {
            fewshotsArray.push(
              this.fb.group({
                user: [fewshot.user || ''],
                assistant: [fewshot.assistant || ''],
              })
            );
          }
        );
      }
    }

    // Populate configuration
    if (useCase.config_json) {
      const preset =
        useCase.config_json['generation_params']?.['sampling_preset'] ||
        'balanced';
      // No default model id; environments have different models. Use saved value or empty until models load.
      const llmModelId = useCase.config_json['models']?.['llm'] ?? '';

      // Determine RAG enabled: Schema default for RAG.enabled is True
      // If vector_collections exist, RAG should be considered enabled
      const ragConfig = useCase.config_json['rag'] || {};
      const vectorCollections = ragConfig['vector_collections'] || [];
      const ragEnabledExplicit = ragConfig['enabled'];
      // If enabled is not explicitly set, use schema default (true)
      // If collections exist, default to true to show them
      const ragEnabled =
        ragEnabledExplicit !== undefined ? ragEnabledExplicit : true; // Schema default is true (RAGConfig.enabled defaults to True)

      this.configForm.patchValue({
        llm_model: llmModelId,
        sampling_preset: preset,
        temperature:
          useCase.config_json['generation_params']?.['temperature'] || null,
        max_tokens:
          useCase.config_json['generation_params']?.['max_tokens'] || null,
        top_p: useCase.config_json['generation_params']?.['top_p'] || null,
        frequency_penalty:
          useCase.config_json['generation_params']?.['frequency_penalty'] || 0,
        presence_penalty:
          useCase.config_json['generation_params']?.['presence_penalty'] || 0,
        rag_enabled: ragEnabled,
        rag_top_k: ragConfig['top_k'] || 10,
        rag_similarity_threshold: ragConfig['similarity_threshold'] || 0.6,
        rag_vector_collections:
          vectorCollections.length > 0 ? vectorCollections : ['documents'],
        rag_hybrid_bm25: ragConfig['hybrid_bm25'] || false,
        streaming_enabled:
          useCase.config_json['policy']?.['streaming_enabled'] || true,
        streaming_default:
          useCase.config_json['policy']?.['streaming_default'] || false,
        history_persistence:
          useCase.config_json['policy']?.['history_persistence'] || true,
        pii_redaction:
          useCase.config_json['policy']?.['pii_redaction'] || 'anonymize',
        output_format:
          useCase.config_json['output_contract']?.['format'] || 'text',
        output_schema: this.normalizeOutputSchemaForForm(
          useCase.config_json['output_contract']?.['output_schema']
        ),
        output_template_id:
          useCase.config_json['output_contract']?.['template_id'] ?? null,
        validation_mode:
          useCase.config_json['output_contract']?.['validation_mode'] ||
          'best_effort',
        tools_allowlist: useCase.config_json['tools_allowlist'] || [],
      });

      // Ensure collections from config are in availableCollections
      // This is important for view mode where mat-select needs the options to display selected values
      if (vectorCollections.length > 0) {
        vectorCollections.forEach((collection: string) => {
          if (!this.availableCollections.includes(collection)) {
            this.availableCollections.push(collection);
            // Also add to allCollectionsWithModels if not present
            if (
              !this.allCollectionsWithModels.some((c) => c.name === collection)
            ) {
              this.allCollectionsWithModels.push({
                name: collection,
                embedding_model: 'unknown', // Will be updated when collections load
              });
            }
          }
        });
      }

      // ADR-057: Load tool restrictions
      this.toolRestrictions = useCase.config_json['tool_restrictions'] || null;

      // Input fields (User Experience step)
      const rawFields = useCase.config_json['input_fields'];
      this.inputFields =
        Array.isArray(rawFields) && rawFields.length > 0
          ? rawFields.map((f: Record<string, unknown>) => this.mapRawToInputField(f))
          : [{ ...DEFAULT_QUERY_FIELD }];

      // Try config_json.user_prompt_template first (legacy), then prompts.prompt_template (new location)
      const upt = useCase.config_json['user_prompt_template'];
      const prompts = useCase.prompts;

      if (upt && typeof upt === 'object' && typeof (upt as { template?: string }).template === 'string') {
        this.userPromptTemplate = upt as UserPromptTemplateConfig;
      } else if (prompts) {
        const promptTemplate = (prompts as any)['prompt_template'];
        const variables = (prompts as any)['variables'];

        if (typeof promptTemplate === 'string' && promptTemplate.trim()) {
          this.userPromptTemplate = {
            template: promptTemplate,
            variables: Array.isArray(variables) ? variables : [],
            fallback_mode: 'concatenate'
          };
        } else {
          this.userPromptTemplate = null;
        }
      } else {
        this.userPromptTemplate = null;
      }
    }

    // Set lifecycle state
    this.saveAsPublished = useCase.lifecycle_state === LifecycleState.PUBLISHED;
    this.targetLifecycleState = useCase.lifecycle_state;

    // Disable all forms if in view mode - AFTER all patching is complete
    if (this.isViewMode) {
      this.basicInfoForm.disable();
      this.promptsForm.disable();
      this.configForm.disable();
    }

    // Skip Step 2 (Starting Point) in edit mode - go directly to Step 3
    this.currentStep = 3;
  }

  /**
   * Load available use cases for cloning option
   */
  private loadAvailableUseCases(): void {
    this.useCaseService
      .listUseCases({ lifecycle_state: LifecycleState.PUBLISHED })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.availableUseCases = response.use_cases || [];
        },
        error: (error) => {
          console.error('Error loading use cases:', error);
        },
      });
  }

  /**
   * Load available patterns for pattern option
   */
  private loadAvailablePatterns(): void {
    this.isLoading = true;
    this.patternService
      .listPatterns({ page_size: 100 })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: { patterns?: PromptPattern[] }) => {
          this.availablePatterns = response.patterns || [];
          this.filteredPatterns = this.availablePatterns;
          this.isLoading = false;
        },
        error: (error: Error) => {
          console.error('Error loading patterns:', error);
          this.isLoading = false;
        },
      });
  }

  /**
   * ADR-067: Load dynamic categories and intent types
   * from the backend PlatformConfigService.
   */
  private loadPlatformConfig(): void {
    this.platformConfig
      .loadCategories()
      .pipe(takeUntil(this.destroy$))
      .subscribe((cats) => {
        this.categories = cats;
      });

    this.platformConfig
      .loadIntentTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe((types) => {
        this.intentTypes = types;
      });
  }

  /**
   * ADR-067: Apply auto-presets when intent type changes.
   *
   * Sets `sampling_preset` and `output_format` to the
   * intent type's defaults, unless the user has already
   * overridden them (only in create mode on first set).
   */
  private onIntentTypeChange(intentCode: string): void {
    // Skip auto-preset in edit/view mode
    if (this.isEditMode || this.isViewMode) {
      return;
    }

    const profile = this.platformConfig
      .getIntentType(intentCode);
    if (!profile) {
      return;
    }

    // Apply auto-presets
    this.configForm.patchValue({
      sampling_preset: profile.default_sampling_preset,
      output_format: profile.default_output_format,
    });
    this.intentAutoPresetApplied = true;
  }

  /**
   * Load available models from model registry
   */
  private loadAvailableModels(): void {
    this.isLoadingModels = true;

    // Load LLM models
    this.modelRegistryService
      .getLLMModels()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (models) => {
          this.llmModels = models;
          this.isLoadingModels = false;

          // In create mode: Set default LLM model if form is empty
          // In edit/view mode: Verify the configured model exists in the registry
          if (models.length > 0) {
            const currentModelId = this.configForm.get('llm_model')?.value;

            if (!currentModelId) {
              // Create mode - set default
              const defaultModel =
                models.find(
                  (m) => m.model_id.includes('mistral') || m.is_available
                ) || models[0];
              this.configForm.patchValue({
                llm_model: defaultModel.model_id,
              });
            } else {
              // Edit/view mode - verify configured model exists
              const modelExists = models.some(
                (m) => m.model_id === currentModelId
              );
              // Model validation happens silently - invalid models will display as ID in UI
            }
          }
        },
        error: (error) => {
          console.error('Error loading LLM models:', error);
          this.isLoadingModels = false;
          this.showError('Failed to load LLM models');
        },
      });

    // Load available collections for RAG with their embedding models
    this.collectionService
      .listAvailableCollections()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (resp: any) => {
          const apiCollections = (resp?.collections || []) as {
            name: string;
            embedding_model: string;
          }[];

          // Start with API collections
          this.allCollectionsWithModels = [...apiCollections];
          this.availableCollections = this.allCollectionsWithModels.map(
            (c) => c.name
          );

          // Update any existing entries that had 'unknown' model
          // (these were added earlier in populateFormsForEdit)
          const formCollections = this.configForm.get('rag_vector_collections')
            ?.value as string[] | undefined;
          if (formCollections && formCollections.length > 0) {
            formCollections.forEach((collection: string) => {
              // Check if this collection exists in API response
              const apiCollection = apiCollections.find(
                (c) => c.name === collection
              );
              if (apiCollection) {
                // Collection exists in API - ensure it's in our list (should already be)
                const existing = this.allCollectionsWithModels.find(
                  (c) => c.name === collection
                );
                if (existing && existing.embedding_model === 'unknown') {
                  // Update from 'unknown' to actual model
                  existing.embedding_model = apiCollection.embedding_model;
                }
              } else {
                // Collection not in API response - add to availableCollections for display
                // but keep as 'unknown' since it doesn't exist
                if (!this.availableCollections.includes(collection)) {
                  this.availableCollections.push(collection);
                  // Only add to allCollectionsWithModels if not already there
                  if (
                    !this.allCollectionsWithModels.some(
                      (c) => c.name === collection
                    )
                  ) {
                    this.allCollectionsWithModels.push({
                      name: collection,
                      embedding_model: 'unknown', // Collection doesn't exist in API
                    });
                  }
                }
              }
            });
          }

          // Enforce same-model rule dynamically in the form
          const control = this.configForm.get('rag_vector_collections');
          control?.valueChanges
            .pipe(takeUntil(this.destroy$))
            .subscribe((selected: string[]) => {
              this.enforceSameModelSelection(selected);
            });

          // Re-validate current selection now that we have actual model data
          // This handles the case where form was populated before collections API responded
          // enforceSameModelSelection() will safely skip if models are still 'unknown'
          const currentSelection = control?.value as string[] | undefined;
          if (currentSelection && currentSelection.length > 0) {
            this.enforceSameModelSelection(currentSelection);
          }

          this.isLoadingModels = false;
        },
        error: () => {
          // Fallback to empty; user can still proceed without RAG
          this.allCollectionsWithModels = [];
          this.availableCollections = [];
          this.isLoadingModels = false;
        },
      });
  }

  /**
   * Get collections from form value that are not in availableCollections.
   * Used to display collections in view mode even if they're not loaded yet.
   */
  getFormCollectionsNotInAvailable(): string[] {
    const formCollections = this.configForm.get('rag_vector_collections')
      ?.value as string[] | undefined;
    if (!formCollections || formCollections.length === 0) {
      return [];
    }
    return formCollections.filter(
      (collection) => !this.availableCollections.includes(collection)
    );
  }

  /**
   * Enforce that selected collections share the same embedding model.
   * Filters the available list after the first selection and records a
   * validation error if a mixed selection is detected.
   */
  private enforceSameModelSelection(selected: string[]): void {
    if (!selected || selected.length === 0) {
      // Reset to show all collections when none selected
      this.availableCollections = this.allCollectionsWithModels.map(
        (c) => c.name
      );
      return;
    }

    // Determine the model of the first selected collection
    const first = this.allCollectionsWithModels.find(
      (c) => c.name === selected[0]
    );
    if (!first) {
      return;
    }

    const model = first.embedding_model;

    // Skip filtering if model is still 'unknown' (race condition: collections still loading)
    // This prevents incorrectly filtering out valid collections before their models are loaded
    if (model === 'unknown') {
      // Don't filter yet - wait for collections to load with actual models
      // Keep all collections available until we have real model data
      this.availableCollections = this.allCollectionsWithModels.map(
        (c) => c.name
      );
      return;
    }

    // Check if any selected collection still has 'unknown' model
    // If so, skip filtering to avoid race condition
    const selectedCollections = this.allCollectionsWithModels.filter((c) =>
      selected.includes(c.name)
    );
    const hasUnknownModel = selectedCollections.some(
      (c) => c.embedding_model === 'unknown'
    );
    if (hasUnknownModel) {
      // Still loading - don't filter yet
      this.availableCollections = this.allCollectionsWithModels.map(
        (c) => c.name
      );
      return;
    }

    const sameModelCollections = this.allCollectionsWithModels
      .filter((c) => c.embedding_model === model)
      .map((c) => c.name);

    // Filter available options to only those matching the model
    this.availableCollections = sameModelCollections;

    // Validate current selection - remove any mismatched items
    const mismatched = selected.filter(
      (name) => !sameModelCollections.includes(name)
    );
    if (mismatched.length > 0) {
      const filtered = selected.filter((name) =>
        sameModelCollections.includes(name)
      );
      this.configForm.patchValue(
        { rag_vector_collections: filtered },
        { emitEvent: false }
      );
      this.showError(
        'All selected collections must share the same embedding model'
      );
    }
  }

  /**
   * Filter patterns by search term and category
   */
  filterPatterns(): void {
    this.filteredPatterns = this.availablePatterns.filter((pattern) => {
      const matchesSearch =
        !this.patternSearchTerm ||
        pattern.name
          .toLowerCase()
          .includes(this.patternSearchTerm.toLowerCase()) ||
        (pattern.description &&
          pattern.description
            .toLowerCase()
            .includes(this.patternSearchTerm.toLowerCase()));

      const matchesCategory =
        !this.selectedCategory || pattern.category === this.selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }

  /**
   * Select pattern for use case creation
   */
  selectPattern(pattern: PromptPattern): void {
    this.selectedPattern = pattern;
  }

  /**
   * Get unique pattern categories
   */
  get patternCategories(): string[] {
    const categories = this.availablePatterns
      .map((p) => p.category)
      .filter((c): c is string => c !== null && c !== undefined);
    return [...new Set(categories)].sort();
  }

  /**
   * Navigate to next step
   */
  nextStep(): void {
    // In view mode, just navigate through steps without validation
    if (this.isViewMode) {
      const visibleSteps = this.getVisibleSteps();
      const currentIndex = visibleSteps.indexOf(this.currentStep);
      if (currentIndex < visibleSteps.length - 1) {
        this.currentStep = visibleSteps[currentIndex + 1];
      } else {
        // Last step - go back to list without confirmation (view mode, no data loss)
        this.router.navigate(['/dev/use-cases']);
      }
      return;
    }

    if (this.currentStep === 1 && !this.basicInfoForm.valid) {
      this.showError('Please complete all required fields');
      return;
    }

    if (this.currentStep === 2 && !this.isEditMode) {
      if (!this.startingPoint) {
        this.showError('Please select a starting point');
        return;
      }
      // Apply pattern or load prompts before moving to Step 3
      this.preparePromptsForStep3();
    }

    const visibleSteps = this.getVisibleSteps();
    const currentIndex = visibleSteps.indexOf(this.currentStep);

    if (currentIndex < visibleSteps.length - 1) {
      this.currentStep = visibleSteps[currentIndex + 1];
    } else {
      this.finish();
    }
  }

  /**
   * Navigate to previous step
   */
  previousStep(): void {
    const visibleSteps = this.getVisibleSteps();
    const currentIndex = visibleSteps.indexOf(this.currentStep);

    if (currentIndex > 0) {
      this.currentStep = visibleSteps[currentIndex - 1];
    }
  }

  /**
   * Finish wizard and create/update use case
   */
  finish(): void {
    // Validate configuration
    if (!this.validateConfiguration()) {
      this.showError(
        'Configuration validation failed: ' + this.validationErrors.join(', ')
      );
      return;
    }

    // Confirm publish if selected
    if (this.targetLifecycleState === LifecycleState.PUBLISHED) {
      const confirmed = confirm(
        'Are you sure you want to publish this use case? ' +
          'It will become active and available to users.'
      );
      if (!confirmed) {
        return;
      }
    }

    this.isCreating = true;

    if (this.isEditMode) {
      this.updateUseCase();
    } else {
      this.createUseCase();
    }
  }

  /**
   * Create new use case
   */
  private createUseCase(): void {
    const basicInfo = this.basicInfoForm.value;
    const promptsValue = this.promptsForm.value;
    const configValue = this.configForm.value;

    const newUseCase: UseCaseCreate = {
      use_case_id: this.generateUseCaseId(basicInfo.name),
      name: basicInfo.name,
      description: basicInfo.description,
      category: basicInfo.category,
      intent_type: basicInfo.intent_type,
      lifecycle_state: this.targetLifecycleState,
      is_active: this.targetLifecycleState === LifecycleState.PUBLISHED,
      config_json: {
        models: {
          llm: configValue.llm_model,
        },
        generation_params: {
          sampling_preset: configValue.sampling_preset || 'balanced',
          temperature: configValue.temperature, // null unless custom preset
          max_tokens: configValue.max_tokens, // null unless custom preset
          top_p: configValue.top_p, // null unless custom preset
          frequency_penalty: configValue.frequency_penalty || 0.0,
          presence_penalty: configValue.presence_penalty || 0.0,
        },
        rag: {
          enabled: configValue.rag_enabled,
          top_k: configValue.rag_top_k,
          similarity_threshold: configValue.rag_similarity_threshold,
          vector_collections: configValue.rag_vector_collections || [
            'documents',
          ],
          metadata_filters: {},
          tags: [],
          hybrid_bm25: configValue.rag_hybrid_bm25,
        },
        policy: {
          streaming_enabled: configValue.streaming_enabled,
          streaming_default: configValue.streaming_default,
          history_persistence: configValue.history_persistence,
          pii_redaction: configValue.pii_redaction,
        },
        output_contract: {
          format: configValue.output_format || 'text',
          output_schema: this.parseOutputSchemaForApi(
            configValue.output_schema
          ),
          template_id: configValue.output_template_id ?? null,
          validation_mode: configValue.validation_mode || 'best_effort',
        },
        tools_allowlist: configValue.tools_allowlist || [],
        // ADR-057: Tool security restrictions
        tool_restrictions: this.toolRestrictions,
        visibility: {
          roles: [],
          tags: [],
        },
        input_fields:
          this.inputFields.length > 0
            ? this.inputFields
            : [DEFAULT_QUERY_FIELD],
        user_prompt_template: this.userPromptTemplate?.template?.trim()
          ? this.userPromptTemplate
          : null,
      },
      // Prompts must be a separate field, not inside config_json
      prompts: {
        system_prompt: promptsValue.system_prompt || null,
        developer_prompt: promptsValue.developer_prompt || null,
        fewshots: promptsValue.fewshots || [],
        variables: [],
      },
    };

    this.useCaseService
      .createUseCase(newUseCase)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (created) => {
          let message = `Use case "${created.name}" created`;
          if (this.appliedPatternName) {
            message += ` from pattern: ${this.appliedPatternName}`;
          }
          this.showSuccess(message);
          this.isCreating = false;
          this.router.navigate(['/dev/use-cases/edit', created.id]);
        },
        error: (error) => {
          this.showError('Failed to create use case: ' + error.message);
          this.isCreating = false;
        },
      });
  }

  /**
   * Update existing use case
   */
  private updateUseCase(): void {
    if (!this.useCaseId || !this.currentUseCase) return;

    const basicInfo = this.basicInfoForm.value;
    const promptsValue = this.promptsForm.value;
    const configValue = this.configForm.value;

    // Log for debugging schema save issue
    console.log('[Wizard] Updating use case with config:', {
      output_format: configValue.output_format,
      output_schema_length: configValue.output_schema?.length || 0,
      output_schema_preview: configValue.output_schema?.substring(0, 100),
      template_id: configValue.output_template_id,
    });

    const parsedSchema = this.parseOutputSchemaForApi(configValue.output_schema);
    console.log('[Wizard] Parsed schema for API:', parsedSchema);

    const updateData: UseCaseUpdate = {
      name: basicInfo.name,
      description: basicInfo.description,
      category: basicInfo.category,
      config_json: {
        models: {
          llm: configValue.llm_model,
        },
        generation_params: {
          sampling_preset: configValue.sampling_preset || 'balanced',
          temperature: configValue.temperature, // null unless custom preset
          max_tokens: configValue.max_tokens, // null unless custom preset
          top_p: configValue.top_p, // null unless custom preset
          frequency_penalty: configValue.frequency_penalty || 0.0,
          presence_penalty: configValue.presence_penalty || 0.0,
        },
        rag: {
          enabled: configValue.rag_enabled,
          top_k: configValue.rag_top_k,
          similarity_threshold: configValue.rag_similarity_threshold,
          vector_collections: configValue.rag_vector_collections || [
            'documents',
          ],
          metadata_filters: {},
          tags: [],
          hybrid_bm25: configValue.rag_hybrid_bm25,
        },
        policy: {
          streaming_enabled: configValue.streaming_enabled,
          streaming_default: configValue.streaming_default,
          history_persistence: configValue.history_persistence,
          pii_redaction: configValue.pii_redaction,
        },
        output_contract: {
          format: configValue.output_format || 'text',
          output_schema: parsedSchema,
          template_id: configValue.output_template_id ?? null,
          validation_mode: configValue.validation_mode || 'best_effort',
        },
        tools_allowlist: configValue.tools_allowlist || [],
        // ADR-057: Tool security restrictions
        tool_restrictions: this.toolRestrictions,
        visibility: {
          roles: [],
          tags: [],
        },
        input_fields:
          this.inputFields.length > 0
            ? this.inputFields
            : [DEFAULT_QUERY_FIELD],
        user_prompt_template: this.userPromptTemplate?.template?.trim()
          ? this.userPromptTemplate
          : null,
      },
      // Prompts must be a separate field, not inside config_json
      prompts: {
        system_prompt: promptsValue.system_prompt || null,
        developer_prompt: promptsValue.developer_prompt || null,
        fewshots: promptsValue.fewshots || [],
        variables: [],
      },
    };

    this.useCaseService
      .updateUseCase(this.useCaseId, updateData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (updated) => {
          const message = this.saveAsPublished
            ? `Use case "${updated.name}" updated and published`
            : `Use case "${updated.name}" updated as draft`;
          this.showSuccess(message);
          this.isCreating = false;
          this.router.navigate(['/dev/use-cases']);
        },
        error: (error) => {
          this.showError('Failed to update use case: ' + error.message);
          this.isCreating = false;
        },
      });
  }

  /**
   * Select starting point
   */
  selectStartingPoint(point: StartingPoint): void {
    this.startingPoint = point;
  }

  /**
   * Select use case to clone
   */
  selectUseCaseToClone(useCase: UseCaseResponse): void {
    this.selectedUseCase = useCase;
    const rawFields = useCase.config_json?.['input_fields'];
    this.inputFields =
      Array.isArray(rawFields) && rawFields.length > 0
        ? rawFields.map((f: Record<string, unknown>) => this.mapRawToInputField(f))
        : [{ ...DEFAULT_QUERY_FIELD }];
    // Try config_json.user_prompt_template first (legacy), then prompts.prompt_template (new location)
    const upt = useCase.config_json?.['user_prompt_template'];
    const prompts = useCase.prompts;

    if (upt && typeof upt === 'object' && typeof (upt as { template?: string }).template === 'string') {
      this.userPromptTemplate = upt as UserPromptTemplateConfig;
    } else if (prompts) {
      const promptTemplate = (prompts as any)['prompt_template'];
      const variables = (prompts as any)['variables'];

      if (typeof promptTemplate === 'string' && promptTemplate.trim()) {
        this.userPromptTemplate = {
          template: promptTemplate,
          variables: Array.isArray(variables) ? variables : [],
          fallback_mode: 'concatenate'
        };
      } else {
        this.userPromptTemplate = null;
      }
    } else {
      this.userPromptTemplate = null;
    }
  }

  /** Map raw config_json input_fields entry to InputField. */
  private mapRawToInputField(f: Record<string, unknown>): InputField {
    const def = f['default_value'];
    const default_value: InputField['default_value'] =
      def === undefined || def === null
        ? undefined
        : (def as string | number | boolean);
    return {
      name: String(f['name'] ?? ''),
      type: (f['type'] as InputField['type']) ?? 'text',
      label: String(f['label'] ?? ''),
      description: f['description'] != null ? String(f['description']) : undefined,
      required: Boolean(f['required']),
      placeholder: f['placeholder'] != null ? String(f['placeholder']) : undefined,
      default_value,
      options: Array.isArray(f['options']) ? (f['options'] as InputField['options']) : undefined,
      validation: f['validation'] as InputField['validation'],
    };
  }

  /**
   * Prepare prompts for Step 3 based on starting point
   */
  preparePromptsForStep3(): void {
    if (this.startingPoint === 'pattern' && this.selectedPattern) {
      // Apply pattern to get pre-filled prompts
      this.isLoading = true;
      this.patternService
        .applyPattern(this.selectedPattern.pattern_id, {})
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (appliedPattern) => {
            this.appliedPatternName = this.selectedPattern!.name;
            this.promptsForm.patchValue({
              system_prompt: appliedPattern.system_prompt || '',
              developer_prompt: appliedPattern.developer_prompt || '',
            });

            // Load fewshots
            const fewshotsArray = this.getFewshotsArray();
            fewshotsArray.clear();
            if (appliedPattern.fewshots) {
              appliedPattern.fewshots.forEach((pair) => {
                fewshotsArray.push(
                  this.fb.group({
                    user: [pair.user, Validators.required],
                    assistant: [pair.assistant, Validators.required],
                  })
                );
              });
            }

            this.isLoading = false;
          },
          error: (error) => {
            this.showError('Failed to apply pattern: ' + error.message);
            this.isLoading = false;
          },
        });
    } else if (
      this.startingPoint === 'clone' &&
      this.selectedUseCase?.prompts
    ) {
      // Load prompts from cloned use case
      const prompts = this.selectedUseCase.prompts;
      this.promptsForm.patchValue({
        system_prompt: prompts.system_prompt || '',
        developer_prompt: prompts.developer_prompt || '',
      });

      // Load fewshots
      const fewshotsArray = this.getFewshotsArray();
      fewshotsArray.clear();
      if (prompts.fewshots) {
        prompts.fewshots.forEach((pair) => {
          fewshotsArray.push(
            this.fb.group({
              user: [pair.user, Validators.required],
              assistant: [pair.assistant, Validators.required],
            })
          );
        });
      }

      this.appliedPatternName = null; // Not from pattern
    } else {
      // Blank - leave prompts empty
      this.promptsForm.patchValue({
        system_prompt: '',
        developer_prompt: '',
      });
      this.getFewshotsArray().clear();
      this.appliedPatternName = null;
    }
  }

  /**
   * Get fewshots FormArray
   */
  getFewshotsArray(): FormArray {
    return this.promptsForm.get('fewshots') as FormArray;
  }

  /**
   * Add a new few-shot pair
   */
  addFewshotPair(): void {
    const fewshotsArray = this.getFewshotsArray();
    fewshotsArray.push(
      this.fb.group({
        user: ['', Validators.required],
        assistant: ['', Validators.required],
      })
    );
  }

  /**
   * Remove a few-shot pair
   */
  removeFewshotPair(index: number): void {
    const fewshotsArray = this.getFewshotsArray();
    fewshotsArray.removeAt(index);
  }

  /**
   * Toggle prompt preview
   */
  togglePromptPreview(): void {
    this.showPromptPreview = !this.showPromptPreview;
  }

  /**
   * Toggle JSON config preview
   */
  toggleJsonPreview(): void {
    this.showJsonPreview = !this.showJsonPreview;
  }

  /**
   * Validate Step 5 configuration
   */
  validateConfiguration(): boolean {
    this.validationErrors = [];

    // Check basic info
    if (!this.basicInfoForm.valid) {
      this.validationErrors.push('Basic information is incomplete');
    }

    // Check LLM model selected
    if (!this.configForm.get('llm_model')?.value) {
      this.validationErrors.push('LLM model must be selected');
    }

    // Check RAG configuration if enabled
    if (this.configForm.value.rag_enabled) {
      const collections = this.configForm.value.rag_vector_collections;
      if (!collections || collections.length === 0) {
        this.validationErrors.push(
          'At least one collection must be selected when RAG is enabled'
        );
      }

      // Enforce same-model rule for selected collections
      if (collections && collections.length > 1) {
        const selectedModels = collections
          .map(
            (name: string) =>
              this.allCollectionsWithModels.find((c) => c.name === name)
                ?.embedding_model
          )
          .filter((m: string | undefined): m is string => !!m);
        const unique = new Set(selectedModels);
        if (unique.size > 1) {
          this.validationErrors.push(
            'Selected collections must share the same embedding model'
          );
        }
      }

      if (
        this.configForm.value.rag_top_k < 1 ||
        this.configForm.value.rag_top_k > 100
      ) {
        this.validationErrors.push('RAG top_k must be between 1 and 100');
      }
    }

    // Validate JSON schema if provided
    if (this.configForm.value.output_schema) {
      try {
        JSON.parse(this.configForm.value.output_schema);
      } catch {
        this.validationErrors.push('Output schema is not valid JSON');
      }
    }

    // Block save if User Interaction has template-only variables (ADR-064)
    const syncValid = this.userInteractionValidation
      ? this.userInteractionValidation.isValid
      : this.computeUserInteractionSyncValid();
    if (!syncValid) {
      this.validationErrors.push(
        'Fix template errors: some template variables have no matching input field'
      );
    }

    return this.validationErrors.length === 0;
  }

  /**
   * Compute sync validity from current inputFields and userPromptTemplate.
   * Used when User Experience step was never visited so validation
   * was not emitted.
   */
  private computeUserInteractionSyncValid(): boolean {
    const template = this.userPromptTemplate?.template ?? '';
    const fieldNames = new Set(this.inputFields.map((f) => f.name));
    const variablePattern = /\{\{(\w+)\}\}/g;
    let m: RegExpExecArray | null;
    variablePattern.lastIndex = 0;
    while ((m = variablePattern.exec(template)) !== null) {
      if (!fieldNames.has(m[1])) return false;
    }
    return true;
  }

  /**
   * Handle sync validation from the User Interaction combined panel.
   */
  onUserInteractionValidationChange(result: SyncValidationResult): void {
    this.userInteractionValidation = result;
  }

  /**
   * Get complete use case config for preview
   */
  getConfigPreview(): Record<string, unknown> {
    const basicInfo = this.basicInfoForm.value;
    const promptsValue = this.promptsForm.value;
    const configValue = this.configForm.value;

    return {
      use_case_id: this.generateUseCaseId(basicInfo.name),
      name: basicInfo.name,
      description: basicInfo.description,
      category: basicInfo.category,
      intent_type: basicInfo.intent_type,
      lifecycle_state: this.targetLifecycleState,
      is_active: this.targetLifecycleState === LifecycleState.PUBLISHED,
      config_json: {
        models: {
          llm: configValue.llm_model,
        },
        generation_params: {
          sampling_preset: configValue.sampling_preset || 'balanced',
          temperature: configValue.temperature, // null unless custom preset
          max_tokens: configValue.max_tokens, // null unless custom preset
          top_p: configValue.top_p, // null unless custom preset
          frequency_penalty: configValue.frequency_penalty || 0.0,
          presence_penalty: configValue.presence_penalty || 0.0,
        },
        rag: {
          enabled: configValue.rag_enabled,
          top_k: configValue.rag_top_k,
          similarity_threshold: configValue.rag_similarity_threshold,
          vector_collections: configValue.rag_vector_collections || [
            'documents',
          ],
          metadata_filters: {},
          tags: [],
          hybrid_bm25: configValue.rag_hybrid_bm25,
        },
        policy: {
          streaming_enabled: configValue.streaming_enabled,
          streaming_default: configValue.streaming_default,
          history_persistence: configValue.history_persistence,
          pii_redaction: configValue.pii_redaction,
        },
        output_contract: {
          format: configValue.output_format || 'text',
          output_schema: this.parseOutputSchemaForApi(
            configValue.output_schema
          ),
          template_id: configValue.output_template_id ?? null,
          validation_mode: configValue.validation_mode || 'best_effort',
        },
        tools_allowlist: configValue.tools_allowlist || [],
        tool_restrictions: this.toolRestrictions,
        visibility: {
          roles: [],
          tags: [],
        },
        input_fields:
          this.inputFields.length > 0
            ? this.inputFields
            : [DEFAULT_QUERY_FIELD],
        telemetry: {
          required_metrics: ['retrieval', 'performance', 'model'],
        },
      },
      prompts: {
        system_prompt: promptsValue.system_prompt || '',
        developer_prompt: promptsValue.developer_prompt || '',
        fewshots: promptsValue.fewshots || [],
        variables: [],
      },
      metadata_json: this.selectedPattern
        ? {
            created_from_pattern: this.selectedPattern.pattern_id,
          }
        : {},
    };
  }

  /**
   * Get formatted JSON string for preview
   */
  getConfigPreviewJson(): string {
    return JSON.stringify(this.getConfigPreview(), null, 2);
  }

  /**
   * Generate use_case_id from name (slugify)
   */
  private generateUseCaseId(name: string): string {
    return name
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '-') // Replace non-alphanumeric with hyphens
      .replace(/^-+|-+$/g, '') // Remove leading/trailing hyphens
      .substring(0, 100); // Limit length
  }

  /**
   * Schema presets: domain-grouped presets (ADR-066/067)
   * plus template-based presets as a fallback group.
   */
  get outputSchemaPresets(): SchemaPreset[] {
    // Domain presets have group and recommendedTemplateId
    const domain = [...DOMAIN_SCHEMA_PRESETS];

    // Template-based presets for any templates not
    // covered by domain presets
    const coveredIds = new Set(
      domain
        .map((p) => p.recommendedTemplateId)
        .filter(Boolean)
    );
    const templatePresets: SchemaPreset[] = this
      .templateRegistry
      .list()
      .filter((t) => !coveredIds.has(t.template_id))
      .map((t) => ({
        id: `tpl-${t.template_id}`,
        label: t.name,
        group: 'Templates',
        schema: JSON.stringify(t.data_schema, null, 2),
      }));

    return [...domain, ...templatePresets];
  }

  /** Current output schema as string for the schema editor. */
  getOutputSchemaForEditor(): string {
    const v = this.configForm.get('output_schema')?.value;
    return this.normalizeOutputSchemaForForm(v) ?? '';
  }

  /** Called when schema editor value changes. */
  onOutputSchemaChange(value: string): void {
    this.configForm.patchValue({
      output_schema: value?.trim() || null,
    });
    this.updateSchemaCompatibility();
  }

  /**
   * Called when a domain preset is applied.
   * Suggests the recommended template if one exists.
   */
  onSchemaPresetApplied(preset: SchemaPreset): void {
    if (
      preset.recommendedTemplateId
      && this.templateRegistry.has(preset.recommendedTemplateId)
    ) {
      this.configForm.patchValue({
        output_template_id: preset.recommendedTemplateId,
      });
      this.snackBar.open(
        `Suggested template: ${preset.recommendedTemplateId}`,
        'Dismiss',
        { duration: 3000 }
      );
    }
    this.updateSchemaCompatibility();
  }

  /**
   * Recompute schema-template compatibility (ADR-063).
   */
  updateSchemaCompatibility(): void {
    const templateId =
      this.configForm.get('output_template_id')?.value;
    const template = templateId
      ? this.templateRegistry.get(templateId) ?? null
      : null;
    const schemaText =
      this.getOutputSchemaForEditor() || null;

    const result: CompatibilityResult =
      this.schemaCompat.validate(schemaText, template);

    this.schemaCompatibility = {
      level: result.level,
      message: result.message,
    };
  }

  /**
   * Toggle or load output visualization preview with sample data.
   */
  async loadOutputPreview(): Promise<void> {
    const templateId = this.configForm.get('output_template_id')?.value;
    if (!templateId) {
      this.showOutputPreview = false;
      this.formattedPreview = null;
      return;
    }
    const template = this.templateRegistry.get(templateId);
    if (!template) {
      this.formattedPreview = null;
      return;
    }
    if (this.showOutputPreview && this.formattedPreview) {
      this.showOutputPreview = false;
      this.formattedPreview = null;
      return;
    }
    this.isLoadingOutputPreview = true;
    const sample = this.getPreviewSampleForTemplate(templateId);
    try {
      this.formattedPreview = await this.outputFormatting.formatResponse(
        { answer: '', structured_data: sample },
        template
      );
      this.showOutputPreview = true;
    } catch {
      this.formattedPreview = null;
    } finally {
      this.isLoadingOutputPreview = false;
    }
  }

  /**
   * Minimal sample data per built-in template for preview.
   * ADR-066: IDs are structural, not domain-specific.
   */
  private getPreviewSampleForTemplate(
    templateId: string
  ): unknown {
    const samples: Record<string, unknown> = {
      'score-table-timeline': {
        score: 'high',
        confidence: 0.75,
        items: [
          {
            type: 'Finding',
            value: 'Item A',
            context: 'Sample context',
          },
        ],
        events: [
          {
            timestamp: '2025-01-01T12:00:00Z',
            description: 'Sample event',
            severity: 'medium',
          },
        ],
      },
      'filterable-table': {
        items: [
          {
            type: 'Entry',
            value: 'Sample value',
            context: 'Sample context',
            confidence: 0.9,
          },
        ],
      },
      'score-timeline': {
        events: [],
        metric: {
          severity: 5,
          affected_count: 2,
          data_loss: false,
        },
        status: 'investigating',
      },
      'auto-table': {
        data: [
          { col1: 'A', col2: 'B' },
        ],
      },
      'bar-chart': {
        metrics: [
          { label: 'CPU', value: 60 },
          { label: 'Memory', value: 80 },
        ],
      },
      'kv-summary': {
        summary: {
          status: 'Completed',
          score: '85/100',
          category: 'Assessment',
        },
      },
      'multi-table': {
        tables: [
          {
            title: 'Findings',
            rows: [
              { item: 'Finding 1', status: 'Open' },
            ],
          },
          {
            title: 'Recommendations',
            rows: [
              { action: 'Action 1', priority: 'High' },
            ],
          },
        ],
      },
      'comparison-grid': {
        left: {
          title: 'Before',
          content: 'Previous state',
        },
        right: {
          title: 'After',
          content: 'New state',
        },
      },
    };
    return samples[templateId] ?? {};
  }

  /**
   * Normalize output_schema from API (object or string) to form string.
   */
  private normalizeOutputSchemaForForm(
    value: unknown
  ): string | null {
    if (value == null) return null;
    if (typeof value === 'string') return value;
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return null;
    }
  }

  /**
   * Parse output_schema from form (string) to object for API.
   */
  private parseOutputSchemaForApi(
    value: string | Record<string, unknown> | null | undefined
  ): Record<string, unknown> | null {
    if (value == null || value === '') return null;
    if (typeof value === 'object') return value;
    try {
      const parsed = JSON.parse(value as string);
      return typeof parsed === 'object' && parsed !== null ? parsed : null;
    } catch {
      return null;
    }
  }

  /**
   * Cancel wizard and return to list
   */
  cancel(): void {
    const confirmed = confirm(
      'Are you sure you want to cancel? Any progress will be lost.'
    );
    if (confirmed) {
      this.router.navigate(['/dev/use-cases']);
    }
  }

  /**
   * Show success notification
   */
  private showSuccess(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 3000,
      panelClass: ['success-snackbar'],
    });
  }

  /**
   * Show error notification
   */
  private showError(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar'],
    });
  }

  /**
   * Show info notification
   */
  private showInfo(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 4000,
      panelClass: ['info-snackbar'],
    });
  }

  /**
   * Get progress percentage
   */
  getProgress(): number {
    const visibleSteps = this.getVisibleSteps();
    const currentStepIndex = visibleSteps.indexOf(this.currentStep);
    return ((currentStepIndex + 1) / visibleSteps.length) * 100;
  }

  /**
   * Get visible steps based on mode
   */
  getVisibleSteps(): number[] {
    if (this.isEditMode || this.isViewMode) {
      return [1, 3, 4, 5]; // Skip Step 2 (Starting Point) in edit/view mode
    }
    return [1, 2, 3, 4, 5];
  }

  /**
   * Get step number for display
   */
  getStepNumber(step: number): number {
    if (this.isEditMode || this.isViewMode) {
      // In edit/view mode, map steps to display numbers
      const visibleSteps = this.getVisibleSteps();
      return visibleSteps.indexOf(step) + 1;
    }
    return step;
  }

  /**
   * Get step title for display (ADR-065)
   */
  getStepTitle(step: number): string {
    switch (step) {
      case 1:
        return 'Identity';
      case 2:
        return 'Starting Point';
      case 3:
        return 'User Experience';
      case 4:
        return 'AI Engine';
      case 5:
        return 'Review & Publish';
      default:
        return 'Unknown Step';
    }
  }

  /**
   * Get button text based on current step and mode
   */
  getButtonText(): string {
    if (this.isViewMode) {
      // In view mode, show "Close" only on last step, otherwise "Next"
      return this.isLastStep() ? 'Close' : 'Next';
    }
    if (this.isLastStep()) {
      return this.isEditMode ? 'Update AI Operation' : 'Create AI Operation';
    }
    return 'Next';
  }

  /**
   * Check if current step is the last step
   */
  isLastStep(): boolean {
    const visibleSteps = this.getVisibleSteps();
    return this.currentStep === visibleSteps[visibleSteps.length - 1];
  }

  /**
   * Handle sampling preset change (ADR-023)
   */
  onSamplingPresetChange(preset: string): void {
    const tempControl = this.configForm.get('temperature');
    const maxTokensControl = this.configForm.get('max_tokens');
    const topPControl = this.configForm.get('top_p');

    if (preset === 'custom') {
      // Enable custom parameter controls
      tempControl?.enable();
      maxTokensControl?.enable();
      topPControl?.enable();

      // Set default values if null
      if (tempControl?.value === null) {
        tempControl?.setValue(0.7);
      }
      if (maxTokensControl?.value === null) {
        maxTokensControl?.setValue(2048);
      }
      if (topPControl?.value === null) {
        topPControl?.setValue(0.95);
      }
    } else {
      // Disable and clear custom parameters (will be derived from preset)
      tempControl?.setValue(null);
      tempControl?.disable();
      maxTokensControl?.setValue(null);
      maxTokensControl?.disable();
      topPControl?.setValue(null);
      topPControl?.disable();
    }
  }

  /**
   * Get preset parameter values for display
   */
  getPresetParams(preset: string): {
    temperature: number;
    top_p: number;
    max_tokens: number;
  } {
    const presetMap: Record<
      string,
      { temperature: number; top_p: number; max_tokens: number }
    > = {
      strict: { temperature: 0.15, top_p: 0.9, max_tokens: 1024 },
      balanced: { temperature: 0.65, top_p: 0.95, max_tokens: 2048 },
      creative: { temperature: 0.85, top_p: 0.97, max_tokens: 4096 },
      custom: { temperature: 0.7, top_p: 0.95, max_tokens: 2048 },
    };
    return presetMap[preset] || presetMap['balanced'];
  }

  /**
   * Check if current configuration is high-entropy (risky)
   */
  isHighEntropyConfig(): boolean {
    const preset = this.configForm.get('sampling_preset')?.value;
    if (preset !== 'custom') return false;

    const temp = this.configForm.get('temperature')?.value;
    const topP = this.configForm.get('top_p')?.value;

    return temp !== null && topP !== null && temp > 0.9 && topP > 0.97;
  }

  /**
   * Get LLM model display label
   */
  getLLMLabel(modelId: string | null | undefined): string {
    // Handle empty/undefined/null values
    if (!modelId || modelId === '') {
      return 'Not configured';
    }

    // Try to find the model in the loaded models
    const model = this.llmModels.find((m) => m.model_id === modelId);

    if (model) {
      return model.name;
    }

    // Return model ID as fallback (this is the configured value)
    return modelId;
  }

  // NOTE: getEmbeddingLabel removed - embedding model no longer configurable per use case

  /**
   * Get model description for display
   */
  getModelDescription(model: Model): string {
    if (model.description) {
      return model.description;
    }
    // Fallback to specialization or provider info
    const parts = [];
    if (model.specialization) {
      parts.push(model.specialization);
    }
    if (model.context_window) {
      parts.push(`${(model.context_window / 1000).toFixed(0)}k context`);
    }
    return parts.join(' | ') || 'No description';
  }

  /**
   * Check if can proceed to next step
   */
  canProceed(): boolean {
    // In view mode, always allow navigation (read-only browsing)
    if (this.isViewMode) {
      return true;
    }

    if (this.currentStep === 1) {
      return this.basicInfoForm.valid;
    }
    if (this.currentStep === 2 && !this.isEditMode) {
      if (!this.startingPoint) {
        return false;
      }
      if (this.startingPoint === 'clone') {
        return this.selectedUseCase !== null;
      }
      if (this.startingPoint === 'pattern') {
        return this.selectedPattern !== null;
      }
      return true; // blank
    }
    if (this.currentStep === 3) {
      // User Experience: input fields + output config
      return true;
    }
    if (this.currentStep === 4) {
      // AI Engine: prompts + config pre-filled with defaults
      return true;
    }
    if (this.currentStep === 5) {
      // Review & Publish step
      return true;
    }
    return false;
  }

  /**
   * Get category information for pattern styling
   */
  /**
   * ADR-067: Get display name for a category code.
   */
  getCategoryDisplayName(code: string): string {
    const cat = this.categories.find(
      (c) => c.category_code === code
    );
    return cat?.display_name ?? code;
  }

  /**
   * ADR-067: Get display name for an intent type code.
   */
  getIntentDisplayName(code: string): string {
    const intent = this.intentTypes.find(
      (t) => t.intent_code === code
    );
    return intent?.display_name ?? code;
  }

  /**
   * ADR-067: Get the capability profile for the
   * currently selected intent type.
   */
  getSelectedIntentProfile(): IntentTypeConfig | null {
    const code =
      this.basicInfoForm.get('intent_type')?.value;
    if (!code) {
      return null;
    }
    return (
      this.intentTypes.find(
        (t) => t.intent_code === code
      ) ?? null
    );
  }

  getCategoryInfo(categoryId: string) {
    return (
      PATTERN_CATEGORIES.find((c) => c.id === categoryId) || {
        id: categoryId,
        label: categoryId,
        icon: 'shapes',
        description: '',
        color: '#757575',
      }
    );
  }

  /**
   * Handle tool selection change
   */
  onToolsSelectionChange(selectedToolIds: string[]): void {
    this.configForm.patchValue(
      { tools_allowlist: selectedToolIds },
      { emitEvent: false }
    );
  }

  /**
   * Get current tool selection
   */
  getToolsAllowlist(): string[] {
    return this.configForm.get('tools_allowlist')?.value || [];
  }

  /**
   * Handle tool restrictions change (ADR-057)
   */
  onToolRestrictionsChange(restrictions: ToolRestrictions | null): void {
    this.toolRestrictions = restrictions;
  }
}
