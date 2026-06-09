import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

// Angular Material imports
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subject } from 'rxjs';

import { LucideAngularModule } from 'lucide-angular';
import { ModelDetailedResponse } from '../../api/models/model-registry.models';
import { ModelSelectorComponent } from '../../components/model-selector/model-selector.component';

@Component({
  selector: 'app-template-editor',
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
    ModelSelectorComponent,
  ],
  templateUrl: './template-editor.component.html',
  styleUrls: ['./template-editor.component.scss'],
})
export class TemplateEditorComponent implements OnInit, OnDestroy {
  templateForm: FormGroup;
  selectedLLMModelId?: string;
  selectedLLMModel?: ModelDetailedResponse;
  saving = false;

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private snackBar: MatSnackBar
  ) {
    this.templateForm = this.fb.group({
      useCaseId: [
        '',
        [Validators.required, Validators.pattern(/^[a-z0-9_-]+$/)],
      ],
      name: ['', Validators.required],
      description: [''],
      intentType: ['query', Validators.required],
      temperature: [
        0.7,
        [Validators.required, Validators.min(0), Validators.max(2)],
      ],
      maxTokens: [1024, [Validators.required, Validators.min(100)]],
    });
  }

  ngOnInit(): void {
    // Setup form subscriptions if needed
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // =========================================================================
  // Model Selection
  // =========================================================================

  onLLMModelSelected(model: ModelDetailedResponse): void {
    this.selectedLLMModel = model;
    this.selectedLLMModelId = model.model_id;

    // Update max tokens based on model capabilities
    if (model.max_output_tokens) {
      this.templateForm.patchValue({
        maxTokens: Math.min(
          this.templateForm.get('maxTokens')?.value || 1024,
          model.max_output_tokens
        ),
      });
    }

    this.snackBar.open(`Selected model: ${model.name}`, 'Close', {
      duration: 2000,
    });
  }

  // =========================================================================
  // Template Actions
  // =========================================================================

  saveTemplate(): void {
    if (this.templateForm.invalid || !this.selectedLLMModel) {
      this.snackBar.open(
        'Please complete all required fields and select a model',
        'Close',
        {
          duration: 3000,
          panelClass: ['error-snackbar'],
        }
      );
      return;
    }

    this.saving = true;

    const config = this.buildUseCaseConfig();

    // TODO: Call use case service to save template
    // For now, just show preview
    setTimeout(() => {
      this.saving = false;
      this.snackBar.open(
        'Template configuration ready (save API not yet implemented)',
        'Close',
        {
          duration: 3000,
        }
      );
    }, 1000);
  }

  resetForm(): void {
    this.templateForm.reset({
      intentType: 'query',
      temperature: 0.7,
      maxTokens: 1024,
    });
    this.selectedLLMModel = undefined;
    this.selectedLLMModelId = undefined;
  }

  // =========================================================================
  // Config Building
  // =========================================================================

  buildUseCaseConfig(): any {
    const formValue = this.templateForm.value;

    return {
      use_case_id: formValue.useCaseId,
      name: formValue.name,
      description: formValue.description,
      intent_type: formValue.intentType,
      config_json: {
        models: {
          llm: this.selectedLLMModel?.model_id,
        },
        generation_params: {
          temperature: formValue.temperature,
          max_tokens: formValue.maxTokens,
        },
        rag: {
          enabled: true,
          top_k: 10,
        },
      },
    };
  }

  getConfigPreview(): string {
    if (!this.selectedLLMModel) {
      return '// Select a model to see configuration preview';
    }

    const config = this.buildUseCaseConfig();
    return JSON.stringify(config, null, 2);
  }
}
