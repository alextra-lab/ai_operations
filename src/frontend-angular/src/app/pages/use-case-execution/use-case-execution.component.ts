import { CommonModule, Location } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';

// Angular Material imports
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatOptionModule } from '@angular/material/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

// Internal imports
import { Message } from '../../api/models/query-config.models';
import {
  ExecutionResponse,
  UseCase,
  UseCaseConfig,
  UseCaseExecution,
} from '../../api/models/use-case.models';
import { UseCaseExecutionService } from '../../api/services/use-case-execution.service';
import { UseCaseService } from '../../api/services/use-case.service';
import { UserProfile } from '../../core/auth/auth.models';
import { AuthService } from '../../core/auth/auth.service';
import {
  FormattedOutput,
  OutputFormatTemplate,
} from '../../models/output-format.model';
import { OutputFormattingService } from '../../services/output-formatting.service';
import { SessionStorageService } from '../../services/session-storage.service';
import { TemplateRegistryService } from '../../services/template-registry.service';

// Components
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { LucideAngularModule } from 'lucide-angular';
import { ExecutionMetricsComponent } from '../../components/execution-metrics/execution-metrics.component';
import { ExportToolbarComponent } from '../../components/export-toolbar/export-toolbar.component';
import { QueryResultsPanelComponent } from '../../components/query-results-panel/query-results-panel.component';
import {
  SchemaRefineDialogComponent,
  SchemaRefineDialogData,
  SchemaRefineDialogResult,
} from '../../components/schema-refine-dialog/schema-refine-dialog.component';
import { SourceCitationComponent } from '../../components/source-citation/source-citation.component';
import { StructuredOutputRendererComponent } from '../../components/structured-output-renderer/structured-output-renderer.component';

@Component({
  selector: 'app-use-case-execution',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatOptionModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatDialogModule,
    ExecutionMetricsComponent,
    ExportToolbarComponent,
    QueryResultsPanelComponent,
    SourceCitationComponent,
    StructuredOutputRendererComponent,
  ],
  templateUrl: './use-case-execution.component.html',
  styleUrls: ['./use-case-execution.component.scss'],
})
export class UseCaseExecutionComponent implements OnInit, OnDestroy {
  // Component state
  useCaseId: string | null = null;
  useCase: UseCase | null = null;
  useCaseConfig: UseCaseConfig | null = null;
  isLoading = false;
  error: string | null = null;
  currentUser: UserProfile | null = null;

  // Forms
  executionForm: FormGroup;
  overridesForm: FormGroup;

  // Execution state
  isExecuting = false;
  executionResult: ExecutionResponse | null = null;
  executionError: string | null = null;
  executionProgress = 0;
  currentStep = '';

  // Streaming state
  isStreaming = false;
  streamingResponse = '';

  // UI state
  inputPanelExpanded = true;
  showOverrides = false;

  // Conversation messages (for QueryResultsPanel)
  conversationMessages: Message[] = [];

  // Structured output state
  formattedOutput: FormattedOutput | null = null;
  outputTemplate: OutputFormatTemplate | null = null;

