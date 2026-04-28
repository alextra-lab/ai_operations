import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { catchError, map, retry, tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  QueryError,
  QueryProgressUpdate,
  QueryStatus,
  RAGAnswer,
  RAGQAResponse,
  RAGQuestionRequest,
  RAGSource,
} from '../models/query.models';

@Injectable({
  providedIn: 'root',
})
export class RagService {
  private readonly baseUrl = environment.apiBaseUrl;
  private readonly cache = new Map<
    string,
    { data: any; timestamp: number; ttl: number }
  >();
  private readonly defaultCacheTTL = 600000; // 10 minutes

  // Conversation management
  private readonly conversations = new Map<
    string,
    BehaviorSubject<RAGAnswer[]>
  >();
  private readonly activeConversations = new Set<string>();
  private readonly currentConversationId = new BehaviorSubject<string | null>(
    null
  );

  // Real-time streaming support
  private readonly streamingAnswers = new Map<
    string,
    BehaviorSubject<RAGAnswer>
  >();

  constructor(private http: HttpClient) { }

  // Core RAG Q&A Methods
  askQuestion(request: RAGQuestionRequest): Observable<RAGQAResponse> {
    const cacheKey = this.generateCacheKey('ask', request);
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    const queryId = this.generateQueryId();
    this.startQueryTracking(queryId, 'RAG_QA');

    // Use the orchestrator's /process endpoint
    const processRequest = {
      query: request.question,
      context: {
        rag_mode: true,
        max_context_length: request.max_context_length,
        temperature: request.temperature,
        model_preference: request.model_preference,
        conversation_id: request.conversation_id,
      },
    };

    return this.http.post<any>(`${this.baseUrl}/process`, processRequest).pipe(
      map((orchestratorResponse) =>
        this.transformOrchestratorToRAGResponse(orchestratorResponse, request)
      ),
      tap((response) => {
        this.updateQueryProgress(queryId, 'COMPLETED', 100, 'Answer generated');
        this.cacheData(cacheKey, response);

        // Add to conversation if conversation_id is provided
        if (request.conversation_id) {
          this.addToConversation(request.conversation_id, response.answer);
        }
      }),
      catchError((error) => {
        this.updateQueryProgress(queryId, 'FAILED', 0, 'Q&A failed', error);
        return this.handleRAGError(error, 'RAG Q&A failed');
      }),
      retry(2)
    );
  }

  private transformOrchestratorToRAGResponse(
    orchestratorResponse: any,
    request: RAGQuestionRequest
  ): RAGQAResponse {
    // Transform sources from orchestrator format to RAGSource format
    const sources: RAGSource[] = (orchestratorResponse.sources || []).map(
      (source: any) => ({
        document_id: source.document_id || '',
        title: source.title || 'Untitled',
        content_snippet:
          source.content_snippet || source.snippet || source.content || '',
        relevance_score:
          source.relevance_score ||
          source.similarity_score ||
          source.score ||
          0,
        chunk_index: source.chunk_index,
        metadata: source.metadata || {},
      })
    );

    const answer: RAGAnswer = {
      answer: orchestratorResponse.response || 'No answer available',
      confidence: orchestratorResponse.confidence || 0,
      sources,
      conversation_id: request.conversation_id || '',
      message_id:
        orchestratorResponse.request_id ||
        orchestratorResponse.run_id ||
        this.generateQueryId(),
    };

    return {
      answer,
      processing_time_ms:
        orchestratorResponse.metrics?.model?.processing_time_ms || 0,
      model_used: orchestratorResponse.metrics?.model?.model_id || 'unknown',
      token_usage: {
        input_tokens: orchestratorResponse.metrics?.model?.tokens_in || 0,
        output_tokens: orchestratorResponse.metrics?.model?.tokens_out || 0,
        total_tokens:
          (orchestratorResponse.metrics?.model?.tokens_in || 0) +
          (orchestratorResponse.metrics?.model?.tokens_out || 0),
      },
      context_retrieved: {
        documents_count: sources.length,
        total_chunks:
          orchestratorResponse.metrics?.retrieval?.hits || sources.length,
        context_length_tokens: 0,
      },
    };
  }

  // Streaming Q&A for real-time responses
  askQuestionStreaming(request: RAGQuestionRequest): Observable<RAGAnswer> {
    const queryId = this.generateQueryId();
    this.startQueryTracking(queryId, 'RAG_QA');

    // Initialize streaming answer subject
    const streamingSubject = new BehaviorSubject<RAGAnswer>({
      answer: '',
      confidence: 0,
      sources: [],
      conversation_id: request.conversation_id || '',
      message_id: queryId,
    });
    this.streamingAnswers.set(queryId, streamingSubject);

    // Start streaming request
    this.http
      .post<RAGQAResponse>(`${this.baseUrl}/ask/stream`, request)
      .pipe(
        tap((response) => {
          this.updateQueryProgress(
            queryId,
            'COMPLETED',
            100,
            'Streaming completed'
          );
          this.streamingAnswers.delete(queryId);
        }),
        catchError((error) => {
          this.updateQueryProgress(
            queryId,
            'FAILED',
            0,
            'Streaming failed',
            error
          );
          this.streamingAnswers.delete(queryId);
          return this.handleRAGError(error, 'RAG streaming failed');
        })
      )
      .subscribe();

    return streamingSubject.asObservable();
  }

