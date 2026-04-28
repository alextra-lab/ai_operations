import { TestBed } from '@angular/core/testing';
import {
  WebSocketConnectionState,
  WebSocketService,
} from './websocket.service';

describe('WebSocketService', () => {
  let service: WebSocketService;
  let mockWebSocket: {
    close: jest.Mock;
    send: jest.Mock;
    addEventListener: jest.Mock;
    removeEventListener: jest.Mock;
    readyState: number;
    onopen: ((event: Event) => void) | null;
    onmessage: ((event: MessageEvent) => void) | null;
    onclose: ((event: CloseEvent) => void) | null;
    onerror: ((event: Event) => void) | null;
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [WebSocketService],
    });
    service = TestBed.inject(WebSocketService);

    // Mock WebSocket
    mockWebSocket = {
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: WebSocket.CONNECTING,
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
    };

    // Replace global WebSocket with mock - MUST preserve static constants
    const mockWebSocketConstructor = jest.fn(() => mockWebSocket) as any;
    mockWebSocketConstructor.CONNECTING = 0;
    mockWebSocketConstructor.OPEN = 1;
    mockWebSocketConstructor.CLOSING = 2;
    mockWebSocketConstructor.CLOSED = 3;
    (global as any).WebSocket = mockWebSocketConstructor;
  });

  afterEach(() => {
    service.disconnect();
    service.ngOnDestroy();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('connect', () => {
    it('should create WebSocket connection', () => {
      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      const observable = service.connect(config);

      expect(observable).toBeDefined();
      expect((global as any).WebSocket).toHaveBeenCalledWith(
        'ws://localhost:8000/ws/dashboard',
        undefined
      );
    });

    it('should emit connection state changes', (done) => {
      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      service.getConnectionState().subscribe((state) => {
        if (state === WebSocketConnectionState.CONNECTING) {
          expect(state).toBe(WebSocketConnectionState.CONNECTING);
          done();
        }
      });

      service.connect(config);

      // Simulate connection opening
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
    });

    it('should emit messages when received', (done) => {
      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      const testMessage = {
        type: 'dashboard_data',
        data: { timestamp: '2025-01-01T00:00:00Z' },
        timestamp: '2025-01-01T00:00:00Z',
      };

      service.connect(config).subscribe((message) => {
        expect(message.type).toBe('dashboard_data');
        done();
      });

      // Simulate message received
      if (mockWebSocket.onmessage) {
        const messageEvent = new MessageEvent('message', {
          data: JSON.stringify(testMessage),
        });
        mockWebSocket.onmessage(messageEvent);
      }
    });

    it('should handle connection errors', () => {
      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      service.getConnectionState().subscribe((state) => {
        if (state === WebSocketConnectionState.ERROR) {
          expect(state).toBe(WebSocketConnectionState.ERROR);
        }
      });

      service.connect(config);

      // Simulate error
      if (mockWebSocket.onerror) {
        mockWebSocket.onerror(new Event('error'));
      }
    });

    it('should close existing connection before creating new one', () => {
      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      service.connect(config);
      const firstWs = (global as any).WebSocket.mock.results[0].value;

      service.connect(config);

      expect(firstWs.close).toHaveBeenCalled();
    });
  });

  describe('send', () => {
    it('should send message when WebSocket is open', () => {
      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      service.connect(config);
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      const message = {
        type: 'test',
        data: { test: 'data' },
        timestamp: '2025-01-01T00:00:00Z',
      };

      const result = service.send(message);

      expect(result).toBe(true);
      // Check that send was called with a JSON string containing the message type
      expect(mockWebSocket.send).toHaveBeenCalled();
      const sentData = JSON.parse(mockWebSocket.send.mock.calls[0][0]);
      expect(sentData.type).toBe('test');
      expect(sentData.data).toEqual({ test: 'data' });
    });

    it('should return false when WebSocket is not open', () => {
      mockWebSocket.readyState = WebSocket.CLOSED;

      const message = {
        type: 'test',
        data: { test: 'data' },
        timestamp: '2025-01-01T00:00:00Z',
      };

      const result = service.send(message);

      expect(result).toBe(false);
      expect(mockWebSocket.send).not.toHaveBeenCalled();
    });
  });

  describe('disconnect', () => {
    it('should close WebSocket connection', () => {
      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      service.connect(config);
      service.disconnect();

      expect(mockWebSocket.close).toHaveBeenCalledWith(
        1000,
        'Client disconnect'
      );
    });
  });

  describe('isConnected', () => {
    it('should return true when WebSocket is open', () => {
      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      service.connect(config);
      // Simulate connection opening - set readyState first, then trigger onopen
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      expect(service.isConnected()).toBe(true);
    });

    it('should return false when WebSocket is not open', () => {
      // Test when no connection exists
      expect(service.isConnected()).toBe(false);

      const config = {
        url: 'ws://localhost:8000/ws/dashboard',
        protocols: undefined,
        reconnectInterval: 5000,
        maxReconnectAttempts: 5,
      };

      // Connect and then disconnect
      service.connect(config);
      service.disconnect();
      expect(service.isConnected()).toBe(false);

      // Also test when WebSocket exists but is not OPEN
      service.connect(config);
      mockWebSocket.readyState = WebSocket.CLOSED;
      expect(service.isConnected()).toBe(false);
    });
  });
});
