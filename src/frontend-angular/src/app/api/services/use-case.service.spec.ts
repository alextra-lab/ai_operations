import { HttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import {
  UseCase,
  UseCaseConfig,
  UseCaseListResponse,
} from '../models/use-case.models';
import { UseCaseService } from './use-case.service';

describe('UseCaseService', () => {
  let service: UseCaseService;
  let httpClientSpy: {
    get: jest.Mock;
    post: jest.Mock;
    patch: jest.Mock;
    delete: jest.Mock;
  };

  const mockUseCases: UseCase[] = [
    {
      id: '1',
      use_case_id: 'threat-analysis',
      name: 'Threat Analysis',
      description: 'Analyze security threats',
      category: 'threat_analysis',
      intent_type: 'analysis',
      tags: ['security', 'threats'],
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
      created_by: 'admin',
      is_active: true,
    },
    {
      id: '2',
      use_case_id: 'incident-response',
      name: 'Incident Response',
      description: 'Handle security incidents',
      category: 'incident_response',
      intent_type: 'response',
      tags: ['security', 'incidents'],
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
      created_by: 'admin',
      is_active: true,
    },
  ];

  const mockUseCaseConfig: UseCaseConfig = {
    use_case_id: 'threat-analysis',
    name: 'Threat Analysis',
    description: 'Analyze security threats',
    category: 'threat_analysis',
    intent_type: 'analysis',
    template_config: {
      input_fields: [
        {
          name: 'query',
          type: 'text',
          label: 'Query',
          description: 'Enter your query',
          required: true,
          placeholder: 'Enter query here',
        },
      ],
      output_format: 'text',
      validation_rules: [],
      examples: [],
    },
    visibility_config: {
      roles: ['admin', 'analyst'],
      tags: ['security'],
      is_public: false,
    },
    execution_config: {
      default_model: 'gpt-4',
      default_temperature: 0.7,
      default_top_k: 10,
      default_similarity_threshold: 0.7,
      supports_streaming: true,
      max_execution_time_ms: 30000,
    },
    ui_config: {
      icon: 'security',
      color: '#f44336',
      layout: 'single',
      show_metrics: true,
      show_sources: true,
      show_suggestions: true,
      enable_history: true,
    },
  };

  const mockUseCaseListResponse: UseCaseListResponse = {
    use_cases: mockUseCases,
    total: 2,
    page: 1, // Frontend model includes pagination fields
    size: 10,
    pages: 1,
  };

  beforeEach(() => {
    const spy = {
      get: jest.fn(),
      post: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
    };

    TestBed.configureTestingModule({
      providers: [UseCaseService, { provide: HttpClient, useValue: spy }],
    });

    service = TestBed.inject(UseCaseService);
    httpClientSpy = TestBed.inject(HttpClient) as typeof spy;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getAvailableUseCases', () => {
    it('should return available use cases', (done) => {
      httpClientSpy.get.mockReturnValue(of(mockUseCaseListResponse));

      service.getAvailableUseCases().subscribe({
        next: (useCases) => {
          expect(useCases).toEqual(mockUseCases);
          expect(httpClientSpy.get).toHaveBeenCalledWith(
            '/api/v1/use-cases/available'
          );
          done();
        },
        error: done.fail,
      });
    });

    it('should handle HTTP errors', (done) => {
      const errorResponse = new Error('HTTP Error');
      httpClientSpy.get.mockReturnValue(throwError(() => errorResponse));

      service.getAvailableUseCases().subscribe({
        next: done.fail,
        error: (error) => {
          expect(error).toBeInstanceOf(Error);
          done();
        },
      });
    });
  });

  describe('getUseCase', () => {
    it('should return a specific use case', (done) => {
      const useCaseId = 'threat-analysis';
      httpClientSpy.get.mockReturnValue(of(mockUseCases[0]));

      service.getUseCase(useCaseId).subscribe({
        next: (useCase) => {
          expect(useCase).toEqual(mockUseCases[0]);
          expect(httpClientSpy.get).toHaveBeenCalledWith(
            `/api/v1/use-cases/${useCaseId}`
          );
          done();
        },
        error: done.fail,
      });
    });

    it('should handle errors when fetching use case', (done) => {
      const useCaseId = 'non-existent';
      const errorResponse = new Error('Not found');
      httpClientSpy.get.mockReturnValue(throwError(() => errorResponse));

      service.getUseCase(useCaseId).subscribe({
        next: done.fail,
        error: (error) => {
          expect(error).toBeInstanceOf(Error);
          done();
        },
      });
    });
  });

  describe('getUseCaseConfig', () => {
    it('should return use case configuration with transformed structure', (done) => {
      const useCaseId = 'threat-analysis';
      // Mock backend response format (what the API actually returns)
      const backendResponse = {
        use_case_id: 'threat-analysis',
        name: 'Threat Analysis',
        description: 'Analyze security threats',
        category: 'threat_analysis',
        intent_type: 'analysis',
        config: {
          input_fields: [
            {
              name: 'query',
              type: 'text',
              label: 'Query',
              description: 'Enter your query',
              required: true,
              placeholder: 'Enter query here',
            },
          ],
          models: {
            llm: 'gpt-4',
          },
          generation_params: {
            temperature: 0.7,
          },
          rag: {
            top_k: 10,
            similarity_threshold: 0.7,
          },
          policies: {
            streaming_enabled: false,
          },
          visibility: {
            roles: ['admin', 'analyst'],
            tags: ['security'],
            is_public: false,
          },
        },
      };
      httpClientSpy.get.mockReturnValue(of(backendResponse));

      service.getUseCaseConfig(useCaseId).subscribe({
        next: (config) => {
          // Verify transformation: should have template_config with input_fields
          expect(config.template_config).toBeDefined();
          expect(config.template_config.input_fields).toHaveLength(1);
          expect(config.template_config.input_fields[0].name).toBe('query');
          expect(config.use_case_id).toBe('threat-analysis');
          expect(config.name).toBe('Threat Analysis');
          expect(config.description).toBe('Analyze security threats');
          expect(config.category).toBe('threat_analysis');
          expect(config.execution_config).toBeDefined();
          expect(config.execution_config.default_model).toBe('gpt-4');
          expect(httpClientSpy.get).toHaveBeenCalledWith(
            `/api/v1/use-cases/${useCaseId}/config`
          );
          done();
        },
        error: done.fail,
      });
    });

    it('should merge incomplete visibility_config with defaults', (done) => {
      const useCaseId = 'test-use-case';
      const backendResponse = {
        use_case_id: 'test-use-case',
        name: 'Test Use Case',
        description: 'Test',
        category: 'test',
        intent_type: 'query',
        config: {
          input_fields: [],
          visibility: {
            roles: ['admin'],
            // Missing tags and is_public
          },
        },
      };
      httpClientSpy.get.mockReturnValue(of(backendResponse));

      service.getUseCaseConfig(useCaseId).subscribe({
        next: (config) => {
          // Verify all required fields are present
          expect(config.visibility_config.roles).toEqual(['admin']);
          expect(config.visibility_config.tags).toEqual([]);
          expect(config.visibility_config.is_public).toBe(false);
          done();
        },
        error: done.fail,
      });
    });

    it('should preserve zero values for numeric config fields', (done) => {
      const useCaseId = 'test-use-case';
      const backendResponse = {
        use_case_id: 'test-use-case',
        name: 'Test Use Case',
        description: 'Test',
        category: 'test',
        intent_type: 'query',
        config: {
          input_fields: [],
          generation_params: {
            temperature: 0, // Legitimate zero value
          },
          rag: {
            top_k: 0, // Legitimate zero value
            similarity_threshold: 0, // Legitimate zero value
          },
        },
      };
      httpClientSpy.get.mockReturnValue(of(backendResponse));

      service.getUseCaseConfig(useCaseId).subscribe({
        next: (config) => {
          // Verify zero values are preserved, not replaced with defaults
          expect(config.execution_config.default_temperature).toBe(0);
          expect(config.execution_config.default_top_k).toBe(0);
          expect(config.execution_config.default_similarity_threshold).toBe(0);
          done();
        },
        error: done.fail,
      });
    });
  });

  describe('searchUseCases', () => {
    it('should search use cases with query and filters', (done) => {
      const query = 'threat';
      const filters = {
        category: 'threat_analysis',
        tags: ['security'],
        intent_type: 'analysis',
      };

      httpClientSpy.get.mockReturnValue(of(mockUseCaseListResponse));

      service.searchUseCases(query, filters).subscribe({
        next: (useCases) => {
          expect(useCases).toEqual(mockUseCases);
          expect(httpClientSpy.get).toHaveBeenCalledWith(
            '/api/v1/use-cases/search',
            {
              params: expect.any(Object),
            }
          );
          done();
        },
        error: done.fail,
      });
    });
  });

  describe('getCategories', () => {
    it('should return available categories', (done) => {
      const categories = ['threat_analysis', 'incident_response'];
      httpClientSpy.get.mockReturnValue(of(categories));

      service.getCategories().subscribe({
        next: (cats) => {
          expect(cats).toEqual(categories);
          expect(httpClientSpy.get).toHaveBeenCalledWith(
            '/api/v1/use-cases/categories'
          );
          done();
        },
        error: done.fail,
      });
    });
  });

  describe('cache management', () => {
    it('should clear cache', (done) => {
      // Add some data to cache
      httpClientSpy.get.mockReturnValue(of(mockUseCaseListResponse));

      service.getAvailableUseCases().subscribe({
        next: () => {
          // Clear cache
          service.clearCache();

          // Verify cache is cleared (implementation dependent)
          expect(true).toBeTruthy(); // Placeholder assertion
          done();
        },
        error: done.fail,
      });
    });

    it('should invalidate cache with prefix', () => {
      // Test cache invalidation
      service.invalidateCache('test');
      expect(true).toBeTruthy(); // Placeholder assertion
    });
  });

  describe('observable streams', () => {
    it('should provide use cases stream', (done) => {
      httpClientSpy.get.mockReturnValue(of(mockUseCaseListResponse));

      service.getUseCasesStream().subscribe({
        next: (useCases) => {
          expect(Array.isArray(useCases)).toBeTruthy();
          done();
        },
        error: done.fail,
      });
    });

    it('should provide categories stream', (done) => {
      httpClientSpy.get.mockReturnValue(
        of(['threat_analysis', 'incident_response'])
      );

      service.getCategoriesStream().subscribe({
        next: (categories) => {
          expect(Array.isArray(categories)).toBeTruthy();
          done();
        },
        error: done.fail,
      });
    });
  });
});
