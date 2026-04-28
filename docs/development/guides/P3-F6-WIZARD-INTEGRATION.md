# P3-F6 Wizard Integration Guide

**Status:** Infrastructure Complete - Integration Pending
**Date:** October 21, 2025

---

## Overview

P3-F6 Use Case Validation & Testing infrastructure is complete. This document describes how to integrate validation into the Use Case wizard.

---

## Completed Infrastructure

### Backend ✅
- `ValidationEngine` - Core validation orchestration
- 9 validation rules (5 prompt, 4 config)
- Validation API endpoints (`/validate`, `/auto-fix`, `/test`, `/test-suite`)
- Test query execution service
- Database schema for test suites/results

### Frontend ✅
- `UseCaseValidationService` - API service
- `ValidationReportComponent` - Display validation issues
- `UseCaseTestPanelComponent` - Test query interface
- TypeScript models for validation/testing

### Documentation ✅
- User guide: `docs/user-guides/use-case-validation.md`
- Developer guide: `docs/development/guides/creating-validation-rules.md`

---

## Integration Steps

### Step 1: Add Components to Wizard

**File:** `src/frontend-angular/src/app/pages/use-case-wizard/use-case-wizard.component.ts`

```typescript
import { ValidationReportComponent } from '../../components/validation-report/validation-report.component';
import { UseCaseTestPanelComponent } from '../../components/use-case-test-panel/use-case-test-panel.component';
import { UseCaseValidationService } from '../../services/use-case-validation.service';

@Component({
  // ... existing config ...
  imports: [
    // ... existing imports ...
    ValidationReportComponent,
    UseCaseTestPanelComponent,
  ],
})
export class UseCaseWizardComponent {
  validationReport?: ValidationReport;
  showValidationPanel = false;

  constructor(
    // ... existing dependencies ...
    private validationService: UseCaseValidationService
  ) {}
}
```

### Step 2: Add Validation to Step 5 Template

**File:** `src/frontend-angular/src/app/pages/use-case-wizard/use-case-wizard.component.html`

Add to Step 5 (Preview & Save):

```html
<!-- Step 5: Preview & Save -->
@if (currentStep === 5) {
  <!-- Existing preview content -->

  <!-- Validation Section -->
  <div class="validation-section mt-6">
    <h3 class="text-lg font-medium mb-4">Validation & Testing</h3>

    <button mat-raised-button
            color="primary"
            (click)="validateUseCase()"
            [disabled]="isValidating">
      <mat-icon>check_circle</mat-icon>
      Validate Use Case
    </button>

    @if (validationReport) {
      <app-validation-report
        [report]="validationReport"
        (autoFixApplied)="handleAutoFix($event)">
      </app-validation-report>
    }
  </div>

  <!-- Test Query Section -->
  <div class="test-query-section mt-6">
    <app-use-case-test-panel
      [useCaseId]="useCase.use_case_id">
    </app-use-case-test-panel>
  </div>
}
```

### Step 3: Implement Validation Methods

```typescript
async validateUseCase(): Promise<void> {
  if (!this.useCase.use_case_id) {
    this.snackBar.open('Save Use Case first', 'Close', { duration: 3000 });
    return;
  }

  this.isValidating = true;

  try {
    this.validationReport = await this.validationService
      .validateUseCase(this.useCase.use_case_id)
      .toPromise();

    if (this.validationReport.is_valid) {
      this.snackBar.open('✓ Validation passed', 'Close', { duration: 3000 });
    } else {
      this.snackBar.open(
        `${this.validationReport.errors.length} error(s) found`,
        'View',
        { duration: 5000 }
      );
    }
  } catch (error) {
    this.snackBar.open(`Validation error: ${error}`, 'Close', { duration: 5000 });
  } finally {
    this.isValidating = false;
  }
}

async handleAutoFix(issue: ValidationIssue): Promise<void> {
  const confirm = await this.confirmDialog.open({
    title: 'Apply Auto-Fix?',
    message: `This will automatically fix: ${issue.message}`
  }).afterClosed().toPromise();

  if (!confirm) return;

  try {
    const result = await this.validationService
      .autoFixIssues(this.useCase.use_case_id, [issue.rule_id])
      .toPromise();

    // Reload Use Case with fixes
    this.useCase = result.use_case;

    // Re-validate
    await this.validateUseCase();

    this.snackBar.open('Auto-fix applied successfully', 'Close', { duration: 3000 });
  } catch (error) {
    this.snackBar.open(`Auto-fix failed: ${error}`, 'Close', { duration: 5000 });
  }
}
```