  // Session tracking (ADR-030: Stateless Core)
  currentSessionId: string | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private location: Location,
    private useCaseService: UseCaseService,
    private executionService: UseCaseExecutionService,
    private outputFormattingService: OutputFormattingService,
    private templateRegistry: TemplateRegistryService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar,
    private sessionStorage: SessionStorageService,
    private cdr: ChangeDetectorRef,
    private dialog: MatDialog,
    private authService: AuthService
  ) {
    this.executionForm = this.fb.group({});
    this.overridesForm = this.fb.group({});
  }

  ngOnInit(): void {
    // Load current user for permission checks
    this.authService
      .getCurrentUser()
      .pipe(takeUntil(this.destroy$))
      .subscribe((user) => {
        this.currentUser = user;
      });

    this.route.params.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      this.useCaseId = params['id'];
      if (this.useCaseId) {
        this.loadUseCase();
      }
    });

    // Reload config when navigation state indicates schema was updated
    // This handles the flow: execution → wizard edit → save → back to execution
    const navigation = this.router.getCurrentNavigation();
    if (navigation?.extras?.state?.['schemaUpdated']) {
      // Reload use case config after schema update
      setTimeout(() => {
        if (this.useCaseId) {
          this.loadUseCase();
        }
      }, 100);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========================================================================
  // Data Loading
  // ========================================================================

  private loadUseCase(): void {
    if (!this.useCaseId) return;

    this.isLoading = true;
    this.error = null;

    // Clear cache for this use case to ensure fresh data
    // (handles case where user edited in wizard and returned)
    this.useCaseService.invalidateCache('use_case', this.useCaseId);

    // Load use case details and config in parallel
    const useCase$ = this.useCaseService.getUseCase(this.useCaseId);
    const config$ = this.useCaseService.getUseCaseConfig(this.useCaseId);

    useCase$.pipe(takeUntil(this.destroy$)).subscribe({
      next: (useCase) => {
        this.useCase = useCase;
        this.setupExecutionForm();
        this.createConversationSession();
      },
      error: (error) => {
        this.error = 'Failed to load use case details.';
        this.isLoading = false;
        console.error('Error loading use case:', error);
      },
    });

    config$.pipe(takeUntil(this.destroy$)).subscribe({
      next: (config) => {
        this.useCaseConfig = config;
        this.setupExecutionForm();
        this.setupOverridesForm();
        this.loadOutputTemplate();
        this.isLoading = false;
      },
      error: (error) => {
        this.error = 'Failed to load use case configuration.';
        this.isLoading = false;
        console.error('Error loading use case config:', error);
      },
    });
  }

  /**
   * Load output format template when output_contract has template_id.
   */
  private loadOutputTemplate(): void {
    const templateId = this.useCaseConfig?.output_contract?.template_id ?? null;
    if (templateId) {
      this.outputTemplate = this.templateRegistry.get(templateId) ?? null;
    } else {
      this.outputTemplate = null;
    }
  }

  // ========================================================================
  // Form Setup
  // ========================================================================

  private setupExecutionForm(): void {
    if (!this.useCaseConfig?.template_config?.input_fields) return;

    const formControls: Record<string, any> = {};

    this.useCaseConfig.template_config.input_fields.forEach((field) => {
      const validators = [];

      if (field.required) {
        validators.push(Validators.required);
      }

      if (field.validation) {
        if (field.validation.min_length) {
          validators.push(Validators.minLength(field.validation.min_length));
        }
        if (field.validation.max_length) {
          validators.push(Validators.maxLength(field.validation.max_length));
        }
        if (field.validation.min_value !== undefined) {
          validators.push(Validators.min(field.validation.min_value));
        }
        if (field.validation.max_value !== undefined) {
          validators.push(Validators.max(field.validation.max_value));
        }
        if (field.validation.pattern) {
          validators.push(Validators.pattern(field.validation.pattern));
        }
      }

      formControls[field.name] = [
        field.default_value || this.getDefaultValue(field.type),
        validators,
      ];
    });

    this.executionForm = this.fb.group(formControls);
  }

  private setupOverridesForm(): void {
    if (!this.useCaseConfig?.execution_config) return;

    const config = this.useCaseConfig.execution_config;

    this.overridesForm = this.fb.group({
      temperature: [
        config.default_temperature,
        [Validators.min(0), Validators.max(2)],
      ],
      top_k: [config.default_top_k, [Validators.min(1), Validators.max(100)]],
      similarity_threshold: [
        config.default_similarity_threshold,
        [Validators.min(0), Validators.max(1)],
      ],
      streaming: [false],
      max_tokens: [null, [Validators.min(1), Validators.max(4000)]],
    });
  }

  private getDefaultValue(fieldType: string): any {
    switch (fieldType) {
      case 'text':
      case 'textarea':
        return '';
      case 'number':
        return null;
      case 'boolean':
        return false;
      case 'select':
      case 'multiselect':
        return null;
      default:
        return null;
    }
  }

  // ========================================================================
  // Execution
  // ========================================================================

  execute(): void {
    if (!this.executionForm.valid || !this.useCaseId) {
      this.markFormGroupTouched(this.executionForm);
      return;
    }

    const execution: UseCaseExecution = {
      use_case_id: this.useCaseId,
      inputs: this.executionForm.value,
      overrides: this.showOverrides ? this.overridesForm.value : undefined,
    };

    this.isExecuting = true;
    this.executionResult = null;
    this.executionError = null;
    this.executionProgress = 0;
    this.streamingResponse = '';
    this.conversationMessages = [];
    this.formattedOutput = null;

    // Collapse input panel to maximize result space
    this.inputPanelExpanded = false;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: this.formatInputsAsMessage(execution.inputs),
      created_at: new Date().toISOString(),
    };
    this.conversationMessages.push(userMessage);
    this.addMessageToSession('user', userMessage.content);

    if (this.overridesForm.value.streaming) {
      this.executeStreaming(execution);
    } else {
      this.executeStandard(execution);
    }
  }

  private executeStandard(execution: UseCaseExecution): void {
    this.currentStep = 'Initializing execution...';
    this.executionProgress = 10;

    this.executionService
      .executeUseCase(execution)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: async (result) => {
          this.executionResult = result;
          this.executionProgress = 100;
          this.currentStep = 'Execution completed';
          this.isExecuting = false;

          if (
            result.structured_data &&
            this.useCaseConfig?.output_contract?.template_id
          ) {
            await this.renderStructuredOutput(result);
          }

          // Add assistant message
          const assistantMessage: Message = {
            id: Date.now().toString(),
            role: 'assistant',
            content: result.response || 'Execution completed',
            created_at: new Date().toISOString(),
          };
          this.conversationMessages.push(assistantMessage);
          this.addMessageToSession('assistant', assistantMessage.content);
        },
        error: (error) => {
          this.executionError = error.message || 'Execution failed';
          this.executionProgress = 0;
          this.currentStep = 'Execution failed';
          this.isExecuting = false;
        },
      });
  }

  private executeStreaming(execution: UseCaseExecution): void {
    this.isStreaming = true;
    this.currentStep = 'Starting streaming execution...';
    this.executionProgress = 10;

    this.executionService
      .executeUseCaseStreaming(execution)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: async (response) => {
          switch (response.type) {
            case 'chunk':
              this.streamingResponse += response.data;
              this.executionProgress = Math.min(
                this.executionProgress + 10,
                80
              );
              this.currentStep = 'Generating response...';
              break;
            case 'sources':
              // Sources handled by executionResult
              this.executionProgress = 90;
              break;
            case 'complete':
              this.executionResult = response.data;
              this.executionProgress = 100;
              this.currentStep = 'Execution completed';
              this.isExecuting = false;
              this.isStreaming = false;

              if (
                response.data?.structured_data &&
                this.useCaseConfig?.output_contract?.template_id
              ) {
                await this.renderStructuredOutput(response.data);
              }

              // Add assistant message
              const assistantMessage: Message = {
                id: Date.now().toString(),
                role: 'assistant',
                content:
                  this.streamingResponse || response.data?.response || '',
                created_at: new Date().toISOString(),
              };
              this.conversationMessages.push(assistantMessage);
              this.addMessageToSession('assistant', assistantMessage.content);
              break;
            case 'error':
              this.executionError =
                response.data.message || 'Streaming execution failed';
              this.executionProgress = 0;
              this.currentStep = 'Execution failed';
              this.isExecuting = false;
              this.isStreaming = false;
              break;
          }
        },
        error: (error) => {
          this.executionError = error.message || 'Streaming execution failed';
          this.executionProgress = 0;
          this.currentStep = 'Execution failed';
          this.isExecuting = false;
          this.isStreaming = false;
        },
      });
  }

  cancelExecution(): void {
    this.executionService.disconnectWebSocket();
    this.isExecuting = false;
    this.isStreaming = false;
    this.executionProgress = 0;
    this.currentStep = '';
  }

  /**
   * Render structured output using template when backend returns structured_data.
   */
  private async renderStructuredOutput(
    result: ExecutionResponse
  ): Promise<void> {
    const templateId = this.useCaseConfig?.output_contract?.template_id ?? null;
    if (!templateId || !result.structured_data) {
      return;
    }

    const template = this.templateRegistry.get(templateId);
    if (!template) {
      return;
    }

    try {
      this.formattedOutput = await this.outputFormattingService.formatResponse(
        {
          answer: result.response,
          structured_data: result.structured_data,
        },
        template
      );
      this.cdr.detectChanges();
    } catch (error) {
      console.error(
        '[UseCaseExecution] Failed to format structured output:',
        error
      );
      this.formattedOutput = null;
    }
  }

  // ========================================================================
  // Schema Refinement (ADR-063 Amendment 2)
  // ========================================================================

  /** Whether the refine schema button should be shown. */
  get canRefineSchema(): boolean {
    return !!this.executionResult?.structured_data && !!this.useCaseId;
  }

  /**
   * Check if current user can modify the use case schema.
   * Follows AIOps lifecycle rules (ADR-060):
   * - Only draft use cases can be modified
   * - Admin can edit any draft
   * - Creator can edit their own draft
   * - Published/archived use cases cannot be modified
   */
  private canModifyUseCase(): boolean {
    if (!this.currentUser || !this.useCase) {
      return false;
    }

    // Admin can edit any draft
    if (this.currentUser.roles.includes('admin')) {
      // But still only drafts - published/archived cannot be edited
      return (this.useCase as any).lifecycle_state === 'draft';
    }

    // Non-admins can only edit drafts
    if ((this.useCase as any).lifecycle_state !== 'draft') {
      return false;
    }

    // Check if user is creator (creator can edit own drafts)
    const createdBy =
      (this.useCase as any).created_by_user_id ||
      (this.useCase as any).created_by;
    if (createdBy && createdBy === this.currentUser.id) {
      return true;
    }

    // AIOps development roles can edit drafts they have access to
    // (This aligns with the wizard edit permissions)
    const devRoles: readonly string[] = [
      'developer',
      'use_case_admin',
      'corpus_admin',
    ];
    return devRoles.some(
      (role) => this.currentUser?.roles.includes(role as any) ?? false
    );
  }

  /**
   * Open the schema refine dialog comparing current
   * schema with one inferred from execution output.
   */
  openRefineSchemaDialog(): void {
    if (!this.executionResult?.structured_data) return;

    const currentSchema = this.useCaseConfig?.output_contract?.output_schema
      ? JSON.stringify(
          this.useCaseConfig.output_contract.output_schema,
          null,
          2
        )
      : null;

    const data: SchemaRefineDialogData = {
      currentSchema,
      structuredData: this.executionResult.structured_data,
      useCaseId: this.useCaseId ?? '',
      canModifySchema: this.canModifyUseCase(),
    };

    const dialogRef = this.dialog.open(SchemaRefineDialogComponent, {
      data,
      width: '750px',
    });

    dialogRef
      .afterClosed()
      .subscribe((result: SchemaRefineDialogResult | undefined) => {
        if (!result || result.strategy === 'cancel') return;
        if (!result.schema || !this.useCaseId) return;

        // Double-check permission before navigating
        if (!this.canModifyUseCase()) {
          this.snackBar.open(
            'You do not have permission to modify this use case. Only draft use cases can be edited by their creator or AIOps developers.',
            'OK',
            { duration: 5000 }
          );
          return;
        }

        // Navigate to wizard in edit mode with
        // updated schema via query param (route: /dev/use-cases/edit/:id)
        this.router.navigate(['/dev/use-cases/edit', this.useCaseId], {
          queryParams: {
            refinedSchema: result.schema,
            step: 3,
          },
        });
        this.snackBar.open(
          'Navigating to wizard with refined schema...',
          'OK',
          { duration: 3000 }
        );
      });
  }

  // ========================================================================
  // UI Actions
  // ========================================================================

  toggleOverrides(): void {
    this.showOverrides = !this.showOverrides;
  }

  resetExecution(): void {
    this.executionResult = null;
    this.executionError = null;
    this.executionProgress = 0;
    this.currentStep = '';
    this.streamingResponse = '';
    this.conversationMessages = [];
    this.formattedOutput = null;
    this.inputPanelExpanded = true;
    this.isExecuting = false;
    this.isStreaming = false;
  }

  navigateToUseCases(): void {
    // Use browser back to respect navigation context
    // This keeps us in the correct flow (AIOps Development vs Browse)
    this.location.back();
  }

  // ========================================================================
  // Utility Methods
  // ========================================================================

  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.keys(formGroup.controls).forEach((key) => {
      const control = formGroup.get(key);
      control?.markAsTouched();
    });
  }

  getFieldOptions(fieldName: string): any[] {
    const field = this.useCaseConfig?.template_config?.input_fields?.find(
      (f) => f.name === fieldName
    );
    return field?.options || [];
  }

  getFieldValidationMessage(fieldName: string): string {
    const control = this.executionForm.get(fieldName);
    if (!control || !control.errors || !control.touched) return '';

    const errors = control.errors;
    if (errors['required']) return 'This field is required';
    if (errors['minlength']) {
      return `Minimum length is ${errors['minlength'].requiredLength}`;
    }
    if (errors['maxlength']) {
      return `Maximum length is ${errors['maxlength'].requiredLength}`;
    }
    if (errors['min']) return `Minimum value is ${errors['min'].min}`;
    if (errors['max']) return `Maximum value is ${errors['max'].max}`;
    if (errors['pattern']) return 'Invalid format';

    return 'Invalid value';
  }

  private formatInputsAsMessage(inputs: Record<string, any>): string {
    return Object.entries(inputs)
      .map(([key, value]) => `**${key}:** ${value}`)
      .join('\n');
  }

  formatTokens(tokens: number): string {
    if (isNaN(tokens)) {
      return 'N/A';
    }
    if (tokens < 1000) {
      return tokens.toString();
    } else if (tokens < 1000000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    } else {
      return `${(tokens / 1000000).toFixed(1)}M`;
    }
  }

  formatDuration(ms: number): string {
    if (isNaN(ms)) {
      return 'N/A';
    }
    if (ms < 1000) {
      return `${ms}ms`;
    } else if (ms < 60000) {
      return `${(ms / 1000).toFixed(1)}s`;
    } else {
      const minutes = Math.floor(ms / 60000);
      const seconds = Math.floor((ms % 60000) / 1000);
      return `${minutes}m ${seconds}s`;
    }
  }

  // ========================================================================
  // Session Management (ADR-030: Stateless Core)
  // ========================================================================

  private async createConversationSession(): Promise<void> {
    if (!this.useCase || !this.useCaseId) return;

    try {
      const session = await this.sessionStorage.createSession(
        `${this.useCase.name} - ${new Date().toLocaleDateString()}`,
        this.useCaseId,
        this.useCase.name,
        24 // 24-hour TTL
      );
      this.currentSessionId = session.id;
    } catch (error) {
      console.error('[UseCaseExecution] Failed to create session:', error);
    }
  }

  private async addMessageToSession(
    role: 'user' | 'assistant',
    content: string
  ): Promise<void> {
    if (!this.currentSessionId) return;

    try {
      await this.sessionStorage.addMessage(
        this.currentSessionId,
        role,
        content,
        {
          use_case_id: this.useCaseId,
          created_at: new Date().toISOString(),
        }
      );
    } catch (error) {
      console.error('[UseCaseExecution] Failed to add message:', error);
    }
  }

  onExportComplete(event: { format: string; filename: string }): void {
    this.snackBar.open(`Exported as ${event.format.toUpperCase()}`, 'Close', {
      duration: 3000,
    });
  }

  onSummaryGenerated(event: { summary: string; type: string }): void {
    const typeName = event.type.charAt(0).toUpperCase() + event.type.slice(1);
    this.snackBar.open(`${typeName} summary generated`, 'Close', {
      duration: 3000,
    });
  }

  // ========================================================================
  // Template Helpers
  // ========================================================================

  get hasInputFields(): boolean {
    return (this.useCaseConfig?.template_config?.input_fields?.length ?? 0) > 0;
  }

  get inputFieldsCount(): number {
    return this.useCaseConfig?.template_config?.input_fields?.length ?? 0;
  }

  get canExecute(): boolean {
    return (
      this.executionForm.valid && !this.isExecuting && this.useCaseId !== null
    );
  }

  get showProgress(): boolean {
    return this.isExecuting || this.executionProgress > 0;
  }

  get hasResults(): boolean {
    return this.conversationMessages.length > 1; // More than just user input
  }

  get hasError(): boolean {
    return this.executionError !== null;
  }

  get supportsStreaming(): boolean {
    return this.useCaseConfig?.execution_config?.supports_streaming === true;
  }

  get hasStructuredOutput(): boolean {
    return (
      this.formattedOutput !== null &&
      this.formattedOutput.rendered_sections.length > 0
    );
  }

  getCategoryDisplayName(category: string): string {
    return category
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }
}
