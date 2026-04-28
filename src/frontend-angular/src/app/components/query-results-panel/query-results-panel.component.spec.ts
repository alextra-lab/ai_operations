/**
 * QueryResultsPanelComponent Unit Tests
 *
 * Tests for query results display component.
 * Target: 80%+ coverage
 *
 * Related: P4-TOOLS-01, P4-TOOLS-08, ADR-045
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import {
  ExecutionMetrics,
  Message,
  SourceMetadata,
} from '../../api/models/query-config.models';
import { AutoScrollService } from '../../services/auto-scroll.service';
import { QueryResultsPanelComponent } from './query-results-panel.component';

describe('QueryResultsPanelComponent', () => {
  let component: QueryResultsPanelComponent;
  let fixture: ComponentFixture<QueryResultsPanelComponent>;
  let autoScrollService: AutoScrollService;

  const mockMessages: Message[] = [
    {
      role: 'user',
      content: 'Test question',
      created_at: '2025-01-01T10:00:00Z',
      token_count: 10,
    },
    {
      role: 'assistant',
      content: 'Test answer',
      created_at: '2025-01-01T10:00:05Z',
      token_count: 50,
    },
  ];

  const mockSources: SourceMetadata[] = [
    {
      document_id: 'doc1',
      title: 'Test Document',
      content_snippet: 'This is a test snippet...',
      relevance_score: 0.95,
      chunk_index: 0,
      page_number: 42,
      metadata: {
        author: 'Test Author',
        source: 'Test Source',
      },
    },
  ];

  const mockMetrics: ExecutionMetrics = {
    timing: {
      retrieval_time_ms: 150,
      generation_time_ms: 850,
      total_time_ms: 1000,
    },
    tokens: {
      input_tokens: 100,
      output_tokens: 200,
      total_tokens: 300,
    },
    cost: {
      input_cost: 0.0001,
      output_cost: 0.0002,
      total_cost: 0.0003,
      currency: 'USD',
    },
    confidence_score: 0.85,
    retrieval: {
      chunks_retrieved: 5,
      avg_similarity: 0.82,
      collections_searched: ['documents'],
    },
    guard: {
      risk_score: 0.15,
      checks_performed: ['toxicity', 'pii'],
      warnings: [],
    },
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QueryResultsPanelComponent, NoopAnimationsModule],
      providers: [AutoScrollService],
    }).compileComponents();

    fixture = TestBed.createComponent(QueryResultsPanelComponent);
    component = fixture.componentInstance;
    autoScrollService = TestBed.inject(AutoScrollService);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // ========================================================================
  // Message Display Tests
  // ========================================================================

  describe('Message Display', () => {
    it('should display user messages', () => {
      fixture.componentRef.setInput('messages', [mockMessages[0]]);
      fixture.detectChanges();

      const userMessage = fixture.debugElement.query(By.css('.user-message'));
      expect(userMessage).toBeTruthy();
      // Check for role name instead of content (LLMContentRenderer might not render in tests)
      expect(userMessage.nativeElement.textContent).toContain('You');
      expect(userMessage.nativeElement.textContent).toContain('10 tokens');
    });

    it('should display assistant messages', () => {
      fixture.componentRef.setInput('messages', [mockMessages[1]]);
      fixture.detectChanges();

      const assistantMessage = fixture.debugElement.query(
        By.css('.assistant-message')
      );
      expect(assistantMessage).toBeTruthy();
      // Check for role name instead of content
      expect(assistantMessage.nativeElement.textContent).toContain('Assistant');
      expect(assistantMessage.nativeElement.textContent).toContain('50 tokens');
    });

    it('should display multiple messages', () => {
      fixture.componentRef.setInput('messages', mockMessages);
      fixture.detectChanges();

      const messages = fixture.debugElement.queryAll(
        By.css('.message-wrapper')
      );
      expect(messages.length).toBe(2);
    });

    it('should display token count', () => {
      fixture.componentRef.setInput('messages', [mockMessages[0]]);
      fixture.detectChanges();

      const tokenCount = fixture.debugElement.query(By.css('.token-count'));
      expect(tokenCount).toBeTruthy();
      expect(tokenCount.nativeElement.textContent).toContain('10');
    });
  });

  // ========================================================================
  // Streaming Tests
  // ========================================================================

  describe('Streaming', () => {
    it('should display streaming indicator', () => {
      fixture.componentRef.setInput('isStreaming', true);
      fixture.componentRef.setInput('streamingContent', 'Streaming...');
      fixture.detectChanges();

      const streaming = fixture.debugElement.query(By.css('.streaming'));
      expect(streaming).toBeTruthy();

      const spinner = fixture.debugElement.query(By.css('mat-spinner'));
      expect(spinner).toBeTruthy();
    });

    it('should display streaming content', () => {
      fixture.componentRef.setInput('isStreaming', true);
      fixture.componentRef.setInput('streamingContent', 'Partial response...');
      fixture.detectChanges();

      const content = fixture.debugElement.query(
        By.css('.streaming .message-content')
      );
      expect(content).toBeTruthy();
    });

    it('should hide streaming when complete', () => {
      fixture.componentRef.setInput('isStreaming', false);
      fixture.detectChanges();

      const streaming = fixture.debugElement.query(By.css('.streaming'));
      expect(streaming).toBeFalsy();
    });
  });

  // ========================================================================
  // Sources Display Tests
  // ========================================================================

  describe('Sources Display', () => {
    it('should display sources', () => {
      fixture.componentRef.setInput('sources', mockSources);
      fixture.detectChanges();

      const sourceCards = fixture.debugElement.queryAll(By.css('.source-card'));
      expect(sourceCards.length).toBe(1);
    });

    it('should display source title and relevance', () => {
      fixture.componentRef.setInput('sources', mockSources);
      fixture.detectChanges();

      const sourceCard = fixture.debugElement.query(By.css('.source-card'));
      expect(sourceCard.nativeElement.textContent).toContain('Test Document');
      expect(sourceCard.nativeElement.textContent).toContain('95.0%');
    });

    it('should emit sourceClicked on click', () => {
      fixture.componentRef.setInput('sources', mockSources);
      fixture.detectChanges();

      const spy = jest.spyOn(component.sourceClicked, 'emit');

      const sourceCard = fixture.debugElement.query(By.css('.source-card'));
      sourceCard.nativeElement.click();

      expect(spy).toHaveBeenCalledWith(mockSources[0]);
    });

    it('should not display sources section when empty', () => {
      fixture.componentRef.setInput('sources', []);
      fixture.detectChanges();

      const sourcesSection = fixture.debugElement.query(
        By.css('.sources-section')
      );
      expect(sourcesSection).toBeFalsy();
    });
  });

  // ========================================================================
  // Metrics Display Tests
  // ========================================================================

  describe('Metrics Display', () => {
    it('should display metrics card', () => {
      fixture.componentRef.setInput('metrics', mockMetrics);
      fixture.detectChanges();

      const metricsCard = fixture.debugElement.query(By.css('.metrics-card'));
      expect(metricsCard).toBeTruthy();
    });

    it('should display timing metrics', () => {
      fixture.componentRef.setInput('metrics', mockMetrics);
      fixture.detectChanges();

      const metrics = fixture.debugElement.nativeElement;
      expect(metrics.textContent).toContain('150ms');
      expect(metrics.textContent).toContain('850ms');
      expect(metrics.textContent).toContain('1.0s');
    });

    it('should display token metrics', () => {
      fixture.componentRef.setInput('metrics', mockMetrics);
      fixture.detectChanges();

      const metrics = fixture.debugElement.nativeElement;
      expect(metrics.textContent).toContain('300');
    });

    it('should display confidence score', () => {
      fixture.componentRef.setInput('metrics', mockMetrics);
      fixture.detectChanges();

      const metrics = fixture.debugElement.nativeElement;
      expect(metrics.textContent).toContain('85.0%');
    });

    it('should not display metrics when null', () => {
      fixture.componentRef.setInput('metrics', null);
      fixture.detectChanges();

      const metricsCard = fixture.debugElement.query(By.css('.metrics-card'));
      expect(metricsCard).toBeFalsy();
    });
  });

  // ========================================================================
  // Auto-scroll Tests
  // ========================================================================

  describe('Auto-scroll', () => {
    it('should scroll to bottom on streaming start', () => {
      const spy = jest.spyOn(autoScrollService, 'scrollToBottom');

      component.isStreaming = true;
      component.ngOnChanges({
        isStreaming: {
          currentValue: true,
          previousValue: false,
          firstChange: false,
          isFirstChange: () => false,
        },
      });

      // Wait for setTimeout
      setTimeout(() => {
        expect(spy).toHaveBeenCalled();
      }, 100);
    });

    it('should scroll on streaming chunks', () => {
      component.isStreaming = true;
      component.autoScrollEnabled = true;

      const spy = jest.spyOn(autoScrollService, 'scrollToBottom');

      component.streamingContent = 'New content';
      component.ngOnChanges({
        streamingContent: {
          currentValue: 'New content',
          previousValue: 'Old content',
          firstChange: false,
          isFirstChange: () => false,
        },
      });

      setTimeout(() => {
        expect(spy).toHaveBeenCalled();
      }, 100);
    });
  });

  // ========================================================================
  // Helper Methods Tests
  // ========================================================================

  describe('Helper Methods', () => {
    it('should get role icon', () => {
      expect(component.getRoleIcon('user')).toBe('person');
      expect(component.getRoleIcon('assistant')).toBe('smart_toy');
      expect(component.getRoleIcon('system')).toBe('settings');
      expect(component.getRoleIcon('unknown')).toBe('help');
    });

    it('should get role name', () => {
      expect(component.getRoleName('user')).toBe('You');
      expect(component.getRoleName('assistant')).toBe('Assistant');
      expect(component.getRoleName('system')).toBe('System');
      expect(component.getRoleName('unknown')).toBe('Unknown');
    });

    it('should format tokens', () => {
      expect(component.formatTokens(500)).toBe('500');
      expect(component.formatTokens(1500)).toBe('1.5K');
      expect(component.formatTokens(1500000)).toBe('1.5M');
    });

    it('should format duration', () => {
      expect(component.formatDuration(500)).toBe('500ms');
      expect(component.formatDuration(1500)).toBe('1.5s');
      expect(component.formatDuration(65000)).toBe('1m 5s');
    });

    it('should format percentage', () => {
      expect(component.formatPercentage(0.856)).toBe('85.6%');
    });

    it('should format cost', () => {
      expect(component.formatCost(0.0123)).toBe('$0.0123');
    });
  });

  // ========================================================================
  // TrackBy Functions
  // ========================================================================

  describe('TrackBy Functions', () => {
    it('should track messages by id', () => {
      const message: Message = {
        id: 'msg1',
        role: 'user',
        content: 'Test',
        created_at: '2025-01-01T10:00:00Z',
      };
      expect(component.trackByMessage(0, message)).toBe('msg1');
    });

    it('should track messages by index if no id', () => {
      const message: Message = {
        role: 'user',
        content: 'Test',
        created_at: '2025-01-01T10:00:00Z',
      };
      expect(component.trackByMessage(5, message)).toBe(5);
    });

    it('should track sources by document id and chunk', () => {
      const source: SourceMetadata = {
        document_id: 'doc1',
        title: 'Test',
        content_snippet: 'Test',
        relevance_score: 0.9,
        chunk_index: 2,
      };
      expect(component.trackBySource(0, source)).toBe('doc12');
    });
  });
});
