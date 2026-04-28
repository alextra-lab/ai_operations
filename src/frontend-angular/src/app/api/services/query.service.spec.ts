import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../environments/environment';
import { QueryService } from './query.service';

describe('QueryService', () => {
  let service: QueryService;
  let httpMock: HttpTestingController;
  let consoleWarnSpy: jest.SpyInstance;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });
    service = TestBed.inject(QueryService);
    httpMock = TestBed.inject(HttpTestingController);
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
  });

  afterEach(() => {
    httpMock.verify();
    consoleWarnSpy.mockRestore();
  });

  it('search should pass threshold mapped from request', () => {
    const req$ = service.search({
      query: 'test',
      limit: 5,
      threshold: 0.7,
    } as any);

    req$.subscribe();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/query/search`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(
      expect.objectContaining({ query: 'test', limit: 5, threshold: 0.7 })
    );
    req.flush({
      results: [],
      total_count: 0,
      query_id: 'q',
      processing_time_ms: 1,
    });
  });

  describe('ADR-030 deprecated methods', () => {
    it('saveQueryToHistory should log deprecation warning', (done) => {
      service.saveQueryToHistory({ query_text: 'test' }).subscribe({
        next: (result) => {
          expect(result).toBeDefined();
          expect(consoleWarnSpy).toHaveBeenCalledWith(
            expect.stringContaining('saveQueryToHistory is deprecated')
          );
          done();
        },
        error: done.fail,
      });

      // Flush successful response (no retries)
      const req = httpMock.expectOne(`${environment.apiBaseUrl}/query-history`);
      req.flush({ id: 'test', query_text: 'test' });
    });

    it('forkQuery should log deprecation warning', (done) => {
      service.forkQuery('test-id', {}).subscribe({
        next: (result) => {
          expect(result).toBeDefined();
          expect(consoleWarnSpy).toHaveBeenCalledWith(
            expect.stringContaining('forkQuery is deprecated')
          );
          done();
        },
        error: done.fail,
      });

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}/query-history/fork`
      );
      req.flush({ id: 'forked', parent_query_id: 'test-id' });
    });

    it('updateQuery should log deprecation warning', (done) => {
      service.updateQuery('test-id', {}).subscribe({
        next: (result) => {
          expect(result).toBeDefined();
          expect(consoleWarnSpy).toHaveBeenCalledWith(
            expect.stringContaining('updateQuery is deprecated')
          );
          done();
        },
        error: done.fail,
      });

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}/query-history/test-id`
      );
      req.flush({ id: 'test-id', query_text: 'updated' });
    });

    it('deleteQuery should log deprecation warning', (done) => {
      service.deleteQuery('test-id').subscribe({
        next: () => {
          expect(consoleWarnSpy).toHaveBeenCalledWith(
            expect.stringContaining('deleteQuery is deprecated')
          );
          done();
        },
        error: done.fail,
      });

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}/query-history/test-id`
      );
      req.flush(null);
    });
  });
});
