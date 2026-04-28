import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ChunkingStrategy } from '../api/models/preflight.models';
import { CorpusService } from './corpus.service';

describe('CorpusService', () => {
  let service: CorpusService;
  let httpMock: HttpTestingController;

  const mockPreflightReport = {
    document_name: 'test.pdf',
    document_type: 'application/pdf',
    document_size_bytes: 1024,
    sample_size_tokens: 500,
    structure_signals: {
      heading_density: 0.15,
      table_ratio: 0.05,
      list_ratio: 0.1,
      avg_paragraph_length: 150,
      sentence_count: 50,
      token_count: 500,
      has_code_blocks: false,
      has_equations: false,
    },
    strategy_results: [
      {
        strategy: ChunkingStrategy.FIXED_TOKEN,
        chunk_count: 10,
        avg_chunk_size: 256,
        std_chunk_size: 20,
        processing_time_ms: 100,
        score: 0.85,
        rank: 1,
      },
    ],
    recommendation: {
      strategy: ChunkingStrategy.FIXED_TOKEN,
      confidence: 0.9,
      reasoning: ['Document has consistent structure', 'Low table density'],
      alternative_strategies: [ChunkingStrategy.SLIDING_TOKEN],
    },
    analysis_time_ms: 150,
    created_at: '2025-10-26T00:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [CorpusService],
    });
    service = TestBed.inject(CorpusService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('runPreflight', () => {
    it('should send preflight request with file', () => {
      const file = new File(['test content'], 'test.pdf', {
        type: 'application/pdf',
      });
      const request = {
        file,
        collection_id: 'collection-123',
      };

      service.runPreflight(request).subscribe((report) => {
        expect(report).toEqual(mockPreflightReport);
      });

      const req = httpMock.expectOne(
        (req) =>
          req.url.includes('/api/v1/corpus/preflight') && req.method === 'POST'
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body instanceof FormData).toBe(true);
      req.flush(mockPreflightReport);
    });

    it('should send preflight request with document_id', () => {
      const request = {
        document_id: 'doc-123',
        collection_id: 'collection-123',
        run_retrieval_metrics: true,
      };

      service.runPreflight(request).subscribe((report) => {
        expect(report).toEqual(mockPreflightReport);
      });

      const req = httpMock.expectOne(
        (req) =>
          req.url.includes('/api/v1/corpus/preflight') && req.method === 'POST'
      );
      expect(req.request.method).toBe('POST');
      req.flush(mockPreflightReport);
    });

    it('should include test_suite_id if provided', () => {
      const file = new File(['test content'], 'test.pdf', {
        type: 'application/pdf',
      });
      const request = {
        file,
        collection_id: 'collection-123',
        test_suite_id: 'suite-123',
      };

      service.runPreflight(request).subscribe();

      const req = httpMock.expectOne(
        (req) =>
          req.url.includes('/api/v1/corpus/preflight') && req.method === 'POST'
      );
      req.flush(mockPreflightReport);
    });
  });

  describe('getPreflightReport', () => {
    it('should fetch preflight report by ID', () => {
      const reportId = 'report-123';

      service.getPreflightReport(reportId).subscribe((report) => {
        expect(report).toEqual(mockPreflightReport);
      });

      const req = httpMock.expectOne(
        `${service['apiUrl']}/preflight/${reportId}`
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockPreflightReport);
    });
  });

  describe('applyChunkingConfig', () => {
    it('should apply chunking configuration', () => {
      const documentId = 'doc-123';
      const collectionId = 'collection-123';
      const config = {
        strategy: ChunkingStrategy.FIXED_TOKEN,
        chunk_size: 512,
        overlap: 50,
      };

      const mockResponse = {
        document_id: documentId,
        chunks_created: 15,
        strategy: ChunkingStrategy.FIXED_TOKEN,
      };

      service
        .applyChunkingConfig(documentId, collectionId, config)
        .subscribe((response) => {
          expect(response).toEqual(mockResponse);
        });

      const req = httpMock.expectOne(
        `${service['apiUrl']}/documents/${documentId}/chunk`
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        collection_id: collectionId,
        ...config,
      });
      req.flush(mockResponse);
    });
  });

  describe('getAvailableStrategies', () => {
    it('should return all available chunking strategies', () => {
      const strategies = service.getAvailableStrategies();

      expect(strategies).toContain(ChunkingStrategy.FIXED_TOKEN);
      expect(strategies).toContain(ChunkingStrategy.SLIDING_TOKEN);
      expect(strategies).toContain(ChunkingStrategy.HEADING_AWARE);
      expect(strategies).toContain(ChunkingStrategy.SENTENCE_PARAGRAPH);
      expect(strategies).toContain(ChunkingStrategy.TABLE_AWARE);
      expect(strategies).toContain(ChunkingStrategy.SEMANTIC_ADAPTIVE);
      expect(strategies).toContain(ChunkingStrategy.PAGE_BLOCK);
      expect(strategies).toContain(ChunkingStrategy.RECURSIVE);
      expect(strategies.length).toBe(8);
    });
  });
});
