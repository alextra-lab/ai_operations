/**
 * Output template selector for the Use Case wizard Output Contract section.
 * Displays built-in visualization templates and emits the selected template_id.
 *
 * @see USE_CASE_AUTHORING_COMPLETE_SPEC.md Phase 4
 */

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatRadioModule } from '@angular/material/radio';

import { OutputFormatTemplate } from '../../models/output-format.model';
import { TemplateRegistryService } from '../../services/template-registry.service';

@Component({
  selector: 'app-output-template-selector',
  templateUrl: './output-template-selector.component.html',
  styleUrls: ['./output-template-selector.component.scss'],
  standalone: true,
  imports: [CommonModule, MatRadioModule],
})
export class OutputTemplateSelectorComponent {
  @Input() selectedTemplateId: string | null = null;
  @Output() templateChange = new EventEmitter<string | null>();

  templates: OutputFormatTemplate[] = [];

  constructor(private templateRegistry: TemplateRegistryService) {
    this.templates = this.templateRegistry.list();
  }

  /**
   * Handle radio selection change; empty string means no template.
   */
  onSelectionChange(value: string): void {
    this.selectedTemplateId = value === '' ? null : value;
    this.templateChange.emit(this.selectedTemplateId);
  }
}
