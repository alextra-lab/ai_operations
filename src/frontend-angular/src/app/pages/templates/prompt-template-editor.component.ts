/**
 * Prompt Template Editor Component
 *
 * Comprehensive editor for creating and editing prompt templates
 * with automatic variable detection, validation, and metadata management.
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, takeUntil } from 'rxjs/operators';

import { LucideAngularModule } from 'lucide-angular';
import {
  TemplateCreate,
  TemplateResponse,
  TemplateUpdate,
} from '../../api/models/template.models';
import { TemplateService } from '../../api/services/template.service';

@Component({
  selector: 'app-prompt-template-editor',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTabsModule,
  ],
  templateUrl: './prompt-template-editor.component.html',
  styleUrls: ['./prompt-template-editor.component.scss'],
})
export class PromptTemplateEditorComponent implements OnInit, OnDestroy {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  templateForm: FormGroup;
  metadataForm: FormGroup;

  // State
  isEditMode = false;
  templateId: string | null = null;
  currentTemplate: TemplateResponse | null = null;
  saving = false;
  loading = false;

  // Variable detection
  detectedVariables: string[] = [];

  // Deployment status options
  deploymentStatuses = [
    { value: 'draft', label: 'Draft' },
    { value: 'pending', label: 'Pending Review' },
    { value: 'approved', label: 'Approved' },
    { value: 'deployed', label: 'Deployed' },
  ];

  // Prompt type options
  promptTypes = [
    { value: 'system', label: 'System Prompt' },
    { value: 'user', label: 'User Prompt' },
    { value: 'assistant', label: 'Assistant Prompt' },
  ];

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private templateService: TemplateService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.templateForm = this.fb.group({
      template_id: [
        '',
        [
          Validators.required,
          Validators.pattern(/^[a-z0-9_-]+$/),
          Validators.maxLength(255),
        ],
      ],
      prompt_type: ['system', Validators.required],
      template_content: ['', [Validators.required, Validators.minLength(10)]],
      deployment_status: ['draft', Validators.required],
    });

    this.metadataForm = this.fb.group({
      category: [''],
      description: [''],
      author: [''],
      tags: [''],
    });
  }

  ngOnInit(): void {
    // Check if we're in edit mode
    this.route.paramMap.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      this.templateId = params.get('id');
      if (this.templateId) {
        this.isEditMode = true;
        this.loadTemplate(this.templateId);
        // Disable template_id field in edit mode
        this.templateForm.get('template_id')?.disable();
      }
    });

    // Setup variable detection on content changes
    this.setupVariableDetection();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========================================================================
  // Data Loading
  // ========================================================================

  loadTemplate(templateId: string): void {
    this.loading = true;
    this.templateService
      .getTemplate(templateId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (template) => {
          this.currentTemplate = template;
          this.populateForm(template);
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.snackBar.open(
            `Error loading template: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  private populateForm(template: TemplateResponse): void {
    this.templateForm.patchValue({
      template_id: template.template_id,
      prompt_type: template.prompt_type,
      template_content: template.template_content,
      deployment_status: template.deployment_status,
    });

    // Populate metadata
    if (template.metadata_json) {
      this.metadataForm.patchValue({
        category: template.metadata_json['category'] || '',
        description: template.metadata_json['description'] || '',
        author: template.metadata_json['author'] || '',
        tags: template.metadata_json['tags']?.join(', ') || '',
      });
    }

    // Detect variables
    this.detectVariables();
  }

  // ========================================================================
  // Variable Detection
  // ========================================================================

  private setupVariableDetection(): void {
    this.templateForm
      .get('template_content')
      ?.valueChanges.pipe(debounceTime(500), takeUntil(this.destroy$))
      .subscribe(() => {
        this.detectVariables();
      });
  }

  detectVariables(): void {
    const content = this.templateForm.get('template_content')?.value || '';
    const variableRegex = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
    const matches = content.matchAll(variableRegex);
    const variables = new Set<string>();

    for (const match of matches) {
      variables.add(match[1]);
    }

    this.detectedVariables = Array.from(variables).sort();
  }

  // ========================================================================
  // Save/Update Operations
  // ========================================================================

  saveTemplate(): void {
    if (this.templateForm.invalid) {
      this.snackBar.open('Please complete all required fields', 'Close', {
        duration: 3000,
        panelClass: ['error-snackbar'],
      });
      return;
    }

    this.saving = true;

    if (this.isEditMode && this.templateId) {
      this.updateTemplate();
    } else {
      this.createTemplate();
    }
  }

  private createTemplate(): void {
    const formValue = this.templateForm.getRawValue();
    const metadataValue = this.metadataForm.value;

    const templateData: TemplateCreate = {
      template_id: formValue.template_id,
      prompt_type: formValue.prompt_type,
      template_content: formValue.template_content,
      variables: this.detectedVariables,
      metadata_json: this.buildMetadata(metadataValue),
      deployment_status: formValue.deployment_status,
    };

    this.templateService
      .createTemplate(templateData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (template) => {
          this.snackBar.open('Template created successfully', 'Close', {
            duration: 3000,
          });
          this.saving = false;
          queueMicrotask(() => this.cdr.detectChanges());
          this.router.navigate(['/templates/library']);
        },
        error: (error) => {
          this.snackBar.open(
            `Error creating template: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.saving = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  private updateTemplate(): void {
    const formValue = this.templateForm.getRawValue();
    const metadataValue = this.metadataForm.value;

    const updates: TemplateUpdate = {
      template_content: formValue.template_content,
      variables: this.detectedVariables,
      metadata_json: this.buildMetadata(metadataValue),
      deployment_status: formValue.deployment_status,
    };

    if (this.templateId) {
      this.templateService
        .updateTemplate(this.templateId, updates)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.snackBar.open('Template updated successfully', 'Close', {
              duration: 3000,
            });
            this.saving = false;
            queueMicrotask(() => this.cdr.detectChanges());
            this.router.navigate(['/templates/library']);
          },
          error: (error) => {
            this.snackBar.open(
              `Error updating template: ${error.message}`,
              'Close',
              { duration: 5000, panelClass: ['error-snackbar'] }
            );
            this.saving = false;
            queueMicrotask(() => this.cdr.detectChanges());
          },
        });
    }
  }

  private buildMetadata(metadataValue: any): Record<string, any> {
    const metadata: Record<string, any> = {};

    if (metadataValue.category) metadata['category'] = metadataValue.category;
    if (metadataValue.description)
      metadata['description'] = metadataValue.description;
    if (metadataValue.author) metadata['author'] = metadataValue.author;
    if (metadataValue.tags) {
      const tags = metadataValue.tags
        .split(',')
        .map((t: string) => t.trim())
        .filter((t: string) => t);
      if (tags.length > 0) metadata['tags'] = tags;
    }

    return metadata;
  }

  // ========================================================================
  // UI Actions
  // ========================================================================

  cancel(): void {
    this.router.navigate(['/templates/library']);
  }

  resetForm(): void {
    this.templateForm.reset({
      prompt_type: 'system',
      deployment_status: 'draft',
    });
    this.metadataForm.reset();
    this.detectedVariables = [];
  }

  // ========================================================================
  // Preview
  // ========================================================================

  getPreviewContent(): string {
    const content = this.templateForm.get('template_content')?.value || '';
    if (!content) {
      return 'Enter template content to see preview...';
    }

    // Replace variables with example values for preview
    let preview = content;
    this.detectedVariables.forEach((variable, index) => {
      const exampleValue = `[EXAMPLE_${variable.toUpperCase()}]`;
      preview = preview.replace(
        new RegExp(`\\{${variable}\\}`, 'g'),
        exampleValue
      );
    });

    return preview;
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }
}
