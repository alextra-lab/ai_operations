import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import {
  ValidationIssue,
  ValidationReport,
} from '../../models/validation-report.model';

/**
 * Component to display Use Case validation report with issues and auto-fix options.
 *
 * Follows ADR-012 Hybrid CSS Strategy:
 * - Material components for UI primitives
 * - Tailwind utilities for layout/spacing
 * - Component SCSS for complex states
 */
@Component({
  selector: 'app-validation-report',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatExpansionModule,
    MatListModule,
    MatButtonModule,
  ],
  templateUrl: './validation-report.component.html',
  styleUrls: ['./validation-report.component.scss'],
})
export class ValidationReportComponent {
  @Input() report!: ValidationReport;
  @Output() autoFixApplied = new EventEmitter<ValidationIssue>();

  applyAutoFix(issue: ValidationIssue): void {
    this.autoFixApplied.emit(issue);
  }
}
