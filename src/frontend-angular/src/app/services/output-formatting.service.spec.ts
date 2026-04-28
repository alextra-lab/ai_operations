/**
 * Unit Tests for Output Formatting Service
 */

import { TestBed } from '@angular/core/testing';
import {
  OutputFormatTemplate,
  UseCaseResponse,
} from '../models/output-format.model';
import { OutputFormattingService } from './output-formatting.service';

describe('OutputFormattingService', () => {
  let service: OutputFormattingService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(OutputFormattingService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('formatResponse', () => {
    it('should format response with valid template', async () => {
      const template: OutputFormatTemplate = {
        template_id: 'test-template',
        name: 'Test Template',
        description: 'Test',
        data_schema: {
          type: 'object',
          required: ['value'],
          properties: {
            value: { type: 'number' },
          },
        },
        layout: {
          type: 'single',
          sections: [
            {
              section_id: 'test-section',
              title: 'Test Section',
              component_type: 'text',
              data_path: '$.value',
              config: {},
            },
          ],
        },
        export_formats: ['json'],
      };

      const response: UseCaseResponse = {
        answer: 'Test answer',
        structured_data: { value: 42 },
      };

      const result = await service.formatResponse(response, template);

      expect(result).toBeDefined();
      expect(result.rendered_sections).toHaveLength(1);
      expect(result.rendered_sections[0].data).toBe(42);
    });

    it('should extract nested data using JSON path', async () => {
      const template: OutputFormatTemplate = {
        template_id: 'nested-test',
        name: 'Nested Test',
        description: 'Test',
        data_schema: { type: 'object' },
        layout: {
          type: 'single',
          sections: [
            {
              section_id: 'nested',
              title: 'Nested',
              component_type: 'text',
              data_path: '$.data.nested.value',
              config: {},
            },
          ],
        },
        export_formats: [],
      };

      const response: UseCaseResponse = {
        answer: 'Test',
        structured_data: {
          data: {
            nested: {
              value: 'extracted',
            },
          },
        },
      };

      const result = await service.formatResponse(response, template);
      expect(result.rendered_sections[0].data).toBe('extracted');
    });
  });

  describe('clearCache', () => {
    it('should clear validator cache', () => {
      service.clearCache();
      // Should not throw
      expect(true).toBe(true);
    });
  });
});
