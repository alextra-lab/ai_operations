/**
 * Template Detail Component Unit Tests
 */

import {
  ComponentFixture,
  fakeAsync,
  TestBed,
  tick,
} from '@angular/core/testing';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import {
  TemplateDiffResponse,
  TemplateResponse,
  TemplateVersionListResponse,
} from '../../api/models/template.models';
import { TemplateService } from '../../api/services/template.service';
import { TemplateDetailComponent } from './template-detail.component';

describe('TemplateDetailComponent', () => {
  let component: TemplateDetailComponent;
  let fixture: ComponentFixture<TemplateDetailComponent>;
  let templateService: any;
  let router: any;
  let snackBar: any;
  let activatedRoute: any;
  let dialog: any;

  const mockTemplate: TemplateResponse = {
    id: 'uuid-1',
    template_id: 'test_template',
    prompt_type: 'system',
    template_content: 'Content {var1}',
    variables: ['var1'],
    metadata_json: { category: 'test' },
    version_number: 1,
    is_active_version: true,
    deployment_status: 'draft',
    created_at: '2025-10-13T00:00:00Z',
    updated_at: '2025-10-13T00:00:00Z',
  };

  const mockVersionList: TemplateVersionListResponse = {
    template_id: 'test_template',
    versions: [
      {
        id: 'uuid-1',
        template_id: 'test_template',
        version_number: 1,
        is_active_version: true,
        deployment_status: 'draft',
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:00:00Z',
      },
    ],
    total_versions: 1,
  };

  beforeEach(async () => {
    const templateServiceMock = {
      getTemplate: jest.fn().mockReturnValue(of(mockTemplate)),
      getTemplateVersions: jest.fn().mockReturnValue(of(mockVersionList)),
      createTemplateVersion: jest.fn(),
      activateTemplateVersion: jest.fn(),
      compareTemplateVersions: jest.fn(),
      approveTemplate: jest.fn(),
      rejectTemplate: jest.fn(),
      deleteTemplate: jest.fn(),
      getDeploymentStatusClass: jest.fn().mockReturnValue('bg-gray-100'),
      getDeploymentStatusName: jest.fn().mockReturnValue('Draft'),
    };
    const routerMock = {
      navigate: jest.fn(),
    };
    const snackBarMock = {
      open: jest.fn(),
    };

    const paramMapMock = new Map([['id', 'test_template']]);
    activatedRoute = {
      paramMap: of(paramMapMock),
      params: of({ id: 'test_template' }),
      queryParams: of({}),
      snapshot: {
        params: { id: 'test_template' },
        queryParams: {},
        paramMap: {
          get: jest.fn().mockReturnValue('test_template'),
          has: jest.fn().mockReturnValue(true),
          keys: ['id'],
          getAll: jest.fn().mockReturnValue(['test_template']),
        },
        queryParamMap: {
          get: jest.fn().mockReturnValue(null),
          has: jest.fn().mockReturnValue(false),
          keys: [],
          getAll: jest.fn().mockReturnValue([]),
        },
        url: [],
        fragment: null,
        data: {},
        outlet: 'primary',
        component: null,
        routeConfig: null,
        root: null,
        parent: null,
        firstChild: null,
        children: [],
      },
    };

    const dialogMock = {
      open: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [
        TemplateDetailComponent,
        ReactiveFormsModule,
        BrowserAnimationsModule,
      ],
      providers: [
        FormBuilder,
        { provide: TemplateService, useValue: templateServiceMock },
        { provide: Router, useValue: routerMock },
        { provide: ActivatedRoute, useValue: activatedRoute },
        { provide: MatSnackBar, useValue: snackBarMock },
        { provide: MatDialog, useValue: dialogMock },
      ],
    }).compileComponents();

    templateService = TestBed.inject(TemplateService);
    router = TestBed.inject(Router);
    snackBar = TestBed.inject(MatSnackBar);
    dialog = TestBed.inject(MatDialog);

    fixture = TestBed.createComponent(TemplateDetailComponent);
    component = fixture.componentInstance;
    (component as any).snackBar = snackBar;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load template details on init', () => {
    fixture.detectChanges();

    expect(component.templateId).toBe('test_template');
    expect(templateService.getTemplate).toHaveBeenCalledWith('test_template');
    expect(templateService.getTemplateVersions).toHaveBeenCalledWith(
      'test_template'
    );
    expect(component.template).toEqual(mockTemplate);
    expect(component.versions).toEqual(mockVersionList.versions);
  });

  it('should handle load error', fakeAsync(() => {
    jest.clearAllMocks();
    (templateService.getTemplate as jest.Mock).mockReturnValue(
      throwError(() => new Error('Load failed'))
    );
    (templateService.getTemplateVersions as jest.Mock).mockReturnValue(
      throwError(() => new Error('Load failed'))
    );

    const errorFixture = TestBed.createComponent(TemplateDetailComponent);
    const errorComponent = errorFixture.componentInstance;
    (errorComponent as any).snackBar = snackBar;
    errorFixture.detectChanges();
    tick();

    expect(snackBar.open).toHaveBeenCalled();
    expect(errorComponent.loading).toBe(false);
  }));

  it('should create new version', fakeAsync(() => {
    fixture.detectChanges();
    tick(); // Let initial load complete so component.template is set

    component.newVersionForm.patchValue({
      template_content: 'New version content',
      change_notes: 'Improved performance',
    });

    (templateService.createTemplateVersion as jest.Mock).mockReturnValue(
      of(mockTemplate)
    );
    (templateService.getTemplate as jest.Mock).mockReturnValue(
      of(mockTemplate)
    );
    (templateService.getTemplateVersions as jest.Mock).mockReturnValue(
      of({ versions: [], total: 0 })
    );

    component.createNewVersion();
    tick();
    fixture.detectChanges();

    expect(templateService.createTemplateVersion).toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith('New version created', 'Close', {
      duration: 3000,
    });
  }));

  it('should activate version with confirmation', () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    (templateService.activateTemplateVersion as jest.Mock).mockReturnValue(
      of(mockTemplate)
    );
    fixture.detectChanges();

    component.activateVersion(1);

    expect(templateService.activateTemplateVersion).toHaveBeenCalledWith(
      'test_template',
      1
    );
  });

  it('should not activate version if user cancels', () => {
    jest.spyOn(window, 'confirm').mockReturnValue(false);
    fixture.detectChanges();

    component.activateVersion(1);

    expect(templateService.activateTemplateVersion).not.toHaveBeenCalled();
  });

  it('should compare versions', () => {
    const mockDiff: TemplateDiffResponse = {
      template_id: 'test_template',
      version_1: 1,
      version_2: 2,
      content_diff: '--- v1\n+++ v2',
      variables_added: [],
      variables_removed: [],
      metadata_changes: {},
    };

    (templateService.compareTemplateVersions as jest.Mock).mockReturnValue(
      of(mockDiff)
    );
    fixture.detectChanges();

    component.selectedVersion1 = 1;
    component.selectedVersion2 = 2;
    component.compareVersions();

    expect(templateService.compareTemplateVersions).toHaveBeenCalledWith(
      'test_template',
      1,
      2
    );
    expect(component.diffResult).toEqual(mockDiff);
  });

  it('should approve template', () => {
    (templateService.approveTemplate as jest.Mock).mockReturnValue(
      of(mockTemplate)
    );
    fixture.detectChanges();

    component.approvalForm.patchValue({ approval_notes: 'Looks good' });
    component.approveTemplate();

    expect(templateService.approveTemplate).toHaveBeenCalledWith(
      'test_template',
      'Looks good'
    );
  });

  it('should reject template with reason', () => {
    jest.spyOn(window, 'prompt').mockReturnValue('Needs improvement');
    (templateService.rejectTemplate as jest.Mock).mockReturnValue(
      of(mockTemplate)
    );
    fixture.detectChanges();

    component.rejectTemplate();

    expect(templateService.rejectTemplate).toHaveBeenCalledWith(
      'test_template',
      'Needs improvement'
    );
  });

  it('should navigate to edit page', () => {
    fixture.detectChanges();

    component.editTemplate();

    expect(router.navigate).toHaveBeenCalledWith([
      '/templates',
      'test_template',
      'edit',
    ]);
  });

  it('should navigate back to library', () => {
    component.backToLibrary();

    expect(router.navigate).toHaveBeenCalledWith(['/templates/library']);
  });

  it('should delete template with confirmation', () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    (templateService.deleteTemplate as jest.Mock).mockReturnValue(
      of({ message: 'Deleted', versions_deleted: 2 })
    );
    fixture.detectChanges();

    component.deleteTemplate();

    expect(templateService.deleteTemplate).toHaveBeenCalledWith(
      'test_template'
    );
    expect(router.navigate).toHaveBeenCalledWith(['/templates/library']);
  });

  it('should check if template can be approved', () => {
    fixture.detectChanges();

    component.template = { ...mockTemplate, deployment_status: 'pending' };
    expect(component.canApprove()).toBe(true);

    component.template = { ...mockTemplate, deployment_status: 'draft' };
    expect(component.canApprove()).toBe(false);
  });

  it('should check if template can be rejected', () => {
    fixture.detectChanges();

    component.template = { ...mockTemplate, deployment_status: 'pending' };
    expect(component.canReject()).toBe(true);

    component.template = { ...mockTemplate, deployment_status: 'approved' };
    expect(component.canReject()).toBe(true);

    component.template = { ...mockTemplate, deployment_status: 'draft' };
    expect(component.canReject()).toBe(false);
  });

  it('should toggle version selection', () => {
    component.toggleVersionSelection(1, 5);
    expect(component.selectedVersion1).toBe(5);

    component.toggleVersionSelection(1, 5);
    expect(component.selectedVersion1).toBeNull();
  });

  it('should check metadata existence', () => {
    component.template = { ...mockTemplate, metadata_json: { key: 'value' } };
    expect(component.hasMetadata()).toBe(true);

    component.template = { ...mockTemplate, metadata_json: {} };
    expect(component.hasMetadata()).toBe(false);
  });
});