  // Context Retrieval Methods
  getContext(question: string, maxDocuments = 5): Observable<RAGSource[]> {
    const cacheKey = this.generateCacheKey('context', {
      question,
      maxDocuments,
    });
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    const params = new HttpParams()
      .set('question', question)
      .set('max_documents', maxDocuments.toString());

    return this.http
      .get<RAGSource[]>(`${this.baseUrl}/context`, { params })
      .pipe(
        tap((context) => this.cacheData(cacheKey, context)),
        catchError((error) =>
          this.handleRAGError(error, 'Failed to retrieve context')
        ),
        retry(2)
      );
  }

  // Conversation Management
  startConversation(topic?: string): Observable<string> {
    const conversationId = this.generateConversationId();

    const body = topic ? { topic } : {};

    return this.http
      .post<{ conversation_id: string }>(`${this.baseUrl}/conversations`, body)
      .pipe(
        map((response) => response.conversation_id),
        tap((id) => {
          this.conversations.set(id, new BehaviorSubject<RAGAnswer[]>([]));
          this.activeConversations.add(id);
          this.currentConversationId.next(id);
        }),
        catchError((error) =>
          this.handleRAGError(error, 'Failed to start conversation')
        ),
        retry(2)
      );
  }

  getConversation(conversationId: string): Observable<RAGAnswer[]> {
    const conversation = this.conversations.get(conversationId);
    if (conversation) {
      return conversation.asObservable();
    }

    // Load conversation from server if not in memory
    return this.http
      .get<RAGAnswer[]>(`${this.baseUrl}/conversations/${conversationId}`)
      .pipe(
        tap((answers) => {
          const subject = new BehaviorSubject<RAGAnswer[]>(answers);
          this.conversations.set(conversationId, subject);
        }),
        catchError((error) =>
          this.handleRAGError(error, 'Failed to load conversation')
        ),
        retry(2)
      );
  }

  getConversations(): Observable<
    { id: string; topic?: string; created_at: string; message_count: number }[]
  > {
    const cacheKey = this.generateCacheKey('conversations', 'list');
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http
      .get<
        {
          id: string;
          topic?: string;
          created_at: string;
          message_count: number;
        }[]
      >(`${this.baseUrl}/conversations`)
      .pipe(
        tap((conversations) => this.cacheData(cacheKey, conversations)),
        catchError((error) =>
          this.handleRAGError(error, 'Failed to fetch conversations')
        ),
        retry(2)
      );
  }

  deleteConversation(conversationId: string): Observable<void> {
    return this.http
      .delete<void>(`${this.baseUrl}/conversations/${conversationId}`)
      .pipe(
        tap(() => {
          this.conversations.delete(conversationId);
          this.activeConversations.delete(conversationId);
          if (this.currentConversationId.value === conversationId) {
            this.currentConversationId.next(null);
          }
        }),
        catchError((error) =>
          this.handleRAGError(error, 'Failed to delete conversation')
        ),
        retry(2)
      );
  }

  // Follow-up Questions
  getFollowUpQuestions(
    conversationId: string,
    lastAnswer: RAGAnswer
  ): Observable<string[]> {
    const cacheKey = this.generateCacheKey('followup', {
      conversationId,
      lastAnswer: lastAnswer.message_id,
    });
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    const body = {
      conversation_id: conversationId,
      last_answer: lastAnswer,
    };

    return this.http.post<string[]>(`${this.baseUrl}/followup`, body).pipe(
      tap((questions) => this.cacheData(cacheKey, questions)),
      catchError((error) =>
        this.handleRAGError(error, 'Failed to generate follow-up questions')
      ),
      retry(2)
    );
  }

  // Answer Quality Assessment
  assessAnswerQuality(answer: RAGAnswer): Observable<{
    overall_score: number;
    confidence_score: number;
    relevance_score: number;
    completeness_score: number;
    source_quality_score: number;
    feedback: string[];
    suggestions: string[];
  }> {
    const cacheKey = this.generateCacheKey('assessment', answer.message_id);
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http.post<any>(`${this.baseUrl}/assess`, { answer }).pipe(
      tap((assessment) => this.cacheData(cacheKey, assessment)),
      catchError((error) =>
        this.handleRAGError(error, 'Failed to assess answer quality')
      ),
      retry(2)
    );
  }

