/**
 * System Configuration Service Unit Tests
 */

import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../../../environments/environment';
import { ConfigSection } from '../models/system-config.models';
import { SystemConfigService } from './system-config.service';

describe('SystemConfigService', () => {
  let service: SystemConfigService;
  let httpMock: HttpTestingController;
  const baseUrl = `${environment.apiBaseUrl}/admin/config`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [SystemConfigService],
    });
    service = TestBed.inject(SystemConfigService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getConfig', () => {
    it('should fetch all configuration', () => {
      const mockConfig = {
        corpus: {
          chunk_size: 512,
          chunk_overlap: 50,
          default_embedding_model: 'test-model',
          max_document_size_mb: 50,
          allowed_file_types: ['pdf', 'txt'],
        },
        auth: {
          session_timeout_minutes: 60,
          refresh_token_ttl_days: 30,
          password_policy: {
            min_length: 8,
            require_uppercase: true,
            require_lowercase: true,
            require_numbers: true,
            require_special: false,
          },
        },
        features: {
          multi_collection_search: false,
          export_functionality: true,
          conversation_cache: true,
          telemetry_enabled: true,
        },
        system: {
          log_level: 'INFO' as const,
          max_workers: 4,
          request_timeout_seconds: 30,
          enable_debug_endpoints: false,
        },
      };

      service.getConfig().subscribe((config) => {
        expect(config).toEqual(mockConfig);
      });

      const req = httpMock.expectOne(`${baseUrl}/`);
      expect(req.request.method).toBe('GET');
      req.flush(mockConfig);
    });
  });

  describe('getConfigSection', () => {
    it('should fetch specific section', () => {
      const section: ConfigSection = 'corpus';
      const mockResponse = {
        section: 'corpus',
        config: {
          chunk_size: 512,
          chunk_overlap: 50,
          default_embedding_model: 'test-model',
          max_document_size_mb: 50,
          allowed_file_types: ['pdf', 'txt'],
        },
        updated_at: '2025-10-27T12:00:00Z',
        updated_by: 'admin-id',
        restart_required: true,
      };

      service.getConfigSection(section).subscribe((response) => {
        expect(response.section).toBe('corpus');
        expect(response.restart_required).toBe(true);
      });

      const req = httpMock.expectOne(`${baseUrl}/${section}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });

  describe('updateConfigSection', () => {
    it('should update configuration section', () => {
      const section: ConfigSection = 'corpus';
      const config = {
        chunk_size: 1024,
        chunk_overlap: 100,
        default_embedding_model: 'new-model',
        max_document_size_mb: 100,
        allowed_file_types: ['pdf', 'txt', 'docx'],
      };
      const mockResponse = {
        section: 'corpus',
        config,
        updated_at: '2025-10-27T12:00:00Z',
        updated_by: 'admin-id',
        restart_required: true,
      };

      service.updateConfigSection(section, config).subscribe((response) => {
        expect(response.section).toBe('corpus');
        expect(response.restart_required).toBe(true);
      });

      const req = httpMock.expectOne(`${baseUrl}/${section}`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(config);
      req.flush(mockResponse);
    });
  });

  describe('getConfigSchema', () => {
    it('should fetch schema for section', () => {
      const section: ConfigSection = 'corpus';
      const mockSchema = {
        type: 'object',
        properties: {
          chunk_size: {
            type: 'integer',
            minimum: 128,
            maximum: 2048,
            default: 512,
          },
        },
      };

      service.getConfigSchema(section).subscribe((schema) => {
        expect(schema.type).toBe('object');
        expect(schema.properties['chunk_size']).toBeDefined();
      });

      const req = httpMock.expectOne(`${baseUrl}/schema/${section}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockSchema);
    });
  });

  describe('exportConfig', () => {
    it('should export configuration as YAML', () => {
      const mockResponse = {
        config_yaml: 'corpus:\n  chunk_size: 512\n',
        exported_at: '2025-10-27T12:00:00Z',
      };

      service.exportConfig().subscribe((response) => {
        expect(response.config_yaml).toContain('corpus:');
        expect(response.exported_at).toBeDefined();
      });

      const req = httpMock.expectOne(`${baseUrl}/export`);
      expect(req.request.method).toBe('POST');
      req.flush(mockResponse);
    });
  });

  describe('importConfig', () => {
    it('should import configuration from YAML', () => {
      const request = {
        config_yaml: 'corpus:\n  chunk_size: 512\n',
        validate_only: false,
      };
      const mockResponse = {
        success: true,
        sections_updated: ['corpus', 'auth', 'features', 'system'],
        restart_required: true,
      };

      service.importConfig(request).subscribe((response) => {
        expect(response.success).toBe(true);
        expect(response.sections_updated.length).toBe(4);
        expect(response.restart_required).toBe(true);
      });

      const req = httpMock.expectOne(`${baseUrl}/import`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(request);
      req.flush(mockResponse);
    });
  });

  describe('validateConfigYaml', () => {
    it('should validate YAML without importing', () => {
      const configYaml = 'corpus:\n  chunk_size: 512\n';
      const mockResponse = {
        success: true,
        sections_updated: [],
        restart_required: false,
      };

      service.validateConfigYaml(configYaml).subscribe((response) => {
        expect(response.success).toBe(true);
        expect(response.sections_updated.length).toBe(0);
      });

      const req = httpMock.expectOne(`${baseUrl}/import`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body.validate_only).toBe(true);
      req.flush(mockResponse);
    });
  });
});
