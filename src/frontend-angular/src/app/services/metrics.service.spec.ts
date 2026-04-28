/**
 * MetricsService Unit Tests
 *
 * Tests for metrics calculation, recommendations generation,
 * and repeatability analysis.
 *
 * Related: P4-TOOLS-07
 */

import { TestBed } from '@angular/core/testing';

import {
  ExecutionMetrics,
  QueryConfig,
  SamplingPreset,
} from '../api/models/query-config.models';
import { MetricsService } from './metrics.service';

describe('MetricsService', () => {
  let service: MetricsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [MetricsService],
    });
    service = TestBed.inject(MetricsService);
  });

  afterEach(() => {
    service.clearHistory();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // ========================================================================
  // Execution History Management
  // ========================================================================

  describe('Execution History', () => {
    it('should add execution to history', () => {
      const metrics = createMockMetrics(1000, 500);

      service.addExecution(metrics);

      const history = service.getExecutionHistory();
      expect(history.length).toBe(1);
      expect(history[0]).toEqual(metrics);
    });

    it('should clear history', () => {
      service.addExecution(createMockMetrics(1000, 500));
      service.addExecution(createMockMetrics(1200, 600));

      service.clearHistory();

      const history = service.getExecutionHistory();
      expect(history.length).toBe(0);
      expect(service.getAggregateMetrics()).toBeNull();
    });

    it('should emit history updates via observable', (done) => {
      const metrics = createMockMetrics(1000, 500);

      service.executionHistory$.subscribe((history) => {
        if (history.length > 0) {
          expect(history.length).toBe(1);
          expect(history[0]).toEqual(metrics);
          done();
        }
      });

      service.addExecution(metrics);
    });
  });

  // ========================================================================
  // Aggregate Metrics Calculation
  // ========================================================================

  describe('Aggregate Metrics', () => {
    it('should calculate aggregate metrics from multiple executions', () => {
      // Add 3 executions with different metrics
      service.addExecution(createMockMetrics(1000, 500, 0.01));
      service.addExecution(createMockMetrics(1200, 600, 0.012));
      service.addExecution(createMockMetrics(800, 400, 0.008));

      const aggregates = service.getAggregateMetrics();

      expect(aggregates).toBeTruthy();
      expect(aggregates!.execution_count).toBe(3);
      expect(aggregates!.average_latency_ms).toBe(1000); // (1000+1200+800)/3
      expect(aggregates!.average_tokens).toBe(500); // (500+600+400)/3
      expect(aggregates!.min_latency_ms).toBe(800);
      expect(aggregates!.max_latency_ms).toBe(1200);
    });

    it('should return null when no executions', () => {
      const aggregates = service.getAggregateMetrics();
      expect(aggregates).toBeNull();
    });

    it('should calculate consistency score', () => {
      // Add consistent executions (low variance)
      service.addExecution(createMockMetrics(1000, 500));
      service.addExecution(createMockMetrics(1010, 510));
      service.addExecution(createMockMetrics(990, 490));

      const aggregates = service.getAggregateMetrics();

      expect(aggregates).toBeTruthy();
      expect(aggregates!.consistency_score).toBeGreaterThan(0.8);
    });

    it('should calculate cost projections', () => {
      service.addExecution(createMockMetrics(1000, 500, 0.01));
      service.addExecution(createMockMetrics(1200, 600, 0.012));

      const aggregates = service.getAggregateMetrics();

      expect(aggregates).toBeTruthy();
      expect(aggregates!.average_cost_per_query).toBe(0.011);
      expect(aggregates!.projected_monthly_cost).toBe(0.011 * 30);
    });

    it('should emit aggregate updates via observable', (done) => {
      service.aggregateMetrics$.subscribe((aggregates) => {
        if (aggregates) {
          expect(aggregates.execution_count).toBe(1);
          done();
        }
      });

      service.addExecution(createMockMetrics(1000, 500));
    });
  });

  // ========================================================================
  // Parameter Recommendations
  // ========================================================================

  describe('Recommendations', () => {
    it('should not generate recommendations with < 3 executions', () => {
      service.addExecution(createMockMetrics(1000, 500));
      service.addExecution(createMockMetrics(1100, 550));

      const recommendations = service.getRecommendations();
      expect(recommendations.length).toBe(0);
    });

    it('should recommend reducing top_k for high latency', () => {
      const config: QueryConfig = createMockConfig();

      // Add executions with high latency
      for (let i = 0; i < 5; i++) {
        service.addExecution(createMockMetrics(3500, 500));
      }

      service.generateRecommendationsFor(config);
      const recommendations = service.getRecommendations();

      const topKRec = recommendations.find((r) => r.parameter === 'top_k');
      expect(topKRec).toBeTruthy();
      expect(topKRec!.type).toBe('performance');
      expect(topKRec!.recommended_value).toBeLessThan(config.rag.top_k);
    });

    it('should recommend STRICT preset for low consistency', () => {
      const config: QueryConfig = createMockConfig();

      // Add executions with high variance (low consistency)
      service.addExecution(createMockMetrics(1000, 500));
      service.addExecution(createMockMetrics(3000, 1500));
      service.addExecution(createMockMetrics(500, 200));
      service.addExecution(createMockMetrics(2500, 1200));

      service.generateRecommendationsFor(config);
      const recommendations = service.getRecommendations();

      const presetRec = recommendations.find(
        (r) => r.parameter === 'sampling_preset'
      );
      expect(presetRec).toBeTruthy();
      expect(presetRec!.type).toBe('consistency');
      expect(presetRec!.recommended_value).toBe(SamplingPreset.STRICT);
    });

    it('should recommend reducing max_tokens for high token usage', () => {
      const config: QueryConfig = createMockConfig();

      // Add executions with high token usage
      for (let i = 0; i < 5; i++) {
        service.addExecution(createMockMetrics(1000, 2500));
      }

      service.generateRecommendationsFor(config);
      const recommendations = service.getRecommendations();

      const maxTokensRec = recommendations.find(
        (r) => r.parameter === 'max_tokens'
      );
      expect(maxTokensRec).toBeTruthy();
      expect(maxTokensRec!.type).toBe('cost');
    });

    it('should emit recommendation updates via observable', (done) => {
      const config: QueryConfig = createMockConfig();
      let doneCalled = false;

      service.recommendations$.subscribe((recs) => {
        if (recs.length > 0 && !doneCalled) {
          expect(recs.length).toBeGreaterThan(0);
          doneCalled = true;
          done();
        }
      });

      // Add executions to trigger recommendations
      for (let i = 0; i < 5; i++) {
        service.addExecution(createMockMetrics(3500, 2500, 0.015));
      }
      service.generateRecommendationsFor(config);
    });
  });

  // ========================================================================
  // Repeatability Analysis
  // ========================================================================

  describe('Repeatability Analysis', () => {
    it('should analyze repeatability test results', () => {
      const query = 'test query';
      const config = createMockConfig();
      const executions = [
        createMockMetrics(1000, 500, 0.01),
        createMockMetrics(1100, 520, 0.011),
        createMockMetrics(950, 480, 0.0095),
        createMockMetrics(1050, 510, 0.0105),
        createMockMetrics(980, 490, 0.098),
      ];

      const result = service.analyzeRepeatability(query, config, executions);

      expect(result.iterations).toBe(5);
      expect(result.query).toBe(query);
      expect(result.latency.avg).toBeGreaterThan(0);
      expect(result.latency.std_dev).toBeGreaterThan(0);
      expect(result.tokens.avg).toBeGreaterThan(0);
      expect(result.consistency_score).toBeGreaterThan(0);
      expect(result.consistency_score).toBeLessThanOrEqual(1);
    });

    it('should calculate correct repeatability metrics', () => {
      const executions = [
        createMockMetrics(1000, 500),
        createMockMetrics(1000, 500),
        createMockMetrics(1000, 500),
      ];

      const result = service.analyzeRepeatability(
        'test',
        createMockConfig(),
        executions
      );

      // Perfect consistency should have high score
      expect(result.consistency_score).toBeGreaterThan(0.95);
      expect(result.latency.std_dev).toBe(0);
      expect(result.tokens.std_dev).toBe(0);
    });

    it('should throw error for empty executions', () => {
      expect(() => {
        service.analyzeRepeatability('test', createMockConfig(), []);
      }).toThrow();
    });
  });

  // ========================================================================
  // Export Functions
  // ========================================================================

  describe('Export', () => {
    it('should export metrics as CSV', () => {
      service.addExecution(createMockMetrics(1000, 500, 0.01));
      service.addExecution(createMockMetrics(1200, 600, 0.012));

      const csv = service.exportAsCSV();

      expect(csv).toContain('Metric,Value,Unit');
      expect(csv).toContain('Average Latency');
      expect(csv).toContain('Average Tokens');
      expect(csv).toContain('Consistency Score');
    });

    it('should return empty string when no metrics for CSV', () => {
      const csv = service.exportAsCSV();
      expect(csv).toBe('');
    });

    it('should export metrics as JSON', () => {
      service.addExecution(createMockMetrics(1000, 500, 0.01));
      service.addExecution(createMockMetrics(1200, 600, 0.012));

      const json = service.exportAsJSON();
      const parsed = JSON.parse(json);

      expect(parsed.aggregate_metrics).toBeTruthy();
      expect(parsed.execution_count).toBe(2);
      expect(parsed.execution_history).toBeTruthy();
      expect(parsed.export_timestamp).toBeTruthy();
    });
  });
});

// ============================================================================
// Test Helpers
// ============================================================================

function createMockMetrics(
  latencyMs: number,
  totalTokens: number,
  cost = 0.01
): ExecutionMetrics {
  return {
    timing: {
      total_time_ms: latencyMs,
      retrieval_time_ms: latencyMs * 0.3,
      generation_time_ms: latencyMs * 0.7,
    },
    tokens: {
      input_tokens: Math.floor(totalTokens * 0.4),
      output_tokens: Math.floor(totalTokens * 0.6),
      total_tokens: totalTokens,
    },
    cost: {
      input_cost: cost * 0.4,
      output_cost: cost * 0.6,
      total_cost: cost,
      currency: 'USD',
    },
    confidence_score: 0.85,
  };
}

function createMockConfig(): QueryConfig {
  return {
    llm_model: 'gpt-4o-mini',
    sampling: {
      preset: SamplingPreset.BALANCED,
      temperature: 0.65,
      top_p: 0.95,
      max_tokens: 2048,
    },
    rag: {
      enabled: true,
      vector_collections: ['documents'],
      top_k: 10,
      similarity_threshold: 0.6,
    },
    query_type: 'rag',
  };
}
