import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Capabilities, CapabilitiesService } from './capabilities.service';

describe('CapabilitiesService', () => {
  let service: CapabilitiesService;
  let httpMock: HttpTestingController;

  const mockCapabilities: Capabilities = {
    stateless: true,
    stateful: false,
    history: 'none',
    evidence: 'none',
    crypto: 'none',
    exports: ['md', 'json'],
    edition: 'core',
    features: {
      run_manifests: true,
      preflight_analysis: true,
      test_suites: true,
      exemplar_selection: false,
    },
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [CapabilitiesService],
    });

    service = TestBed.inject(CapabilitiesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('fetchCapabilities', () => {
    it('should fetch capabilities from backend', async () => {
      const promise = service.fetchCapabilities();

      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      expect(req.request.method).toBe('GET');
      req.flush(mockCapabilities);

      await promise;

      const caps = service.getCurrentCapabilities();
      expect(caps).toEqual(mockCapabilities);
    });

    it('should update loading state during fetch', async () => {
      const loadingStates: boolean[] = [];
      service.isLoading().subscribe((loading) => loadingStates.push(loading));

      const promise = service.fetchCapabilities();

      expect(loadingStates).toContain(true);

      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);

      await promise;

      expect(loadingStates[loadingStates.length - 1]).toBe(false);
    });

    it('should handle fetch errors gracefully', async () => {
      const promise = service.fetchCapabilities();

      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.error(new ErrorEvent('Network error'));

      try {
        await promise;
      } catch (error) {
        // Expected to throw
      }

      // Should fallback to safe defaults
      const caps = service.getCurrentCapabilities();
      expect(caps).toBeDefined();
      expect(caps?.stateless).toBe(false);
      expect(caps?.stateful).toBe(true);
    });

    it('should not fetch multiple times concurrently', async () => {
      const promise1 = service.fetchCapabilities();
      const promise2 = service.fetchCapabilities();

      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);

      await Promise.all([promise1, promise2]);

      // Should only make one request
      httpMock.verify();
    });
  });

  describe('getCapabilities', () => {
    it('should return capabilities as observable', (done) => {
      service.getCapabilities().subscribe((caps) => {
        if (caps) {
          expect(caps).toEqual(mockCapabilities);
          done();
        }
      });

      service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
    });

    it('should return null before capabilities are loaded', (done) => {
      service.getCapabilities().subscribe((caps) => {
        expect(caps).toBeNull();
        done();
      });
    });
  });

  describe('getCurrentCapabilities', () => {
    it('should return current capabilities synchronously', async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;

      const caps = service.getCurrentCapabilities();
      expect(caps).toEqual(mockCapabilities);
    });

    it('should return null if not loaded', () => {
      const caps = service.getCurrentCapabilities();
      expect(caps).toBeNull();
    });
  });

  describe('hasCapability', () => {
    beforeEach(async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;
    });

    it('should return true for available boolean capabilities', () => {
      expect(service.hasCapability('stateless')).toBe(true);
      expect(service.hasCapability('stateful')).toBe(false);
    });

    it('should return true for enabled feature flags', () => {
      expect(service.hasCapability('run_manifests')).toBe(true);
      expect(service.hasCapability('preflight_analysis')).toBe(true);
    });

    it('should return false for disabled feature flags', () => {
      expect(service.hasCapability('exemplar_selection')).toBe(false);
    });

    it('should return false for non-existent capabilities', () => {
      expect(service.hasCapability('non_existent')).toBe(false);
    });

    it('should return false if capabilities not loaded', () => {
      const newService = new CapabilitiesService(
        TestBed.inject(HttpClientTestingModule) as any
      );
      expect(newService.hasCapability('stateless')).toBe(false);
    });
  });

  describe('supportsExport', () => {
    beforeEach(async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;
    });

    it('should return true for supported export formats', () => {
      expect(service.supportsExport('md')).toBe(true);
      expect(service.supportsExport('json')).toBe(true);
    });

    it('should return false for unsupported export formats', () => {
      expect(service.supportsExport('pdf')).toBe(false);
      expect(service.supportsExport('xml')).toBe(false);
    });
  });

  describe('isStateless', () => {
    it('should return true when system is stateless', async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;

      expect(service.isStateless()).toBe(true);
    });

    it('should return false when system is stateful', async () => {
      const statefulCaps: Capabilities = {
        ...mockCapabilities,
        stateless: false,
        stateful: true,
      };

      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(statefulCaps);
      await promise;

      expect(service.isStateless()).toBe(false);
    });
  });

  describe('isStateful', () => {
    it('should return false when system is stateless', async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;

      expect(service.isStateful()).toBe(false);
    });
  });

  describe('getHistoryProvider', () => {
    it('should return history provider type', async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;

      expect(service.getHistoryProvider()).toBe('none');
    });

    it('should return "none" if capabilities not loaded', () => {
      expect(service.getHistoryProvider()).toBe('none');
    });
  });

  describe('getEvidenceSink', () => {
    it('should return evidence sink type', async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;

      expect(service.getEvidenceSink()).toBe('none');
    });
  });

  describe('getEdition', () => {
    it('should return system edition', async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;

      expect(service.getEdition()).toBe('core');
    });

    it('should return "core" if capabilities not loaded', () => {
      expect(service.getEdition()).toBe('core');
    });
  });

  describe('isCoreEdition', () => {
    it('should return true for core edition', async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;

      expect(service.isCoreEdition()).toBe(true);
      expect(service.isPlusEdition()).toBe(false);
    });
  });

  describe('isPlusEdition', () => {
    it('should return true for plus edition', async () => {
      const plusCaps: Capabilities = {
        ...mockCapabilities,
        edition: 'plus',
      };

      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(plusCaps);
      await promise;

      expect(service.isPlusEdition()).toBe(true);
      expect(service.isCoreEdition()).toBe(false);
    });
  });

  describe('isFeatureEnabled', () => {
    beforeEach(async () => {
      const promise = service.fetchCapabilities();
      const req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;
    });

    it('should return true for enabled features', () => {
      expect(service.isFeatureEnabled('run_manifests')).toBe(true);
      expect(service.isFeatureEnabled('preflight_analysis')).toBe(true);
    });

    it('should return false for disabled features', () => {
      expect(service.isFeatureEnabled('exemplar_selection')).toBe(false);
    });

    it('should return false for non-existent features', () => {
      expect(service.isFeatureEnabled('non_existent_feature')).toBe(false);
    });
  });

  describe('reloadCapabilities', () => {
    it('should reload capabilities from backend', async () => {
      // Initial load
      let promise = service.fetchCapabilities();
      let req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(mockCapabilities);
      await promise;

      expect(service.getCurrentCapabilities()).toEqual(mockCapabilities);

      // Reload with updated capabilities
      const updatedCaps: Capabilities = {
        ...mockCapabilities,
        stateless: false,
        stateful: true,
      };

      promise = service.reloadCapabilities();
      req = httpMock.expectOne('/api/v1/capabilities/system/simple');
      req.flush(updatedCaps);
      await promise;

      expect(service.getCurrentCapabilities()).toEqual(updatedCaps);
    });
  });
});
