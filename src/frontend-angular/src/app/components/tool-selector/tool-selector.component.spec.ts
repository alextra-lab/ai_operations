import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { ToolCategory, ToolListItem } from '../../api/models/tool.models';
import { ToolDeveloperService } from '../../api/services/tool-developer.service';
import { ToolSelectorComponent } from './tool-selector.component';

describe('ToolSelectorComponent', () => {
  let component: ToolSelectorComponent;
  let fixture: ComponentFixture<ToolSelectorComponent>;
  let toolServiceSpy: {
    listAvailableTools: jest.Mock;
  };

  const mockTools: ToolListItem[] = [
    {
      id: '1',
      tool_id: 'tool-1',
      name: 'Database Tool',
      category: ToolCategory.DATABASE,
      is_enabled: true,
      is_healthy: true,
      requires_authentication: false,
      description: 'A database tool',
    },
    {
      id: '2',
      tool_id: 'tool-2',
      name: 'Web Scraper',
      category: ToolCategory.WEB_SCRAPING,
      is_enabled: true,
      is_healthy: false,
      requires_authentication: true,
      description: 'A scraper tool',
    },
  ];

  beforeEach(async () => {
    toolServiceSpy = {
      listAvailableTools: jest.fn().mockReturnValue(of(mockTools)),
    };

    await TestBed.configureTestingModule({
      imports: [ToolSelectorComponent, NoopAnimationsModule],
      providers: [{ provide: ToolDeveloperService, useValue: toolServiceSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load tools on init', () => {
    expect(toolServiceSpy.listAvailableTools).toHaveBeenCalled();
    expect(component.tools.length).toBe(2);
    expect(component.filteredTools.length).toBe(2);
    expect(component.availableCategories).toEqual(
      [ToolCategory.DATABASE, ToolCategory.WEB_SCRAPING].sort()
    );
  });

  it('should filter tools by search term', () => {
    component.searchTerm = 'database';
    component.filterTools();
    expect(component.filteredTools.length).toBe(1);
    expect(component.filteredTools[0].name).toBe('Database Tool');
  });

  it('should filter tools by category', () => {
    component.selectedCategory = ToolCategory.WEB_SCRAPING;
    component.filterTools();
    expect(component.filteredTools.length).toBe(1);
    expect(component.filteredTools[0].name).toBe('Web Scraper');
  });

  it('should toggle tool selection', () => {
    // Select
    component.toggleTool('1');
    expect(component.selectedToolIds).toContain('1');

    // Deselect
    component.toggleTool('1');
    expect(component.selectedToolIds).not.toContain('1');
  });

  it('should emit selection change on toggle', () => {
    jest.spyOn(component.selectionChange, 'emit');
    component.toggleTool('1');
    expect(component.selectionChange.emit).toHaveBeenCalledWith(['1']);
  });

  it('should handle load error', () => {
    toolServiceSpy.listAvailableTools.mockReturnValue(
      throwError(() => new Error('Error'))
    );
    component.loadTools();
    expect(component.error).toBe('Failed to load available tools');
    expect(component.isLoading).toBe(false);
  });

  it('should check if tool is selected', () => {
    component.selectedToolIds = ['1', '2'];
    expect(component.isSelected('1')).toBe(true);
    expect(component.isSelected('3')).toBe(false);
  });

  it('should filter tools by both search term and category', () => {
    component.searchTerm = 'database';
    component.selectedCategory = ToolCategory.DATABASE;
    component.filterTools();
    expect(component.filteredTools.length).toBe(1);
    expect(component.filteredTools[0].name).toBe('Database Tool');
  });

  it('should return empty array when no tools match filters', () => {
    component.searchTerm = 'nonexistent';
    component.filterTools();
    expect(component.filteredTools.length).toBe(0);
  });

  it('should handle empty description in search', () => {
    const toolWithoutDesc: ToolListItem = {
      id: '3',
      tool_id: 'tool-3',
      name: 'No Desc Tool',
      category: ToolCategory.REASONING,
      is_enabled: true,
      is_healthy: true,
      requires_authentication: false,
    };
    component.tools = [...mockTools, toolWithoutDesc];
    component.searchTerm = 'no desc';
    component.filterTools();
    expect(component.filteredTools.length).toBe(1);
    expect(component.filteredTools[0].name).toBe('No Desc Tool');
  });

  it('should get category icon for all categories', () => {
    expect(component.getCategoryIcon(ToolCategory.DATABASE)).toBe('dns');
    expect(component.getCategoryIcon(ToolCategory.VECTOR_DB)).toBe('storage');
    expect(component.getCategoryIcon(ToolCategory.WEB_SCRAPING)).toBe('public');
    expect(component.getCategoryIcon(ToolCategory.REASONING)).toBe(
      'psychology'
    );
    expect(component.getCategoryIcon(ToolCategory.DOCUMENTATION)).toBe(
      'description'
    );
    expect(component.getCategoryIcon(ToolCategory.CODE_ANALYSIS)).toBe('code');
    expect(component.getCategoryIcon(ToolCategory.THREAT_INTEL)).toBe(
      'security'
    );
    expect(component.getCategoryIcon(ToolCategory.CUSTOM)).toBe('extension');
    expect(component.getCategoryIcon('unknown')).toBe('build');
  });

  it('should format category labels correctly', () => {
    expect(component.getCategoryLabel('database')).toBe('Database');
    expect(component.getCategoryLabel('web_scraping')).toBe('Web Scraping');
    expect(component.getCategoryLabel('threat_intel')).toBe('Threat Intel');
  });

  it('should initialize with selectedToolIds input', () => {
    component.selectedToolIds = ['1'];
    component.ngOnInit();
    expect(component.selectedToolIds).toEqual(['1']);
  });

  it('should extract categories correctly', () => {
    component.tools = mockTools;
    component.extractCategories();
    expect(component.availableCategories).toContain(ToolCategory.DATABASE);
    expect(component.availableCategories).toContain(ToolCategory.WEB_SCRAPING);
  });

  it('should handle case-insensitive search', () => {
    component.searchTerm = 'DATABASE';
    component.filterTools();
    expect(component.filteredTools.length).toBe(1);
    expect(component.filteredTools[0].name).toBe('Database Tool');
  });
});
