import { setupZoneTestEnv } from 'jest-preset-angular/setup-env/zone';

setupZoneTestEnv();

// ============================================================================
// Lucide icon registry for tests
// The app registers icons once in app.config.ts (root injector), which the
// TestBed does not replicate. Without a LUCIDE_ICONS provider, rendering any
// <lucide-icon> throws. Inject the app registry into every testing module.
// ============================================================================
import { TestBed } from '@angular/core/testing';
import { LUCIDE_ICONS } from 'lucide-angular';
import { APP_ICONS } from './app/shared/icons/lucide-icons';
import { SafeLucideIconProvider } from './app/shared/icons/safe-lucide-icon-provider';

const originalConfigureTestingModule =
  TestBed.configureTestingModule.bind(TestBed);
TestBed.configureTestingModule = (
  moduleDef: Parameters<typeof TestBed.configureTestingModule>[0]
) => {
  moduleDef.providers = [
    ...(moduleDef.providers ?? []),
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new SafeLucideIconProvider(APP_ICONS),
    },
  ];
  return originalConfigureTestingModule(moduleDef);
};

// Polyfill ReadableStream for jsdom (required for SSE streaming tests)
import {
  ReadableStream,
  TransformStream,
  WritableStream,
} from 'web-streams-polyfill';

// Make ReadableStream available globally
if (typeof global.ReadableStream === 'undefined') {
  (global as any).ReadableStream = ReadableStream;
  (global as any).WritableStream = WritableStream;
  (global as any).TransformStream = TransformStream;
}

// Also add to window for browser-like environment
if (
  typeof window !== 'undefined' &&
  typeof (window as any).ReadableStream === 'undefined'
) {
  (window as any).ReadableStream = ReadableStream;
  (window as any).WritableStream = WritableStream;
  (window as any).TransformStream = TransformStream;
}

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => void 0,
    removeListener: () => void 0,
    addEventListener: () => void 0,
    removeEventListener: () => void 0,
    dispatchEvent: () => false,
  }),
});

// ============================================================================
// FUNCTIONAL localStorage and sessionStorage mocks
// These actually store and retrieve values, which is required for tests
// that verify localStorage integration (e.g., EnterToExecuteDirective)
// ============================================================================
class MockStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  key(index: number): string | null {
    const keys = Array.from(this.store.keys());
    return keys[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }
}

// Create separate instances for localStorage and sessionStorage
const mockLocalStorage = new MockStorage();
const mockSessionStorage = new MockStorage();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
  writable: true,
});

// Mock console methods to reduce noise
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Mock Buffer for Node.js compatibility
(global as any).Buffer = {
  from: (str: string, encoding?: string) => ({
    toString: (targetEncoding?: string) => {
      if (encoding === 'base64' && targetEncoding === 'binary') {
        return atob(str);
      }
      if (targetEncoding === 'base64') {
        return btoa(str);
      }
      return str;
    },
  }),
};

// Mock HTMLCanvasElement for gauge visualizer
HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
  fillRect: jest.fn(),
  clearRect: jest.fn(),
  getImageData: jest.fn(),
  putImageData: jest.fn(),
  createImageData: jest.fn(),
  setTransform: jest.fn(),
  drawImage: jest.fn(),
  save: jest.fn(),
  fillText: jest.fn(),
  restore: jest.fn(),
  beginPath: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  closePath: jest.fn(),
  stroke: jest.fn(),
  translate: jest.fn(),
  scale: jest.fn(),
  rotate: jest.fn(),
  arc: jest.fn(),
  fill: jest.fn(),
  measureText: jest.fn(() => ({ width: 0 })),
  transform: jest.fn(),
  rect: jest.fn(),
  clip: jest.fn(),
  font: '10px sans-serif',
  fillStyle: '#000',
  strokeStyle: '#000',
  lineWidth: 1,
  lineCap: 'butt',
  lineJoin: 'miter',
  miterLimit: 10,
  shadowOffsetX: 0,
  shadowOffsetY: 0,
  shadowBlur: 0,
  shadowColor: 'transparent',
  globalAlpha: 1,
  globalCompositeOperation: 'source-over',
  canvas: null,
})) as any;

// Mock crypto.randomUUID
Object.defineProperty(global.crypto, 'randomUUID', {
  writable: true,
  value: jest.fn(() => '00000000-0000-0000-0000-000000000000'),
});

// Mock navigator.clipboard
Object.defineProperty(navigator, 'clipboard', {
  writable: true,
  value: {
    writeText: jest.fn(() => Promise.resolve()),
    readText: jest.fn(() => Promise.resolve('')),
  },
});

// Mock URL.createObjectURL and URL.revokeObjectURL
Object.defineProperty(window.URL, 'createObjectURL', {
  writable: true,
  value: jest.fn(() => 'blob:mock-url'),
});

Object.defineProperty(window.URL, 'revokeObjectURL', {
  writable: true,
  value: jest.fn(),
});

// Mock Mermaid library (required for library loader service tests)
if (typeof window !== 'undefined') {
  (window as any).mermaid = {
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
}

// Mock Web Animations API (element.animate) for jsdom
// Angular Material animations use this API which is not available in jsdom
if (!Element.prototype.animate) {
  Element.prototype.animate = jest.fn(() => ({
    play: jest.fn(),
    pause: jest.fn(),
    cancel: jest.fn(),
    finish: jest.fn(),
    reverse: jest.fn(),
    updatePlaybackRate: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
    currentTime: null,
    startTime: null,
    playState: 'idle',
    playbackRate: 1,
    playPending: false,
    ready: Promise.resolve(),
    finished: Promise.resolve(),
    onfinish: null,
    oncancel: null,
    onremove: null,
    effect: null,
    timeline: null,
  })) as any;
}

// ============================================================================
// WebSocket Mock with proper static constants
// jsdom doesn't include WebSocket static constants (CONNECTING, OPEN, etc.)
// ============================================================================
class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  readonly CONNECTING = MockWebSocket.CONNECTING;
  readonly OPEN = MockWebSocket.OPEN;
  readonly CLOSING = MockWebSocket.CLOSING;
  readonly CLOSED = MockWebSocket.CLOSED;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  protocol = '';
  extensions = '';
  bufferedAmount = 0;
  binaryType: BinaryType = 'blob';

  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;

  constructor(url: string, protocols?: string | string[]) {
    this.url = url;
  }

  close(code?: number, reason?: string): void {
    this.readyState = MockWebSocket.CLOSED;
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView): void {}

  addEventListener(
    type: string,
    listener: EventListenerOrEventListenerObject
  ): void {}

  removeEventListener(
    type: string,
    listener: EventListenerOrEventListenerObject
  ): void {}

  dispatchEvent(event: Event): boolean {
    return true;
  }
}

// Only set if not already defined (allows tests to override)
if (typeof (global as any).WebSocket === 'undefined') {
  (global as any).WebSocket = MockWebSocket;
}

// ============================================================================
// Global test cleanup - clear storage between tests
// ============================================================================
beforeEach(() => {
  jest.clearAllMocks();
  jest.clearAllTimers();
  // Clear storage between tests
  mockLocalStorage.clear();
  mockSessionStorage.clear();
});

afterEach(() => {
  jest.clearAllTimers();
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
});