  // Source Analysis
  analyzeSources(sources: RAGSource[]): Observable<{
    source_reliability: {
      source: RAGSource;
      reliability_score: number;
      credibility_factors: string[];
    }[];
    conflicting_information: {
      sources: RAGSource[];
      conflict_type: string;
      description: string;
    }[];
    information_gaps: string[];
    recommendations: string[];
  }> {
    const cacheKey = this.generateCacheKey(
      'source_analysis',
      sources.map((s) => s.document_id).join(',')
    );
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http
      .post<any>(`${this.baseUrl}/analyze-sources`, { sources })
      .pipe(
        tap((analysis) => this.cacheData(cacheKey, analysis)),
        catchError((error) =>
          this.handleRAGError(error, 'Failed to analyze sources')
        ),
        retry(2)
      );
  }

  // Current Conversation Management
  getCurrentConversationId(): Observable<string | null> {
    return this.currentConversationId.asObservable();
  }

  setCurrentConversation(conversationId: string | null): void {
    this.currentConversationId.next(conversationId);
  }

  // Answer Enhancement
  enhanceAnswer(
    answer: RAGAnswer,
    enhancementType: 'CLARIFY' | 'EXPAND' | 'SIMPLIFY' | 'FORMAL' | 'CASUAL'
  ): Observable<RAGAnswer> {
    const body = {
      answer,
      enhancement_type: enhancementType,
    };

    return this.http.post<RAGAnswer>(`${this.baseUrl}/enhance`, body).pipe(
      catchError((error) =>
        this.handleRAGError(error, 'Failed to enhance answer')
      ),
      retry(2)
    );
  }

  // Export Conversation
  exportConversation(
    conversationId: string,
    format: 'JSON' | 'PDF' | 'TXT' | 'MD'
  ): Observable<Blob> {
    const params = new HttpParams().set('format', format);

    return this.http
      .get(`${this.baseUrl}/conversations/${conversationId}/export`, {
        params,
        responseType: 'blob',
      })
      .pipe(
        catchError((error) =>
          this.handleRAGError(error, 'Failed to export conversation')
        ),
        retry(2)
      );
  }

  // Utility Methods
  private addToConversation(conversationId: string, answer: RAGAnswer): void {
    const conversation = this.conversations.get(conversationId);
    if (conversation) {
      const currentAnswers = conversation.value;
      conversation.next([...currentAnswers, answer]);
    }
  }

  private generateConversationId(): string {
    return `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateQueryId(): string {
    return `rag_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private startQueryTracking(queryId: string, queryType: string): void {
    const progressUpdate: QueryProgressUpdate = {
      query_id: queryId,
      status: 'PENDING',
      progress_percentage: 0,
      current_step: 'Initializing RAG query...',
    };

    // Simulate progress updates for demo purposes
    this.simulateRAGProgress(queryId);
  }

  private updateQueryProgress(
    queryId: string,
    status: QueryStatus,
    progress: number,
    step: string,
    error?: any
  ): void {
    if (error) {
      console.error('RAG Query error:', error);
    }
  }

  private simulateRAGProgress(queryId: string): void {
    const steps = [
      { progress: 15, step: 'Analyzing question...' },
      { progress: 30, step: 'Retrieving relevant documents...' },
      { progress: 50, step: 'Processing context...' },
      { progress: 70, step: 'Generating answer...' },
      { progress: 85, step: 'Validating sources...' },
      { progress: 95, step: 'Finalizing response...' },
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length) {
        this.updateQueryProgress(
          queryId,
          'PROCESSING',
          steps[currentStep].progress,
          steps[currentStep].step
        );
        currentStep++;
      } else {
        clearInterval(interval);
      }
    }, 800);
  }

  // Cache Management
  private getCachedData(key: string): any | null {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < cached.ttl) {
      return cached.data;
    }
    if (cached) {
      this.cache.delete(key);
    }
    return null;
  }

  private cacheData(
    key: string,
    data: any,
    ttl: number = this.defaultCacheTTL
  ): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
    });
  }

  private generateCacheKey(prefix: string, data: any): string {
    return `rag_${prefix}:${JSON.stringify(data)}`;
  }

  private handleRAGError(error: any, message: string): Observable<never> {
    console.error('RAG Service Error:', error);
    const ragError: QueryError = {
      code: error.status?.toString() || 'RAG_ERROR',
      message: error.message || message,
      timestamp: new Date().toISOString(),
      details: error,
    };
    return throwError(() => ragError);
  }

  // Public cache management
  clearCache(): void {
    this.cache.clear();
  }

  // Conversation cleanup
  cleanupInactiveConversations(): void {
    // Remove conversations that haven't been accessed in the last hour
    const oneHourAgo = Date.now() - 3600000;

    for (const [conversationId, subject] of this.conversations.entries()) {
      if (!this.activeConversations.has(conversationId)) {
        this.conversations.delete(conversationId);
      }
    }
  }
}
