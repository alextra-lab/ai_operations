import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ValidationReport } from '../../models/validation-report.model';
import { ValidationReportComponent } from './validation-report.component';

describe('ValidationReportComponent', () => {
  let component: ValidationReportComponent;
  let fixture: ComponentFixture<ValidationReportComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ValidationReportComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(ValidationReportComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display validation report', () => {
    const mockReport: ValidationReport = {
      use_case_id: 'test-001',
      is_valid: true,
      can_publish: true,
      issues: [],
      errors: [],
      warnings: [],
      infos: [],
      validated_at: new Date().toISOString(),
    };

    component.report = mockReport;
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('mat-card-title')).toBeTruthy();
  });

  it('should display errors', () => {
    const mockReport: ValidationReport = {
      use_case_id: 'test-001',
      is_valid: false,
      can_publish: false,
      issues: [
        {
          rule_id: 'test-rule',
          severity: 'error',
          message: 'Test error message',
        },
      ],
      errors: [
        {
          rule_id: 'test-rule',
          severity: 'error',
          message: 'Test error message',
        },
      ],
      warnings: [],
      infos: [],
      validated_at: new Date().toISOString(),
    };

    component.report = mockReport;
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('1 Error(s)');
  });

  it('should emit autoFixApplied event', () => {
    const mockReport: ValidationReport = {
      use_case_id: 'test-001',
      is_valid: false,
      can_publish: false,
      issues: [],
      errors: [],
      warnings: [],
      infos: [],
      validated_at: new Date().toISOString(),
    };

    component.report = mockReport;

    const issue = {
      rule_id: 'test-rule',
      severity: 'error' as const,
      message: 'Test error',
      auto_fix: { test: 'fix' },
    };

    jest.spyOn(component.autoFixApplied, 'emit');

    component.applyAutoFix(issue);

    expect(component.autoFixApplied.emit).toHaveBeenCalledWith(issue);
  });
});
