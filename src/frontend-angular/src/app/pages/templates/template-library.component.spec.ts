/**
 * Template Library Component Unit Tests
 */

import {
  ComponentFixture,
  fakeAsync,
  TestBed,
  tick,
} from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import {
  TemplateListResponse,
  TemplateResponse,
} from '../../api/models/template.models';
import { TemplateService } from '../../api/services/template.service';
import { TemplateLibraryComponent } from './template-library.component';

describe('TemplateLibraryComponent', () => {
  let component: TemplateLibraryComponent;
  let fixture: ComponentFixture<TemplateLibraryComponent>;
  let templateService: any;
  let router: any;
  let snackBar: any;

  const mockTemplate: TemplateResponse = {
    id: 'uuid-1',
    template_id: 'test_template',
    prompt_type: 'system',
    template_content: 'Test content {var1}',
    variables: ['var1'],
    metadata_json: {},
    version_number: 1,
    is_active_version: true,
    deployment_status: 'draft',
    created_at: '2025-10-13T00:00:00Z',
    updated_at: '2025-10-13T00:00:00Z',
  };

  const mockListResponse: TemplateListResponse = {
    templates: [mockTemplate],
    total_count: 1,
    page: 1,
    page_size: 50,
  };

  beforeEach(async () => {
    const templateServiceMock = {
      listTemplates: jest.fn(),
      deleteTemplate: jest.fn(),
      approveTemplate: jest.fn(),
      rejectTemplate: jest.fn(),
      getDeploymentStatusClass: jest.fn().mockReturnValue('bg-gray-100'),
      getDeploymentStatusName: jest.fn().mockReturnValue('Draft'),
    };
    const routerMock = {
      navigate: jest.fn(),
    };
    const snackBarMock = {
      open: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [TemplateLibraryComponent, BrowserAnimationsModule],
      providers: [
        { provide: TemplateService, useValue: templateServiceMock },
        { provide: Router, useValue: routerMock },
        { provide: MatSnackBar, useValue: snackBarMock },
      ],
    }).compileComponents();

    templateService = TestBed.inject(TemplateService) as any;
    router = TestBed.inject(Router) as any;
    snackBar = TestBed.inject(MatSnackBar) as any;

    (templateService.listTemplates as jest.Mock).mockReturnValue(
      of(mockListResponse)
    );

    fixture = TestBed.createComponent(TemplateLibraryComponent);
    component = fixture.componentInstance;
    (component as any).snackBar = snackBar;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load templates on init', () => {
    fixture.detectChanges();

    expect(templateService.listTemplates).toHaveBeenCalled();
    expect(component.templates).toEqual([mockTemplate]);
    expect(component.totalCount).toBe(1);
  });

  it('should handle load error', fakeAsync(() => {
    jest.clearAllMocks();
    (templateService.listTemplates as jest.Mock).mockReturnValue(
      throwError(() => new Error('Load failed'))
    );

    const errorFixture = TestBed.createComponent(TemplateLibraryComponent);
    const errorComponent = errorFixture.componentInstance;
    (errorComponent as any).snackBar = snackBar;
    errorFixture.detectChanges();
    tick();

    expect(snackBar.open).toHaveBeenCalled();
    expect(errorComponent.isLoading).toBe(false);
  }));

  it('should navigate to template detail on view', () => {
    component.viewTemplate(mockTemplate);

    expect(router.navigate).toHaveBeenCalledWith([
      '/templates',
      mockTemplate.template_id,
    ]);
  });

  it('should navigate to editor on edit', () => {
    component.editTemplate(mockTemplate);

    expect(router.navigate).toHaveBeenCalledWith([
      '/templates',
      mockTemplate.template_id,
      'edit',
    ]);
  });

  it('should delete template with confirmation', fakeAsync(() => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    (templateService.deleteTemplate as jest.Mock).mockReturnValue(
      of({ message: 'Deleted', versions_deleted: 1 })
    );
    (templateService.listTemplates as jest.Mock).mockReturnValue(
      of({ templates: [], total_count: 0, page: 1, page_size: 50 })
    );

    component.deleteTemplate(mockTemplate);
    tick();
    fixture.detectChanges();

    expect(templateService.deleteTemplate).toHaveBeenCalledWith(
      'test_template'
    );
    expect(snackBar.open).toHaveBeenCalledWith(
      'Template deleted: 1 versions removed',
      'Close',
      { duration: 3000 }
    );
  }));

  it('should not delete template if user cancels', () => {
    jest.spyOn(window, 'confirm').mockReturnValue(false);

    component.deleteTemplate(mockTemplate);

    expect(templateService.deleteTemplate).not.toHaveBeenCalled();
  });

  it('should approve template with notes', () => {
    jest.spyOn(window, 'prompt').mockReturnValue('Approval notes');
    (templateService.approveTemplate as jest.Mock).mockReturnValue(
      of(mockTemplate)
    );

    component.approveTemplate(mockTemplate);

    expect(templateService.approveTemplate).toHaveBeenCalledWith(
      'test_template',
      'Approval notes'
    );
  });

  it('should reject template with reason', () => {
    jest.spyOn(window, 'prompt').mockReturnValue('Rejection reason');
    (templateService.rejectTemplate as jest.Mock).mockReturnValue(
      of(mockTemplate)
    );

    component.rejectTemplate(mockTemplate);

    expect(templateService.rejectTemplate).toHaveBeenCalledWith(
      'test_template',
      'Rejection reason'
    );
  });

  it('should handle pagination', () => {
    fixture.detectChanges();

    const event = { pageIndex: 1, pageSize: 25, length: 100 };
    component.onPageChange(event as any);

    expect(component.currentPage).toBe(2);
    expect(component.pageSize).toBe(25);
    expect(templateService.listTemplates).toHaveBeenCalled();
  });

  it('should apply filters', (done) => {
    fixture.detectChanges();

    component.filterForm.patchValue({
      searchTerm: 'test',
      deploymentStatus: 'approved',
    });

    // Wait for debounce
    setTimeout(() => {
      expect(templateService.listTemplates).toHaveBeenCalledWith(
        expect.objectContaining({
          template_id_filter: 'test',
          deployment_status: 'approved',
        })
      );
      done();
    }, 400);
  });

  it('should format date correctly', () => {
    const date = '2025-10-13T12:00:00Z';
    const formatted = component.formatDate(date);

    expect(formatted).toContain('10/13/2025');
  });

  it('should check if template can be approved', () => {
    const pendingTemplate = { ...mockTemplate, deployment_status: 'pending' };
    expect(component.canApprove(pendingTemplate)).toBe(true);
    expect(component.canApprove(mockTemplate)).toBe(false);
  });

  it('should check if template can be rejected', () => {
    const pendingTemplate = { ...mockTemplate, deployment_status: 'pending' };
    const approvedTemplate = { ...mockTemplate, deployment_status: 'approved' };

    expect(component.canReject(pendingTemplate)).toBe(true);
    expect(component.canReject(approvedTemplate)).toBe(true);
    expect(component.canReject(mockTemplate)).toBe(false);
  });
});
