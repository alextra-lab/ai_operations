import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import {
  ConversationMessage,
  ConversationSession,
  ExportService,
  SummaryRequest,
  SummaryResponse,
} from './export.service';

describe('ExportService', () => {
  let service: ExportService;
  let httpMock: HttpTestingController;

  const mockMessage: ConversationMessage = {
    role: 'user',
    content: 'Test message content',
    timestamp: new Date('2025-10-22T10:00:00Z'),
    metadata: { key: 'value' },
  };

  const mockSession: ConversationSession = {
    id: 'test-session-123',
    use_case_id: 'uc-001',
    use_case_name: 'Test Use Case',
    messages: [mockMessage],
    createdAt: new Date('2025-10-22T09:00:00Z'),
    updatedAt: new Date('2025-10-22T10:00:00Z'),
    metadata: { source: 'test' },
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ExportService],
    });

    service = TestBed.inject(ExportService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('exportAsMarkdown', () => {
    it('should export conversation as markdown with header', () => {
      const markdown = service.formatAsMarkdown(mockSession);

      expect(markdown).toContain('# Conversation Export');
      expect(markdown).toContain('**Session ID:** test-session-123');
      expect(markdown).toContain('**Use Case:** Test Use Case');
      expect(markdown).toContain('**Exported:**');
    });

    it('should include all messages in markdown', () => {
      const markdown = service.formatAsMarkdown(mockSession);

      expect(markdown).toContain('## User');
      expect(markdown).toContain('Test message content');
      expect(markdown).toContain('**Timestamp:** 2025-10-22T10:00:00.000Z');
    });

    it('should include message metadata in markdown', () => {
      const markdown = service.formatAsMarkdown(mockSession);

      expect(markdown).toContain('**Metadata:**');
      expect(markdown).toContain('"key": "value"');
    });

    it('should format multiple messages correctly', () => {
      const sessionWithMultiple: ConversationSession = {
        ...mockSession,
        messages: [
          mockMessage,
          {
            role: 'assistant',
            content: 'Response',
            timestamp: new Date('2025-10-22T10:01:00Z'),
          },
        ],
      };

      const markdown = service.formatAsMarkdown(sessionWithMultiple);

      expect(markdown).toContain('## User');
      expect(markdown).toContain('## Assistant');
      expect(markdown.match(/---/g)?.length).toBeGreaterThan(2);
    });
  });

  describe('exportAsJSON', () => {
    it('should export conversation as valid JSON', () => {
      const json = service.exportAsJSON(mockSession);
      const parsed = JSON.parse(json);

      expect(parsed.format_version).toBe('1.0');
      expect(parsed.export_timestamp).toBeDefined();
      expect(parsed.session).toBeDefined();
    });

    it('should include all session data in JSON', () => {
      const json = service.exportAsJSON(mockSession);
      const parsed = JSON.parse(json);

      expect(parsed.session.id).toBe('test-session-123');
      expect(parsed.session.use_case_id).toBe('uc-001');
      expect(parsed.session.use_case_name).toBe('Test Use Case');
      expect(parsed.session.metadata).toEqual({ source: 'test' });
    });

    it('should format messages correctly in JSON', () => {
      const json = service.exportAsJSON(mockSession);
      const parsed = JSON.parse(json);

      expect(parsed.session.messages).toHaveLength(1);
      expect(parsed.session.messages[0].role).toBe('user');
      expect(parsed.session.messages[0].content).toBe('Test message content');
      expect(parsed.session.messages[0].timestamp).toBe(
        '2025-10-22T10:00:00.000Z'
      );
    });

    it('should handle optional fields gracefully', () => {
      const minimalSession: ConversationSession = {
        id: 'minimal',
        messages: [],
        createdAt: new Date('2025-10-22T09:00:00Z'),
      };

      const json = service.exportAsJSON(minimalSession);
      const parsed = JSON.parse(json);

      expect(parsed.session.id).toBe('minimal');
      expect(parsed.session.use_case_id).toBeUndefined();
      expect(parsed.session.messages).toHaveLength(0);
    });
  });

  describe('generateSummary', () => {
    it('should call summary API endpoint', () => {
      const request: SummaryRequest = {
        use_case_id: 'uc-001',
        messages: [mockMessage],
        export_format: 'markdown',
        redaction: { pii: true, secrets: true },
      };

      const mockResponse: SummaryResponse = {
        summary: 'This is a test summary',
        redacted_fields: ['email', 'phone'],
        token_count: 50,
      };

      service.generateSummary(request).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/summaries');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(request);
      req.flush(mockResponse);
    });
  });

  describe('downloadFile', () => {
    it('should create download link and trigger download', () => {
      const content = 'Test content';
      const filename = 'test.txt';
      const mimeType = 'text/plain';

      // Mock createElement to return a mock anchor element
      const mockAnchor = {
        href: '',
        download: '',
        style: { display: '' },
        click: jest.fn(),
      };

      const createElementSpy = jest
        .spyOn(document, 'createElement')
        .mockReturnValue(mockAnchor as any);
      const appendChildSpy = jest
        .spyOn(document.body, 'appendChild')
        .mockImplementation(() => null as any);
      const removeChildSpy = jest
        .spyOn(document.body, 'removeChild')
        .mockImplementation(() => null as any);

      service.downloadFile(content, filename, mimeType);

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(mockAnchor.download).toBe(filename);
      expect(mockAnchor.click).toHaveBeenCalled();
      expect(appendChildSpy).toHaveBeenCalled();
      expect(removeChildSpy).toHaveBeenCalled();
    });
  });

  describe('copyToClipboard', () => {
    it('should copy content to clipboard', async () => {
      const content = 'Test clipboard content';

      // Mock clipboard API
      const clipboardSpy = jest
        .spyOn(navigator.clipboard, 'writeText')
        .mockResolvedValue(undefined);

      await service.copyToClipboard(content);

      expect(clipboardSpy).toHaveBeenCalledWith(content);
    });
  });

  describe('exportAndDownloadMarkdown', () => {
    it('should export and download markdown with default filename', () => {
      const downloadSpy = jest
        .spyOn(service, 'downloadFile')
        .mockImplementation(() => {});

      service.exportAndDownloadMarkdown(mockSession);

      expect(downloadSpy).toHaveBeenCalled();
      const args = downloadSpy.mock.calls[0];
      expect(args[0]).toContain('# Conversation Export');
      expect(args[1]).toMatch(/conversation-\d+\.md/);
      expect(args[2]).toBe('text/markdown');
    });

    it('should use custom filename when provided', () => {
      const downloadSpy = jest
        .spyOn(service, 'downloadFile')
        .mockImplementation(() => {});
      const customFilename = 'my-conversation.md';

      service.exportAndDownloadMarkdown(mockSession, customFilename);

      const args = downloadSpy.mock.calls[0];
      expect(args[1]).toBe(customFilename);
    });
  });

  describe('exportAndDownloadJSON', () => {
    it('should export and download JSON with default filename', () => {
      const downloadSpy = jest
        .spyOn(service, 'downloadFile')
        .mockImplementation(() => {});

      service.exportAndDownloadJSON(mockSession);

      expect(downloadSpy).toHaveBeenCalled();
      const args = downloadSpy.mock.calls[0];
      expect(() => JSON.parse(args[0])).not.toThrow();
      expect(args[1]).toMatch(/conversation-\d+\.json/);
      expect(args[2]).toBe('application/json');
    });

    it('should use custom filename when provided', () => {
      const downloadSpy = jest
        .spyOn(service, 'downloadFile')
        .mockImplementation(() => {});
      const customFilename = 'my-conversation.json';

      service.exportAndDownloadJSON(mockSession, customFilename);

      const args = downloadSpy.mock.calls[0];
      expect(args[1]).toBe(customFilename);
    });
  });

  describe('copyMarkdownToClipboard', () => {
    it('should copy markdown to clipboard', async () => {
      const clipboardSpy = jest
        .spyOn(navigator.clipboard, 'writeText')
        .mockResolvedValue(undefined);

      await service.copyMarkdownToClipboard(mockSession);

      expect(clipboardSpy).toHaveBeenCalled();
      const args = clipboardSpy.mock.calls[0];
      expect(args[0]).toContain('# Conversation Export');
    });
  });

  describe('generateAndDownloadSummary', () => {
    it('should generate summary and download it', async () => {
      const request: SummaryRequest = {
        use_case_id: 'uc-001',
        messages: [mockMessage],
      };

      const mockResponse: SummaryResponse = {
        summary: 'Generated summary content',
      };

      const downloadSpy = jest
        .spyOn(service, 'downloadFile')
        .mockImplementation(() => {});

      const promise = service.generateAndDownloadSummary(request, 'summary.md');

      const req = httpMock.expectOne('/api/v1/summaries');
      req.flush(mockResponse);

      await promise;

      expect(downloadSpy).toHaveBeenCalledWith(
        'Generated summary content',
        'summary.md',
        'text/markdown'
      );
    });
  });
});
