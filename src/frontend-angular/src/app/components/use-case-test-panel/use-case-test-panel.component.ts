import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { TestQueryResult } from '../../models/test-query-result.model';
import { UseCaseValidationService } from '../../services/use-case-validation.service';

/**
 * Component for testing Use Cases with sample queries.
 *
 * Follows ADR-012 Hybrid CSS Strategy:
 * - Material components for UI primitives
 * - Tailwind utilities for layout/spacing
 * - Component SCSS for complex states
 */
@Component({
  selector: 'app-use-case-test-panel',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatExpansionModule,
    MatChipsModule,
    MatSnackBarModule,
  ],
  templateUrl: './use-case-test-panel.component.html',
  styleUrls: ['./use-case-test-panel.component.scss'],
})
export class UseCaseTestPanelComponent {
  @Input() useCaseId!: string;

  testQuery = '';
  expectedOutputJson = '';
  testResult?: TestQueryResult;
  isExecuting = false;

  constructor(
    private validationService: UseCaseValidationService,
    private snackBar: MatSnackBar
  ) {}

  async executeTest(): Promise<void> {
    if (!this.testQuery) {
      return;
    }

    this.isExecuting = true;

    try {
      // Parse expected output if provided
      let expectedOutput: Record<string, any> | undefined = undefined;
      if (this.expectedOutputJson.trim()) {
        try {
          expectedOutput = JSON.parse(this.expectedOutputJson);
        } catch (e) {
          this.snackBar.open('Invalid expected output JSON', 'Close', {
            duration: 3000,
          });
          this.isExecuting = false;
          return;
        }
      }

      // Execute test
      this.testResult = await firstValueFrom(
        this.validationService.testQuery(
          this.useCaseId,
          this.testQuery,
          expectedOutput
        )
      );

      // Show notification
      if (this.testResult?.success) {
        this.snackBar.open(
          `Test passed in ${this.testResult.execution_time_ms}ms`,
          'Close',
          { duration: 3000 }
        );
      } else {
        this.snackBar.open('Test failed', 'Close', { duration: 3000 });
      }
    } catch (error) {
      this.snackBar.open(`Test error: ${error}`, 'Close', { duration: 5000 });
    } finally {
      this.isExecuting = false;
    }
  }
}
