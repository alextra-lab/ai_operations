import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../environments/environment';
import { ChunkingStrategy, PreflightReport } from '../models/preflight.models';
import { PreflightService } from './preflight.service';

describe('PreflightService', () => {
  let service: PreflightService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [PreflightService],
    });
    service = TestBed.inject(PreflightService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('analyzeDocument', () => {
    it('should upload file and return preflight report', (done) => {
      const mockFile = new File(['test content'], 'test.txt', {
        type: 'text/plain',
      });
      const mockReport: PreflightReport = {
        document_name: 'test.txt',
        document_type: 'text/plain',
        document_size_bytes: 100,
        sample_size_tokens: 10,
        structure_signals: {
          heading_density: 0.2,
          table_ratio: 0,
          list_ratio: 0,
          avg_paragraph_length: 50,
          sentence_count: 5,
          token_count: 100,
          has_code_blocks: false,
          has_equations: false,
        },
        strategy_results: [],
        recommendation: {
          strategy: ChunkingStrategy.SENTENCE_PARAGRAPH,
          confidence: 0.85,
          reasoning: ['Test reasoning'],
          alternative_strategies: [],
        },
        analysis_time_ms: 1000,
        created_at: new Date().toISOString(),
      };

      service.analyzeDocument(mockFile, 'default').subscribe((report) => {
        expect(report).toEqual(mockReport);
        done();
      });

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}/chunking/preflight/analyze`
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body instanceof FormData).toBe(true);
      req.flush(mockReport);
    });

    it('should handle analysis errors', (done) => {
      const mockFile = new File(['test'], 'test.txt', { type: 'text/plain' });

      service.analyzeDocument(mockFile, 'default').subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.message).toBeTruthy();
          expect(error.message.length).toBeGreaterThan(0);
          done();
        },
      });

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}/chunking/preflight/analyze`
      );
      req.error(new ProgressEvent('error'), {
        status: 500,
        statusText: 'Server Error',
      });
    });
  });

  describe('getAvailableStrategies', () => {
    it('should return list of strategies', (done) => {
      const mockStrategies = ['recursive', 'fixed_token', 'heading_aware'];

      service.getAvailableStrategies().subscribe((strategies) => {
        expect(strategies.length).toBe(3);
        done();
      });

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}/chunking/strategies`
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockStrategies);
    });
  });

  describe('formatStrategyName', () => {
    it('should format strategy names correctly', () => {
      expect(service.formatStrategyName(ChunkingStrategy.FIXED_TOKEN)).toBe(
        'Fixed Token'
      );
      expect(service.formatStrategyName(ChunkingStrategy.HEADING_AWARE)).toBe(
        'Heading Aware'
      );
      expect(service.formatStrategyName(ChunkingStrategy.RECURSIVE)).toBe(
        'Recursive'
      );
    });
  });
});
