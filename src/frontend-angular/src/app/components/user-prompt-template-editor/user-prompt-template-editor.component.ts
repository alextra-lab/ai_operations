/**
 * User prompt template editor for Use Case wizard Step 3.
 * Renders variable chips from input fields and a template textarea with
 * {{variable}} placeholders; supports preview with sample data.
 */

import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  Output,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  InputField,
  UserPromptTemplateConfig,
} from '../../api/models/use-case.models';
import { LucideAngularModule } from 'lucide-angular';

const VARIABLE_PATTERN = /\{\{(\w+)\}\}/g;

function extractTemplateVariables(template: string): string[] {
  const set = new Set<string>();
  let m: RegExpExecArray | null;
  VARIABLE_PATTERN.lastIndex = 0;
  while ((m = VARIABLE_PATTERN.exec(template)) !== null) {
    set.add(m[1]);
  }
  return Array.from(set);
}

function renderPreview(
  template: string,
  sampleValues: Record<string, string>
): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, name) => {
    return sampleValues[name] ?? `[${name}]`;
  });
}

@Component({
  selector: 'app-user-prompt-template-editor',
  templateUrl: './user-prompt-template-editor.component.html',
  styleUrls: ['./user-prompt-template-editor.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
  ],
})
export class UserPromptTemplateEditorComponent {
  @Input() inputFields: InputField[] = [];
  @Input() value: UserPromptTemplateConfig | null = null;
  @Output() valueChange = new EventEmitter<UserPromptTemplateConfig | null>();

  showPreview = signal(false);

  /** Literal text for panel description (contains {{variable}} for display). */
  panelDescriptionText =
    'How user inputs are merged into the prompt ({{variable}} placeholders)';
  /** Literal placeholder for textarea (contains {{...}} for display). */
  placeholderExample =
    'e.g. Analyze incident {{incident_id}} with severity {{severity}}...';

  get template(): string {
    return this.value?.template ?? '';
  }

  get fallbackMode(): 'concatenate' | 'error' {
    return this.value?.fallback_mode ?? 'concatenate';
  }

  get variableChips(): { name: string; placeholder: string }[] {
    return this.inputFields.map((f) => ({
      name: f.name,
      placeholder: `{{${f.name}}}`,
    }));
  }

  get templateVariables(): string[] {
    return extractTemplateVariables(this.template);
  }

  get variableStatus(): { name: string; defined: boolean }[] {
    const fieldNames = new Set(this.inputFields.map((f) => f.name));
    return this.templateVariables.map((name) => ({
      name,
      defined: fieldNames.has(name),
    }));
  }

  get previewText(): string {
    const sample: Record<string, string> = {};
    this.inputFields.forEach((f) => {
      if (f.options?.length) {
        sample[f.name] = String(f.options[0].value);
      } else {
        sample[f.name] = `Sample ${f.label ?? f.name}`;
      }
    });
    return renderPreview(this.template, sample);
  }

  onTemplateInput(template: string): void {
    const trimmed = template.trim();
    if (!trimmed) {
      this.valueChange.emit(null);
      return;
    }
    const variables = extractTemplateVariables(trimmed);
    this.valueChange.emit({
      template: trimmed,
      variables,
      fallback_mode: this.fallbackMode,
    });
  }

  onFallbackModeChange(mode: 'concatenate' | 'error'): void {
    if (!this.template.trim()) {
      this.valueChange.emit(null);
      return;
    }
    this.valueChange.emit({
      template: this.template,
      variables: this.templateVariables,
      fallback_mode: mode,
    });
  }

  insertVariable(placeholder: string, textarea: HTMLTextAreaElement): void {
    const start = textarea.selectionStart ?? 0;
    const end = textarea.selectionEnd ?? start;
    const before = this.template.slice(0, start);
    const after = this.template.slice(end);
    const next = before + placeholder + after;
    this.onTemplateInput(next);
    setTimeout(() => {
      const newPos = start + placeholder.length;
      textarea.setSelectionRange(newPos, newPos);
      textarea.focus();
    }, 0);
  }

  togglePreview(): void {
    this.showPreview.update((v) => !v);
  }
}
