/**
 * Prompt Template Editor Component Unit Tests
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { TemplateResponse } from '../../api/models/template.models';
import { TemplateService } from '../../api/services/template.service';
import { PromptTemplateEditorComponent } from './prompt-template-editor.component';

describe('PromptTemplateEditorComponent', () => {
  let component: PromptTemplateEditorComponent;
  let fixture: ComponentFixture<PromptTemplateEditorComponent>;
  let templateService: any;
  let router: any;
  let snackBar: any;
  let activatedRoute: any;

  const mockTemplate: TemplateResponse = {
    id: 'uuid-1',
    template_id: 'test_template',
    prompt_type: 'system',
    template_content: 'Test content with {variable1} and {variable2}',
    variables: ['variable1', 'variable2'],
    metadata_json: { category: 'test', author: 'admin' },
    version_number: 1,
    is_active_version: true,
    deployment_status: 'draft',
    created_at: '2025-10-13T00:00:00Z',
    updated_at: '2025-10-13T00:00:00Z',
  };

  beforeEach(async () => {
    const templateServiceMock = {
      getTemplate: jest.fn(),
      createTemplate: jest.fn(),
      updateTemplate: jest.fn(),
    };
    const routerMock = {
      navigate: jest.fn(),
    };
    const snackBarMock = {
      open: jest.fn(),
    };

    activatedRoute = {
      paramMap: of(new Map()),
      params: of({}),
      queryParams: of({}),
      snapshot: {
        params: {},
        queryParams: {},
        paramMap: {
          get: jest.fn().mockReturnValue(null),
          has: jest.fn().mockReturnValue(false),
          keys: [],
          getAll: jest.fn().mockReturnValue([]),
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

    await TestBed.configureTestingModule({
      imports: [
        PromptTemplateEditorComponent,
        ReactiveFormsModule,
        BrowserAnimationsModule,
      ],
      providers: [
        FormBuilder,
        { provide: TemplateService, useValue: templateServiceMock },
        { provide: Router, useValue: routerMock },
        { provide: ActivatedRoute, useValue: activatedRoute },
        { provide: MatSnackBar, useValue: snackBarMock },
      ],
    }).compileComponents();

    templateService = TestBed.inject(TemplateService);
    router = TestBed.inject(Router);
    snackBar = TestBed.inject(MatSnackBar);

    fixture = TestBed.createComponent(PromptTemplateEditorComponent);
    component = fixture.componentInstance;
    (component as any).snackBar = snackBar;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize in create mode by default', () => {
    fixture.detectChanges();

    expect(component.isEditMode).toBe(false);
    expect(component.templateId == null).toBe(true);
  });

  it('should detect variables from template content', (done) => {
    fixture.detectChanges();

    component.templateForm.patchValue({
      template_content: 'Test {var1} and {var2} with {var3}',
    });

    setTimeout(() => {
      component.detectVariables();
      expect(component.detectedVariables).toEqual(['var1', 'var2', 'var3']);
      done();
    }, 600);
  });

  it('should not detect invalid variable syntax', () => {
    component.templateForm.patchValue({
      template_content: 'Test {123invalid} and {{nested}}',
    });

    component.detectVariables();
    // Regex matches {varname} only; {123invalid} invalid (starts with number)
    // {{nested}} contains inner {nested} so "nested" is detected
    expect(component.detectedVariables).toEqual(['nested']);
  });

  it('should create template successfully', () => {
    (templateService.createTemplate as jest.Mock).mockReturnValue(
      of(mockTemplate)
    );
    fixture.detectChanges();

    component.templateForm.patchValue({
      template_id: 'new_template',
      prompt_type: 'system',
      template_content: 'Content with {var1}',
      deployment_status: 'draft',
    });

    component.detectVariables();
    component.saveTemplate();

    expect(templateService.createTemplate).toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith(
      'Template created successfully',
      'Close',
      expect.any(Object)
    );
    expect(router.navigate).toHaveBeenCalledWith(['/templates/library']);
  });

  it('should not save invalid template', () => {
    fixture.detectChanges();

    component.templateForm.patchValue({
      template_id: '',
      template_content: '',
    });

    component.saveTemplate();

    expect(templateService.createTemplate).not.toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith(
      'Please complete all required fields',
      'Close',
      expect.any(Object)
    );
  });

  it('should generate preview with example values', () => {
    component.templateForm.patchValue({
      template_content: 'Analyze {threat} with {context}',
    });
    component.detectedVariables = ['threat', 'context'];

    const preview = component.getPreviewContent();

    expect(preview).toContain('[EXAMPLE_THREAT]');
    expect(preview).toContain('[EXAMPLE_CONTEXT]');
  });

  it('should build metadata correctly', () => {
    component.metadataForm.patchValue({
      category: 'security',
      author: 'admin',
      tags: 'tag1, tag2, tag3',
    });

    const metadata = (component as any).buildMetadata(
      component.metadataForm.value
    );

    expect(metadata.category).toBe('security');
    expect(metadata.author).toBe('admin');
    expect(metadata.tags).toEqual(['tag1', 'tag2', 'tag3']);
  });

  it('should reset form correctly', () => {
    fixture.detectChanges();

    component.templateForm.patchValue({
      template_id: 'test',
      template_content: 'content',
    });
    component.detectedVariables = ['var1'];

    component.resetForm();

    expect(component.templateForm.get('prompt_type')?.value).toBe('system');
    expect(component.detectedVariables).toEqual([]);
  });

  it('should navigate back on cancel', () => {
    component.cancel();

    expect(router.navigate).toHaveBeenCalledWith(['/templates/library']);
  });

  it('should format dates correctly', () => {
    const date = '2025-10-13T12:30:00Z';
    const formatted = component.formatDate(date);

    expect(formatted).toBeDefined();
    expect(formatted.length).toBeGreaterThan(0);
  });
});