### Step 4: Add Save-Time Validation Hook

```typescript
async saveUseCase(): Promise<void> {
  // Existing save logic...

  // Run validation
  try {
    const report = await this.validationService
      .validateUseCase(this.useCase.use_case_id)
      .toPromise();

    if (!report.is_valid) {
      const viewReport = await this.snackBar
        .open(`${report.errors.length} validation error(s)`, 'View', { duration: 5000 })
        .onAction()
        .toPromise();

      if (viewReport) {
        this.validationReport = report;
        this.showValidationPanel = true;
      }
    }
  } catch (error) {
    console.warn('Validation failed:', error);
    // Continue with save even if validation fails
  }

  // Continue with save...
}
```

### Step 5: Add Publish-Time Validation Block

```typescript
async publishUseCase(): Promise<void> {
  // Validate before publishing
  const report = await this.validationService
    .validateUseCase(this.useCase.use_case_id)
    .toPromise();

  if (!report.can_publish) {
    this.snackBar.open(
      `Cannot publish: ${report.errors.length} error(s) must be fixed`,
      'View Report',
      { duration: 5000 }
    ).onAction().subscribe(() => {
      this.validationReport = report;
      this.showValidationPanel = true;
    });
    return;
  }

  if (report.warnings.length > 0) {
    const confirm = await this.confirmDialog.open({
      title: 'Publish with Warnings?',
      message: `There are ${report.warnings.length} warning(s). Proceed anyway?`
    }).afterClosed().toPromise();

    if (!confirm) return;
  }

  // Proceed with publish...
  await this.useCaseService.changeLifecycleState(
    this.useCase.use_case_id,
    'published'
  );
}
```

---

## Testing Integration

### Manual Testing

1. Open Use Case wizard
2. Navigate to Step 5
3. Click "Validate Use Case"
4. Verify validation report displays
5. Click "Auto-Fix" on a fixable issue
6. Verify Use Case updates and re-validates
7. Enter test query and click "Run Test"
8. Verify test results display

### Unit Tests

```typescript
// File: src/frontend-angular/src/app/pages/use-case-wizard/use-case-wizard.component.spec.ts

describe('UseCaseWizardComponent - Validation', () => {
  it('should validate Use Case', async () => {
    // Arrange
    const mockReport: ValidationReport = {
      use_case_id: 'test-001',
      is_valid: true,
      can_publish: true,
      issues: [],
      errors: [],
      warnings: [],
      infos: [],
      validated_at: new Date().toISOString()
    };

    validationService.validateUseCase.and.returnValue(of(mockReport));

    // Act
    await component.validateUseCase();

    // Assert
    expect(component.validationReport).toEqual(mockReport);
  });

  it('should block publish with errors', async () => {
    // Test publish blocking logic
  });

  it('should apply auto-fix', async () => {
    // Test auto-fix workflow
  });
});
```

---

## ADR Compliance

### ADR-012 (Hybrid CSS)
- ✅ Components use Material + Tailwind
- ✅ No inline styles
- ✅ Accessibility preserved

### ADR-018 (Use Case Owned Architecture)
- ✅ Validation works with Use Case config_json
- ✅ No external template references

---

## Files to Modify

1. `src/frontend-angular/src/app/pages/use-case-wizard/use-case-wizard.component.ts` - Add validation methods
2. `src/frontend-angular/src/app/pages/use-case-wizard/use-case-wizard.component.html` - Add validation UI
3. `src/frontend-angular/src/app/pages/use-case-wizard/use-case-wizard.component.spec.ts` - Add tests

---

## Estimated Effort

- **Implementation:** 2-3 hours
- **Testing:** 1-2 hours
- **Total:** 3-5 hours

---

## Next Steps

1. Implement integration in wizard component
2. Run frontend tests (`npm test`)
3. Manual testing in browser
4. Update MASTER_ROADMAP.md with completion status

---

**Status:** Ready for integration
**Priority:** Must-complete (Phase 4 Week 2)
