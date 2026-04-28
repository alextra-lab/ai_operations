import { TestBed } from '@angular/core/testing';

import { LibraryLoaderService } from './library-loader.service';

// Mock dynamic imports
jest.mock('prismjs', () => ({ default: { highlightAll: jest.fn() } }), {
  virtual: true,
});
jest.mock('katex', () => ({ default: { render: jest.fn() } }), {
  virtual: true,
});
jest.mock(
  'katex/dist/contrib/auto-render.mjs',
  () => ({ default: jest.fn() }),
  { virtual: true }
);
// Mock Mermaid library
const mockMermaid = {
  initialize: jest.fn((config?: any) => Promise.resolve()),
  render: jest.fn((id: string, definition: string) =>
    Promise.resolve({ svg: '<svg>mock</svg>' })
  ),
  parse: jest.fn((definition: string) => ({ errors: [] })),
  mermaidAPI: {
    render: jest.fn(),
    parse: jest.fn(),
  },
  version: '11.12.0',
};

jest.mock(
  'mermaid',
  () => ({
    default: mockMermaid,
    __esModule: true,
  }),
  { virtual: true }
);
jest.mock('chart.js/auto', () => ({ Chart: jest.fn() }), { virtual: true });

describe('LibraryLoaderService', () => {
  let service: LibraryLoaderService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(LibraryLoaderService);

    // Clear any globally loaded libraries
    delete (window as any).Prism;
    delete (window as any).katex;
    delete (window as any).mermaid;
    delete (window as any).Chart;

    // Mock internal loaders so no test runs dynamic import/network
    jest
      .spyOn(service as any, 'loadPrismInternal')
      .mockResolvedValue(undefined);
    jest
      .spyOn(service as any, 'loadKaTeXInternal')
      .mockResolvedValue(undefined);

    // Reset internal loading state
    (service as any).loadingPromises.clear();
    (service as any).loadedLibraries.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('isLoaded', () => {
    it('should return false for unloaded libraries', () => {
      expect(service.isLoaded('prism')).toBe(false);
      expect(service.isLoaded('katex')).toBe(false);
      expect(service.isLoaded('mermaid')).toBe(false);
      expect(service.isLoaded('chartjs')).toBe(false);
    });
  });

  describe('loadPrism', () => {
    it('should load Prism.js', async () => {
      await service.loadPrism(['typescript']);

      expect(service.isLoaded('prism')).toBe(true);
    });

    it('should load Prism.js only once on multiple calls', async () => {
      const spy = jest.spyOn(console, 'warn');

      await Promise.all([
        service.loadPrism(['typescript']),
        service.loadPrism(['typescript']),
        service.loadPrism(['typescript']),
      ]);

      expect(service.isLoaded('prism')).toBe(true);
      // Should not have warnings about multiple loads
      expect(spy).not.toHaveBeenCalled();

      spy.mockRestore();
    });

    it('should return immediately if already loaded', async () => {
      await service.loadPrism(['typescript']);
      const startTime = Date.now();
      await service.loadPrism(['typescript']);
      const endTime = Date.now();

      // Should be near-instant (<10ms) if already loaded
      expect(endTime - startTime).toBeLessThan(10);
    });
  });

  describe('loadKaTeX', () => {
    it('should load KaTeX', async () => {
      await service.loadKaTeX();
      expect(service.isLoaded('katex')).toBe(true);
    });

    it('should load KaTeX only once on multiple calls', async () => {
      await Promise.all([
        service.loadKaTeX(),
        service.loadKaTeX(),
        service.loadKaTeX(),
      ]);

      expect(service.isLoaded('katex')).toBe(true);
    });
  });

  describe('loadMermaid', () => {
    it('should load Mermaid', async () => {
      await service.loadMermaid();
      expect(service.isLoaded('mermaid')).toBe(true);
    });

    it('should load Mermaid only once on multiple calls', async () => {
      await Promise.all([
        service.loadMermaid(),
        service.loadMermaid(),
        service.loadMermaid(),
      ]);

      expect(service.isLoaded('mermaid')).toBe(true);
    });

    it('should initialize Mermaid with default config', async () => {
      await service.loadMermaid();
      expect((window as any).mermaid).toBeDefined();
    });
  });

  describe('getLoadedLibraries', () => {
    it('should return empty array initially', () => {
      const loaded = service.getLoadedLibraries();
      expect(loaded).toEqual([]);
    });

    it('should return loaded libraries', async () => {
      await service.loadPrism(['typescript']);
      await service.loadKaTeX();

      const loaded = service.getLoadedLibraries();
      expect(loaded).toContain('prism');
      expect(loaded).toContain('katex');
      expect(loaded.length).toBe(2);
    });
  });

  describe('loadChartJS', () => {
    it('should load Chart.js', async () => {
      await service.loadChartJS();
      expect(service.isLoaded('chartjs')).toBe(true);
    });

    it('should load Chart.js only once on multiple calls', async () => {
      await Promise.all([
        service.loadChartJS(),
        service.loadChartJS(),
        service.loadChartJS(),
      ]);

      expect(service.isLoaded('chartjs')).toBe(true);
    });

    it('should return immediately if already loaded', async () => {
      await service.loadChartJS();
      const startTime = Date.now();
      await service.loadChartJS();
      const endTime = Date.now();

      // Should be near-instant (<10ms) if already loaded
      expect(endTime - startTime).toBeLessThan(10);
    });

    it('should set Chart on window object', async () => {
      await service.loadChartJS();
      expect((window as any).Chart).toBeDefined();
    });
  });

  describe('isLoading', () => {
    it('should return false when no libraries are loading', () => {
      expect(service.isLoading()).toBe(false);
    });

    it('should return true while library is loading', async () => {
      const loadPromise = service.loadPrism(['typescript']);
      expect(service.isLoading()).toBe(true);
      await loadPromise;
      expect(service.isLoading()).toBe(false);
    });
  });
});
