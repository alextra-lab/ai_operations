/**
 * Template Service Unit Tests
 */

import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import {
  TemplateCreate,
  TemplateListResponse,
  TemplateResponse,
  TemplateUpdate,
  TemplateVersionCreate,
} from '../models/template.models';
import { TemplateService } from './template.service';

describe('TemplateService', () => {
  let service: TemplateService;
  let httpMock: HttpTestingController;
  const baseUrl = '/api/v1/templates';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [TemplateService],
    });
    service = TestBed.inject(TemplateService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('listTemplates', () => {
    it('should list templates with default filters', () => {
      const mockResponse: TemplateListResponse = {
        templates: [],
        total_count: 0,
        page: 1,
        page_size: 50,
      };

      service.listTemplates().subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(baseUrl);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should list templates with custom filters', () => {
      const mockResponse: TemplateListResponse = {
        templates: [],
        total_count: 0,
        page: 2,
        page_size: 25,
      };

      service
        .listTemplates({
          page: 2,
          page_size: 25,
          deployment_status: 'approved',
          active_only: true,
        })
        .subscribe((response) => {
          expect(response).toEqual(mockResponse);
        });

      const req = httpMock.expectOne(
        `${baseUrl}?page=2&page_size=25&deployment_status=approved&active_only=true`
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });

  describe('getTemplate', () => {
    it('should get template by ID', () => {
      const mockTemplate: TemplateResponse = {
        id: 'uuid-1',
        template_id: 'test_template',
        prompt_type: 'system',
        template_content: 'Test content',
        variables: ['var1'],
        metadata_json: {},
        version_number: 1,
        is_active_version: true,
        deployment_status: 'draft',
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:00:00Z',
      };

      service.getTemplate('test_template').subscribe((template) => {
        expect(template).toEqual(mockTemplate);
      });

      const req = httpMock.expectOne(`${baseUrl}/test_template`);
      expect(req.request.method).toBe('GET');
      req.flush(mockTemplate);
    });

    it('should get specific version of template', () => {
      const mockTemplate: TemplateResponse = {
        id: 'uuid-1',
        template_id: 'test_template',
        prompt_type: 'system',
        template_content: 'Test content',
        variables: [],
        metadata_json: {},
        version_number: 2,
        is_active_version: false,
        deployment_status: 'draft',
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:00:00Z',
      };

      service.getTemplate('test_template', 2).subscribe((template) => {
        expect(template.version_number).toBe(2);
      });

      const req = httpMock.expectOne(`${baseUrl}/test_template?version=2`);
      expect(req.request.method).toBe('GET');
      req.flush(mockTemplate);
    });
  });

  describe('createTemplate', () => {
    it('should create a new template', () => {
      const newTemplate: TemplateCreate = {
        template_id: 'new_template',
        prompt_type: 'system',
        template_content: 'New template content',
        variables: ['var1', 'var2'],
        metadata_json: { category: 'test' },
        deployment_status: 'draft',
      };

      const mockResponse: TemplateResponse = {
        id: 'uuid-new',
        ...newTemplate,
        version_number: 1,
        is_active_version: true,
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:00:00Z',
      };

      service.createTemplate(newTemplate).subscribe((response) => {
        expect(response.template_id).toBe('new_template');
        expect(response.version_number).toBe(1);
      });

      const req = httpMock.expectOne(baseUrl);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(newTemplate);
      req.flush(mockResponse);
    });
  });

  describe('updateTemplate', () => {
    it('should update an existing template', () => {
      const updates: TemplateUpdate = {
        template_content: 'Updated content',
        deployment_status: 'pending',
      };

      const mockResponse: TemplateResponse = {
        id: 'uuid-1',
        template_id: 'test_template',
        prompt_type: 'system',
        template_content: 'Updated content',
        variables: [],
        metadata_json: {},
        version_number: 1,
        is_active_version: true,
        deployment_status: 'pending',
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:01:00Z',
      };

      service.updateTemplate('test_template', updates).subscribe((response) => {
        expect(response.template_content).toBe('Updated content');
        expect(response.deployment_status).toBe('pending');
      });

      const req = httpMock.expectOne(`${baseUrl}/test_template`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(updates);
      req.flush(mockResponse);
    });
  });

  describe('deleteTemplate', () => {
    it('should delete a template', () => {
      const mockResponse = {
        message: 'Template deleted successfully',
        versions_deleted: 2,
      };

      service.deleteTemplate('test_template').subscribe((response) => {
        expect(response.versions_deleted).toBe(2);
      });

      const req = httpMock.expectOne(`${baseUrl}/test_template`);
      expect(req.request.method).toBe('DELETE');
      req.flush(mockResponse);
    });
  });

  describe('Version Control', () => {
    it('should get template versions', () => {
      const mockResponse = {
        template_id: 'test_template',
        versions: [],
        total_versions: 0,
      };

      service.getTemplateVersions('test_template').subscribe((response) => {
        expect(response.template_id).toBe('test_template');
      });

      const req = httpMock.expectOne(`${baseUrl}/test_template/versions`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should create a new version', () => {
      const versionData: TemplateVersionCreate = {
        template_content: 'Version 2 content',
        variables: ['var1'],
        metadata_json: {},
        change_notes: 'Improved performance',
      };

      const mockResponse: TemplateResponse = {
        id: 'uuid-2',
        template_id: 'test_template',
        prompt_type: 'system',
        template_content: 'Version 2 content',
        variables: ['var1'],
        metadata_json: { change_notes: 'Improved performance' },
        version_number: 2,
        is_active_version: true,
        deployment_status: 'draft',
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:00:00Z',
      };

      service
        .createTemplateVersion('test_template', versionData)
        .subscribe((response) => {
          expect(response.version_number).toBe(2);
        });

      const req = httpMock.expectOne(`${baseUrl}/test_template/versions`);
      expect(req.request.method).toBe('POST');
      req.flush(mockResponse);
    });

    it('should activate a specific version', () => {
      const mockResponse: TemplateResponse = {
        id: 'uuid-1',
        template_id: 'test_template',
        prompt_type: 'system',
        template_content: 'Content',
        variables: [],
        metadata_json: {},
        version_number: 1,
        is_active_version: true,
        deployment_status: 'draft',
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:00:00Z',
      };

      service
        .activateTemplateVersion('test_template', 1)
        .subscribe((response) => {
          expect(response.is_active_version).toBe(true);
        });

      const req = httpMock.expectOne(`${baseUrl}/test_template/activate`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ version_number: 1 });
      req.flush(mockResponse);
    });

    it('should compare two versions', () => {
      const mockDiff = {
        template_id: 'test_template',
        version_1: 1,
        version_2: 2,
        content_diff: '--- v1\n+++ v2\n@@ diff',
        variables_added: ['new_var'],
        variables_removed: ['old_var'],
        metadata_changes: {},
      };

      service
        .compareTemplateVersions('test_template', 1, 2)
        .subscribe((diff) => {
          expect(diff.variables_added).toEqual(['new_var']);
          expect(diff.variables_removed).toEqual(['old_var']);
        });

      const req = httpMock.expectOne(`${baseUrl}/test_template/diff`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ version_1: 1, version_2: 2 });
      req.flush(mockDiff);
    });
  });

  describe('Approval Workflow', () => {
    it('should approve a template', () => {
      const mockResponse: TemplateResponse = {
        id: 'uuid-1',
        template_id: 'test_template',
        prompt_type: 'system',
        template_content: 'Content',
        variables: [],
        metadata_json: { approval_notes: 'Approved' },
        version_number: 1,
        is_active_version: true,
        deployment_status: 'approved',
        approved_at: '2025-10-13T00:00:00Z',
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:00:00Z',
      };

      service
        .approveTemplate('test_template', 'Approved')
        .subscribe((response) => {
          expect(response.deployment_status).toBe('approved');
        });

      const req = httpMock.expectOne(`${baseUrl}/test_template/approve`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ approval_notes: 'Approved' });
      req.flush(mockResponse);
    });

    it('should reject a template', () => {
      const mockResponse: TemplateResponse = {
        id: 'uuid-1',
        template_id: 'test_template',
        prompt_type: 'system',
        template_content: 'Content',
        variables: [],
        metadata_json: { rejection_reason: 'Needs work' },
        version_number: 1,
        is_active_version: true,
        deployment_status: 'draft',
        created_at: '2025-10-13T00:00:00Z',
        updated_at: '2025-10-13T00:00:00Z',
      };

      service
        .rejectTemplate('test_template', 'Needs work')
        .subscribe((response) => {
          expect(response.deployment_status).toBe('draft');
        });

      const req = httpMock.expectOne(`${baseUrl}/test_template/reject`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ rejection_reason: 'Needs work' });
      req.flush(mockResponse);
    });
  });

  describe('Helper Methods', () => {
    it('should return correct status class', () => {
      expect(service.getDeploymentStatusClass('draft')).toContain('gray');
      expect(service.getDeploymentStatusClass('pending')).toContain('yellow');
      expect(service.getDeploymentStatusClass('approved')).toContain('green');
      expect(service.getDeploymentStatusClass('deployed')).toContain('blue');
    });

    it('should return correct status name', () => {
      expect(service.getDeploymentStatusName('draft')).toBe('Draft');
      expect(service.getDeploymentStatusName('pending')).toBe('Pending Review');
      expect(service.getDeploymentStatusName('approved')).toBe('Approved');
      expect(service.getDeploymentStatusName('deployed')).toBe('Deployed');
    });
  });
});
