import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatStepper, MatStepperModule } from '@angular/material/stepper';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, takeUntil } from 'rxjs/operators';

import { LucideAngularModule } from 'lucide-angular';
import {
  ToolRegistrationPhase,
  ToolRegistrationService,
} from '../../../api/services/tool-registration.service';
import { AuthService } from '../../../core/auth/auth.service';
import {
  DraftStorageService,
  RegistrationDraft,
} from '../../../services/draft-storage.service';

@Component({
  selector: 'app-tool-registration-wizard',
  templateUrl: './tool-registration-wizard.component.html',
  styleUrls: ['./tool-registration-wizard.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatStepperModule,
  ],
})
export class ToolRegistrationWizardComponent implements OnInit, OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper;

  sessionId: string | null = null;
  currentPhase: ToolRegistrationPhase = ToolRegistrationPhase.BASIC_INFO;

  // Forms
  basicInfoForm: FormGroup;
  mcpConfigForm: FormGroup;
  securityForm: FormGroup;
  permissionsForm: FormGroup;

  // Step data
  basicInfo: Record<string, any> = {};
  mcpConfig: Record<string, any> = {};
  connectionResult: Record<string, any> | null = null;
  securityConfig: Record<string, any> = {};
  permissionsConfig: Record<string, any> = {};

  // UI state
  loading = false;
  error: string | null = null;
  validationErrors: Record<string, string[]> = {};

  // Draft management
  private draftSaveSubject = new Subject<void>();
  private destroy$ = new Subject<void>();

  private currentUserId: string | undefined;

  constructor(
    private fb: FormBuilder,
    private registrationService: ToolRegistrationService,
    private draftStorage: DraftStorageService,
    private router: Router,
    private snackBar: MatSnackBar,
    private authService: AuthService
  ) {
    // Initialize forms
    // Note: tool_id is auto-generated from name (see generateToolId method)
    // Note: tool_purpose/service_location default to 'orchestrator' for all
    //       external MCP tools. 'retrieval' is only for internal platform tools.
    this.basicInfoForm = this.fb.group({
      tool_id: [''], // Auto-generated from name, not user-editable
      name: ['', Validators.required],
      description: ['', Validators.required], // Required for clarity
      category: ['custom'], // Default to custom, optional
      tool_purpose: ['orchestrator'], // Hidden default - 99% of tools
      service_location: ['orchestrator'], // Hidden default - synced with purpose
      provider: [''],
      version: [''],
      documentation_url: [''],
      tags: [[]],
    });

    this.mcpConfigForm = this.fb.group({
      mcp_server_type: ['', Validators.required],
      mcp_command: [''],
      mcp_endpoint: [''],
      mcp_protocol_version: ['2024-11-05'],
      timeout_seconds: [
        30,
        [Validators.required, Validators.min(1), Validators.max(300)],
      ],
    });

    // Dynamic validation based on server type
    this.mcpConfigForm
      .get('mcp_server_type')
      ?.valueChanges.subscribe((serverType) => {
        this.updateMcpValidators(serverType);
      });

    this.securityForm = this.fb.group({
      // Security Classification (ADR-057)
      data_source_type: ['internal', Validators.required],
      data_flow_direction: ['ingress', Validators.required],
      network_access_level: ['internal', Validators.required],
      max_data_sensitivity: ['internal', Validators.required],
      // Authentication
      requires_authentication: [false],
      authentication_type: ['api_key'],
      secret_name: [''],
      secret_value: [''],
      secret_expires_at: [null],
    });

    // Dynamic validation for secrets when authentication is required
    // Note: We use a separate method to allow manual triggering after draft load
    this.securityForm
      .get('requires_authentication')
      ?.valueChanges.pipe(takeUntil(this.destroy$))
      .subscribe((requiresAuth) => {
        this.updateSecretValidators(requiresAuth);
      });

    this.permissionsForm = this.fb.group({
      rate_limit_per_minute: [null],
      max_concurrent_calls: [5, [Validators.min(1), Validators.max(100)]],
      health_check_interval_seconds: [300, [Validators.min(60)]],
      role_permissions: [[]],
    });
  }

  ngOnInit(): void {
    // Get current user ID for user-specific drafts
    this.authService
      .getCurrentUser()
      .pipe(takeUntil(this.destroy$))
      .subscribe((user) => {
        this.currentUserId = user?.id;

        // Check for existing draft (user-specific)
        if (this.draftStorage.hasDraft(this.currentUserId)) {
          this.loadDraft();
        }
      });

    // Setup auto-save (debounced)
    this.draftSaveSubject
      .pipe(debounceTime(500), takeUntil(this.destroy$))
      .subscribe(() => this.saveDraft());

    // Auto-generate tool_id from name
    this.basicInfoForm
      .get('name')
      ?.valueChanges.pipe(debounceTime(300), takeUntil(this.destroy$))
      .subscribe((name: string) => {
        const toolId = this.generateToolId(name);
        this.basicInfoForm.patchValue({ tool_id: toolId });
      });

    // Note: tool_purpose and service_location default to 'orchestrator'
    // This is appropriate for virtually all MCP tools (external processes).
    // The 'retrieval' option is only for platform-internal tools that need
    // direct database access - not exposed in UI for standard registration.
  }

  /**
   * Update validators for secret fields based on authentication requirement.
   * Called both by valueChanges subscription and manually after draft load.
   */
  private updateSecretValidators(requiresAuth: boolean): void {
    const secretNameControl = this.securityForm.get('secret_name');
    const secretValueControl = this.securityForm.get('secret_value');

    if (requiresAuth) {
      secretNameControl?.setValidators([Validators.required]);
      secretValueControl?.setValidators([Validators.required]);
    } else {
      secretNameControl?.clearValidators();
      secretValueControl?.clearValidators();
    }

    secretNameControl?.updateValueAndValidity();
    secretValueControl?.updateValueAndValidity();
  }

  /**
   * Generate a valid tool_id from a human-readable name.
   * Converts "Docker MCP Gateway" → "docker_mcp_gateway"
   */
  generateToolId(name: string): string {
    if (!name) return '';
    return name
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, '') // Remove special chars
      .replace(/\s+/g, '_') // Spaces to underscores
      .replace(/-+/g, '_') // Hyphens to underscores
      .replace(/_+/g, '_') // Collapse multiple underscores
      .replace(/^_|_$/g, ''); // Trim leading/trailing underscores
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadDraft(): void {
    const draft = this.draftStorage.loadDraft(this.currentUserId);
    if (!draft) return;

    this.sessionId = draft.sessionId;
    this.basicInfo = draft.formData['basicInfo'] || {};
    this.mcpConfig = draft.formData['mcpConfig'] || {};
    this.connectionResult = draft.formData['connectionResult'] || null;
    this.securityConfig = draft.formData['securityConfig'] || {};
    this.permissionsConfig = draft.formData['permissionsConfig'] || {};

    // Populate forms with draft data
    if (this.basicInfo) {
      this.basicInfoForm.patchValue(this.basicInfo);
    }
    if (this.mcpConfig) {
      this.mcpConfigForm.patchValue(this.mcpConfig);
      // Reapply validators based on server type after loading draft
      // patchValue may not trigger valueChanges if value doesn't change
      const serverType = this.mcpConfigForm.get('mcp_server_type')?.value;
      if (serverType) {
        this.updateMcpValidators(serverType);
      }
    }
    if (this.securityConfig) {
      this.securityForm.patchValue(this.securityConfig);
      // FIX: Explicitly apply secret validators after draft load
      // patchValue may not trigger valueChanges if value doesn't change
      const requiresAuth = this.securityForm.get(
        'requires_authentication'
      )?.value;
      this.updateSecretValidators(requiresAuth ?? false);
    }
    if (this.permissionsConfig) {
      this.permissionsForm.patchValue(this.permissionsConfig);
    }

    // Navigate to saved step
    setTimeout(() => {
      if (this.stepper) {
        this.stepper.selectedIndex = draft.currentStep;
      }
    });
  }

  saveDraft(): void {
    const draft: RegistrationDraft = {
      sessionId: this.sessionId,
      currentStep: this.stepper?.selectedIndex || 0,
      formData: {
        ['basicInfo']: this.basicInfo,
        ['mcpConfig']: this.mcpConfig,
        ['connectionResult']: this.connectionResult,
        ['securityConfig']: this.securityConfig,
        ['permissionsConfig']: this.permissionsConfig,
      },
      timestamp: Date.now(),
    };

    this.draftStorage.saveDraft(draft, this.currentUserId);
  }

  triggerDraftSave(): void {
    this.draftSaveSubject.next();
  }

  onBasicInfoSubmit(): void {
    if (this.basicInfoForm.invalid) {
      return;
    }
    const data = this.basicInfoForm.value;
    this.onBasicInfoComplete(data);
  }

  async onBasicInfoComplete(data: Record<string, any>): Promise<void> {
    this.loading = true;
    this.error = null;

    try {
      const response = await this.registrationService
        .processPhase({
          session_id: this.sessionId,
          phase: ToolRegistrationPhase.BASIC_INFO,
          data,
        })
        .toPromise();

      if (response) {
        this.sessionId = response.session_id;
        this.basicInfo = data;
        this.validationErrors = response.validation_errors;

        if (response.can_proceed) {
          this.stepper.next();
          this.triggerDraftSave();
        }
      }
    } catch (err: any) {
      const errorMsg = err.error?.detail || 'Failed to process basic info';
      this.error = errorMsg;

      // Handle session expiration/not found - reset session and allow retry
      if (errorMsg.includes('not found') || errorMsg.includes('expired')) {
        this.sessionId = null;
        this.snackBar.open(
          'Session expired. Please try again - your form data has been preserved.',
          'Close',
          { duration: 7000 }
        );
      } else {
        this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
      }
    } finally {
      this.loading = false;
    }
  }

  onMcpConfigSubmit(): void {
    if (this.mcpConfigForm.invalid) {
      // Mark all fields as touched to show validation errors
      this.mcpConfigForm.markAllAsTouched();
      // Find and show first error
      const firstError = this.getFirstFormError(this.mcpConfigForm);
      if (firstError) {
        this.snackBar.open(firstError, 'Close', { duration: 5000 });
      }
      return;
    }
    const data = this.mcpConfigForm.value;
    const serverType = data.mcp_server_type;

    // Clean up mcp_command based on server type
    if (serverType === 'stdio') {
      // For STDIO, parse JSON string to array if needed
      if (data.mcp_command && typeof data.mcp_command === 'string') {
        try {
          data.mcp_command = JSON.parse(data.mcp_command);
        } catch {
          // Invalid JSON, keep as string (will fail backend validation, but that's OK)
        }
      }
      // Ensure it's a list or null
      if (
        !data.mcp_command ||
        (typeof data.mcp_command === 'string' && data.mcp_command.trim() === '')
      ) {
        // Should have been validated as required, but handle edge case
        data.mcp_command = null;
      }
    } else {
      // For HTTP/SSE, mcp_command must be null (not empty string)
      data.mcp_command = null;
    }

    // Clean up mcp_endpoint based on server type
    if (serverType === 'http' || serverType === 'sse') {
      // Endpoint should be present (validated)
      if (!data.mcp_endpoint || data.mcp_endpoint.trim() === '') {
        data.mcp_endpoint = null;
      }
    } else {
      // For STDIO, endpoint must be null
      data.mcp_endpoint = null;
    }

    this.onMcpConfigComplete(data);
  }

  /**
   * URL validator for MCP endpoints
   */
  private urlValidator = (
    control: AbstractControl
  ): ValidationErrors | null => {
    if (!control.value) {
      return null; // Let required validator handle empty values
    }
    try {
      const url = new URL(control.value);
      // Validate it's HTTP or HTTPS
      if (!['http:', 'https:'].includes(url.protocol)) {
        return {
          url: {
            value: control.value,
            message: 'URL must use http:// or https://',
          },
        };
      }
      return null;
    } catch {
      return { url: { value: control.value, message: 'Invalid URL format' } };
    }
  };

  /**
   * Update MCP form validators based on server type
   */
  private updateMcpValidators(serverType: string | null): void {
    const commandControl = this.mcpConfigForm.get('mcp_command');
    const endpointControl = this.mcpConfigForm.get('mcp_endpoint');

    if (serverType === 'stdio') {
      commandControl?.setValidators([Validators.required]);
      endpointControl?.clearValidators();
      // Clear endpoint value when switching to STDIO
      if (endpointControl?.value) {
        endpointControl.setValue(null);
      }
    } else if (serverType === 'http' || serverType === 'sse') {
      endpointControl?.setValidators([Validators.required, this.urlValidator]);
      commandControl?.clearValidators();
      // Clear command value when switching to HTTP/SSE
      if (commandControl?.value) {
        commandControl.setValue(null);
      }
    } else {
      commandControl?.clearValidators();
      endpointControl?.clearValidators();
    }

    commandControl?.updateValueAndValidity();
    endpointControl?.updateValueAndValidity();
  }

  private getFirstFormError(form: FormGroup): string | null {
    for (const controlName in form.controls) {
      const control = form.get(controlName);
      if (control && control.invalid && control.errors) {
        const errors = control.errors;
        if (errors['required']) {
          return `${controlName.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())} is required`;
        }
        if (errors['url']) {
          return errors['url'].message || 'Invalid URL format';
        }
        if (errors['min']) {
          return `${controlName} must be at least ${errors['min'].min}`;
        }
        if (errors['max']) {
          return `${controlName} must be at most ${errors['max'].max}`;
        }
      }
    }
    return 'Please fix form errors before continuing';
  }

  async onMcpConfigComplete(data: Record<string, any>): Promise<void> {
    this.loading = true;
    this.error = null;

    try {
      const response = await this.registrationService
        .processPhase({
          session_id: this.sessionId,
          phase: ToolRegistrationPhase.MCP_CONFIG,
          data,
        })
        .toPromise();

      if (response) {
        this.mcpConfig = data;
        this.validationErrors = response.validation_errors;

        if (response.can_proceed) {
          this.stepper.next();
          this.triggerDraftSave();
        } else {
          // Show backend validation errors
          const errors = response.validation_errors;
          if (errors && Object.keys(errors).length > 0) {
            const errorMessages = Object.values(errors).flat();
            const errorMsg = errorMessages.join('; ');
            this.error = errorMsg;
            this.snackBar.open(errorMsg, 'Close', { duration: 7000 });
            // Mark form fields as touched to show errors
            this.mcpConfigForm.markAllAsTouched();
          }
        }
      }
    } catch (err: any) {
      const errorMsg =
        err.error?.detail ||
        err.error?.message ||
        'Failed to process MCP config';
      this.error = errorMsg;
      this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
    } finally {
      this.loading = false;
    }
  }

  async testConnection(): Promise<void> {
    this.loading = true;
    this.error = null;

    try {
      const response = await this.registrationService
        .processPhase({
          session_id: this.sessionId,
          phase: ToolRegistrationPhase.CONNECTION_TEST,
          data: { action: 'test' },
        })
        .toPromise();

      if (response) {
        this.connectionResult = response.discovered_capabilities || {
          success: response.can_proceed,
          error: response.message,
        };
        this.validationErrors = response.validation_errors;

        if (response.can_proceed) {
          this.snackBar.open('Connection test successful!', 'Close', {
            duration: 3000,
          });
        } else {
          this.snackBar.open('Connection test failed', 'Close', {
            duration: 5000,
          });
        }
      }
    } catch (err: any) {
      const errorMsg = err.error?.detail || 'Connection test failed';
      this.error = errorMsg;
      this.connectionResult = { success: false, error: errorMsg };
      this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
    } finally {
      this.loading = false;
    }
  }

  async onConnectionTestComplete(result: Record<string, any>): Promise<void> {
    this.connectionResult = result;
    this.stepper.next();
    this.triggerDraftSave();
  }

  onSecuritySubmit(): void {
    if (this.securityForm.invalid) {
      return;
    }
    const data = this.securityForm.value;
    this.onSecurityConfigComplete(data);
  }

  async onSecurityConfigComplete(data: Record<string, any>): Promise<void> {
    this.loading = true;
    this.error = null;

    try {
      const response = await this.registrationService
        .processPhase({
          session_id: this.sessionId,
          phase: ToolRegistrationPhase.SECURITY_CONFIG,
          data,
        })
        .toPromise();

      if (response) {
        this.securityConfig = data;
        this.validationErrors = response.validation_errors;

        if (response.can_proceed) {
          this.stepper.next();
          this.triggerDraftSave();
        } else {
          // Show backend validation errors
          const errors = response.validation_errors;
          if (errors && Object.keys(errors).length > 0) {
            const errorMessages = Object.values(errors).flat();
            const errorMsg = errorMessages.join('; ');
            this.error = errorMsg;
            this.snackBar.open(errorMsg, 'Close', { duration: 7000 });
            // Mark form fields as touched to show errors
            this.securityForm.markAllAsTouched();
          }
        }
      }
    } catch (err: any) {
      const errorMsg = err.error?.detail || 'Failed to process security config';
      this.error = errorMsg;

      // Handle session expiration/not found
      if (errorMsg.includes('not found') || errorMsg.includes('expired')) {
        this.sessionId = null;
        this.snackBar.open(
          'Session expired. Please go back to Basic Information and try again.',
          'Close',
          { duration: 7000 }
        );
      } else {
        this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
      }
    } finally {
      this.loading = false;
    }
  }

  onPermissionsSubmit(): void {
    if (this.permissionsForm.invalid) {
      return;
    }
    const data = this.permissionsForm.value;
    this.onPermissionsComplete(data);
  }

  async onPermissionsComplete(data: Record<string, any>): Promise<void> {
    this.loading = true;
    this.error = null;

    try {
      const response = await this.registrationService
        .processPhase({
          session_id: this.sessionId,
          phase: ToolRegistrationPhase.PERMISSIONS,
          data,
        })
        .toPromise();

      if (response) {
        this.permissionsConfig = data;
        this.validationErrors = response.validation_errors;

        if (response.can_proceed) {
          this.stepper.next();
          this.triggerDraftSave();
        } else {
          // Show backend validation errors
          const errors = response.validation_errors;
          if (errors && Object.keys(errors).length > 0) {
            const errorMessages = Object.values(errors).flat();
            const errorMsg = errorMessages.join('; ');
            this.error = errorMsg;
            this.snackBar.open(errorMsg, 'Close', { duration: 7000 });
            // Mark form fields as touched to show errors
            this.permissionsForm.markAllAsTouched();
          }
        }
      }
    } catch (err: any) {
      const errorMsg = err.error?.detail || 'Failed to process permissions';
      this.error = errorMsg;

      // Handle session expiration/not found
      if (errorMsg.includes('not found') || errorMsg.includes('expired')) {
        this.sessionId = null;
        this.snackBar.open(
          'Session expired. Please go back to Basic Information and try again.',
          'Close',
          { duration: 7000 }
        );
      } else {
        this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
      }
    } finally {
      this.loading = false;
    }
  }

  async onReviewConfirm(): Promise<void> {
    this.loading = true;
    this.error = null;

    try {
      // First confirm review
      await this.registrationService
        .processPhase({
          session_id: this.sessionId,
          phase: ToolRegistrationPhase.REVIEW,
          data: { action: 'confirm' },
        })
        .toPromise();

      // Then commit
      const response = await this.registrationService
        .processPhase({
          session_id: this.sessionId,
          phase: ToolRegistrationPhase.COMMIT,
          data: { confirmed: true },
        })
        .toPromise();

      if (response?.tool_id) {
        // Success! Clear draft and navigate
        this.draftStorage.clearDraft(this.currentUserId);
        const toolName = this.basicInfo['name'] || 'Tool';
        this.snackBar.open(
          `Tool '${toolName}' registered successfully!`,
          'Close',
          { duration: 5000 }
        );
        this.router.navigate(['/admin/tools']);
      }
    } catch (err: any) {
      const errorMsg = err.error?.detail || 'Failed to commit registration';
      this.error = errorMsg;

      // Handle session expiration/not found
      if (errorMsg.includes('not found') || errorMsg.includes('expired')) {
        this.sessionId = null;
        this.snackBar.open(
          'Session expired. Please start the registration process again.',
          'Close',
          { duration: 7000 }
        );
      } else {
        this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
      }
    } finally {
      this.loading = false;
    }
  }

  onCancel(): void {
    if (
      confirm(
        'Are you sure you want to cancel? Your draft will be saved for 1 hour.'
      )
    ) {
      if (this.sessionId) {
        this.registrationService.cancelRegistration(this.sessionId).subscribe();
      }
      this.router.navigate(['/admin/tools']);
    }
  }
}
