import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ToolCategory, ToolListItem } from '../models/tool.models';
import { ToolDeveloperService } from './tool-developer.service';

describe('ToolDeveloperService', () => {
  let service: ToolDeveloperService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ToolDeveloperService],
    });
    service = TestBed.inject(ToolDeveloperService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should list available tools', () => {
    const mockTools: ToolListItem[] = [
      {
        id: '123',
        tool_id: 'test-tool',
        name: 'Test Tool',
        category: ToolCategory.DATABASE,
        is_enabled: true,
        is_healthy: true,
        requires_authentication: false,
      },
    ];

    service.listAvailableTools().subscribe((tools) => {
      expect(tools.length).toBe(1);
      expect(tools[0].name).toBe('Test Tool');
    });

    const req = httpMock.expectOne((req) =>
      req.url.includes('/api/v1/tools/available')
    );
    expect(req.request.method).toBe('GET');
    req.flush(mockTools);
  });

  it('should list available tools with category filter', () => {
    service.listAvailableTools('database').subscribe();

    const req = httpMock.expectOne(
      (req) =>
        req.url.includes('/api/v1/tools/available') &&
        req.params.get('category') === 'database'
    );
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('should get tool details', () => {
    const mockTool = {
      id: '123',
      tool_id: 'test-tool',
      name: 'Test Tool',
      category: ToolCategory.DATABASE,
      is_enabled: true,
      is_healthy: true,
      timeout_seconds: 30,
      tool_purpose: 'retrieval',
      service_location: 'retrieval_service',
      mcp_server_type: 'stdio',
      tags: [],
      created_at: '2023-01-01',
      updated_at: '2023-01-01',
    };

    service.getToolDetails('123').subscribe((tool) => {
      expect(tool.name).toBe('Test Tool');
    });

    const req = httpMock.expectOne((req) =>
      req.url.includes('/api/v1/tools/123/details')
    );
    expect(req.request.method).toBe('GET');
    req.flush(mockTool);
  });
});
