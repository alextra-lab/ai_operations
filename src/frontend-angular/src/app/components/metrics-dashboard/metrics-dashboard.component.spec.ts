/**
 * MetricsDashboardComponent Unit Tests
 *
 * Tests for metrics dashboard UI component including display,
 * interactions, and repeatability testing.
 *
 * Related: P4-TOOLS-07
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import {
  ExecutionMetrics,
  QueryConfig,
  SamplingPreset,
} from '../../api/models/query-config.models';
import {
  AggregateMetrics,
  ParameterRecommendation,
} from '../../models/metrics.models';
import { MetricsService } from '../../services/metrics.service';
import { MetricsDashboardComponent } from './metrics-dashboard.component';

describe('MetricsDashboardComponent', () => {
  let component: MetricsDashboardComponent;
  let fixture: ComponentFixture<MetricsDashboardComponent>;
  let metricsService: any;

  const mockAggregateMetrics: AggregateMetrics = {
    execution_count: 5,
    average_latency_ms: 1200,
    min_latency_ms: 1000,
    max_latency_ms: 1500,
    p50_latency_ms: 1200,
    p95_latency_ms: 1450,
    average_tokens: 600,
    total_tokens: 3000,
    average_input_tokens: 240,
    average_output_tokens: 360,
    total_cost: 0.05,
    average_cost_per_query: 0.01,
    projected_monthly_cost: 0.3,
    currency: 'USD',
    consistency_score: 0.85,
    latency_std_dev: 150,
    token_std_dev: 50,
    success_rate: 1.0,
    error_count: 0,
  };

  const mockRecommendations: ParameterRecommendation[] = [
    {
      type: 'performance',
      parameter: 'top_k',
      current_value: 10,
      recommended_value: 7,
      reason: 'High latency detected',
      impact_description: 'Reduce response time',
      confidence: 0.8,
    },
  ];

  beforeEach(async () => {
    const metricsServiceSpy = {
      clearHistory: jest.fn(),
      exportAsCSV: jest.fn().mockReturnValue('csv data'),
      exportAsJSON: jest.fn().mockReturnValue('json data'),
      downloadFile: jest.fn(),
      analyzeRepeatability: jest.fn().mockResolvedValue({
        totalRuns: 10,
        consistencyScore: 0.85,
        variations: [],
        recommendations: [],
      }),
      generateRecommendationsFor: jest.fn().mockReturnValue([]),
      executionHistory$: of([]),
      aggregateMetrics$: of(null),
      recommendations$: of([]),
    };

    await TestBed.configureTestingModule({
      imports: [MetricsDashboardComponent, NoopAnimationsModule],
      providers: [{ provide: MetricsService, useValue: metricsServiceSpy }],
    }).compileComponents();

    metricsService = TestBed.inject(MetricsService) as any;
    fixture = TestBed.createComponent(MetricsDashboardComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // ========================================================================
  // Initialization
  // ========================================================================

  describe('Initialization', () => {
    it('should subscribe to metrics on init', () => {
      fixture.detectChanges();

      expect(component.executionHistory).toBeDefined();
      expect(component.aggregateMetrics).toBeNull();
      expect(component.recommendations).toBeDefined();
    });

    it('should update when metrics change', (done) => {
      (metricsService as any).aggregateMetrics$ = of(mockAggregateMetrics);

      fixture.detectChanges();

      setTimeout(() => {
        expect(component.aggregateMetrics).toEqual(mockAggregateMetrics);
        done();
      }, 100);
    });

    it('should update when recommendations change', (done) => {
      (metricsService as any).recommendations$ = of(mockRecommendations);

      fixture.detectChanges();

      setTimeout(() => {
        expect(component.recommendations.length).toBe(1);
        expect(component.recommendations[0].parameter).toBe('top_k');
        done();
      }, 100);
    });
  });

  // ========================================================================
  // Config Changes
  // ========================================================================

  describe('Config Changes', () => {
    it('should regenerate recommendations when config changes', () => {
      const config: QueryConfig = {
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
      };

      component.currentConfig = config;
      component.ngOnChanges({
        currentConfig: {
          currentValue: config,
          previousValue: undefined,
          firstChange: true,
          isFirstChange: () => true,
        },
      });

      expect(metricsService.generateRecommendationsFor).toHaveBeenCalledWith(
        config
      );
    });
  });

  // ========================================================================
  // Metrics Actions
  // ========================================================================

  describe('Clear Metrics', () => {
    it('should clear metrics and history', () => {
      component.clearMetrics();

      expect(metricsService.clearHistory).toHaveBeenCalled();
      expect(component.repeatabilityResult).toBeNull();
    });
  });

  describe('Export Metrics', () => {
    it('should export as CSV', () => {
      metricsService.exportAsCSV.mockReturnValue('csv data');

      component.exportAsCSV();

      expect(metricsService.exportAsCSV).toHaveBeenCalled();
      expect(metricsService.downloadFile).toHaveBeenCalledWith(
        'csv data',
        expect.stringMatching(/metrics_.*\.csv/),
        'text/csv'
      );
    });

    it('should not export CSV when no metrics', () => {
      metricsService.exportAsCSV.mockReturnValue('');

      component.exportAsCSV();

      expect(metricsService.downloadFile).not.toHaveBeenCalled();
    });

    it('should export as JSON', () => {
      metricsService.exportAsJSON.mockReturnValue('{"test": true}');

      component.exportAsJSON();

      expect(metricsService.exportAsJSON).toHaveBeenCalled();
      expect(metricsService.downloadFile).toHaveBeenCalledWith(
        '{"test": true}',
        expect.stringMatching(/metrics_.*\.json/),
        'application/json'
      );
    });
  });

  // ========================================================================
  // Repeatability Testing
  // ========================================================================

  describe('Repeatability Testing', () => {
    it('should run repeatability test', async () => {
      const mockMetrics: ExecutionMetrics = {
        timing: {
          total_time_ms: 1200,
        },
        tokens: {
          input_tokens: 100,
          output_tokens: 200,
          total_tokens: 300,
        },
      };

      const mockResult = {
        test_id: 'test_123',
        query: 'test query',
        iterations: 5,
        timestamp: new Date().toISOString(),
        latency: {
          min: 1000,
          max: 1500,
          avg: 1200,
          median: 1200,
          std_dev: 100,
          coefficient_of_variation: 0.08,
        },
        tokens: {
          min: 280,
          max: 320,
          avg: 300,
          median: 300,
          std_dev: 10,
          coefficient_of_variation: 0.03,
        },
        cost: {
          min: 0.009,
          max: 0.011,
          avg: 0.01,
          median: 0.01,
          std_dev: 0.001,
          coefficient_of_variation: 0.1,
        },
        consistency_score: 0.9,
        executions: [mockMetrics],
        config: {} as QueryConfig,
      };

      component.currentConfig = {} as QueryConfig;
      component.onExecuteQuery = jest.fn().mockResolvedValue(mockMetrics);
      component.testIterations = 5;

      metricsService.analyzeRepeatability.mockReturnValue(mockResult);

      await component.runRepeatabilityTest();

      expect(component.onExecuteQuery).toHaveBeenCalledTimes(5);
      expect(metricsService.analyzeRepeatability).toHaveBeenCalled();
      expect(component.repeatabilityResult).toEqual(mockResult);
      expect(component.isRunningRepeatabilityTest).toBe(false);
    });

    it('should not run test without config', async () => {
      component.currentConfig = undefined;

      await component.runRepeatabilityTest();

      expect(metricsService.analyzeRepeatability).not.toHaveBeenCalled();
    });

    it('should not run test without execute function', async () => {
      component.currentConfig = {} as QueryConfig;
      component.onExecuteQuery = undefined;

      await component.runRepeatabilityTest();

      expect(metricsService.analyzeRepeatability).not.toHaveBeenCalled();
    });
  });

  // ========================================================================
  // Recommendations
  // ========================================================================

  describe('Recommendations', () => {
    it('should apply recommendation', () => {
      const rec: ParameterRecommendation = {
        type: 'performance',
        parameter: 'top_k',
        current_value: 10,
        recommended_value: 7,
        reason: 'Test',
        impact_description: 'Test impact',
        confidence: 0.8,
      };

      component.applyRecommendation(rec);

      // Just checking it doesn't throw
      expect(component).toBeTruthy();
    });

    it('should get correct icon for recommendation type', () => {
      expect(component.getRecommendationIcon('performance')).toBe('speed');
      expect(component.getRecommendationIcon('consistency')).toBe(
        'check_circle'
      );
      expect(component.getRecommendationIcon('cost')).toBe('attach_money');
      expect(component.getRecommendationIcon('quality')).toBe('star');
      expect(component.getRecommendationIcon('unknown')).toBe('lightbulb');
    });

    it('should get correct color for recommendation type', () => {
      expect(component.getRecommendationColor('performance')).toContain('blue');
      expect(component.getRecommendationColor('consistency')).toContain(
        'green'
      );
      expect(component.getRecommendationColor('cost')).toContain('orange');
      expect(component.getRecommendationColor('quality')).toContain('purple');
    });
  });

  // ========================================================================
  // Formatting Helpers
  // ========================================================================

  describe('Formatting Helpers', () => {
    it('should format percentage', () => {
      expect(component.getPercentage(0.85)).toBe('85.0%');
      expect(component.getPercentage(0.123)).toBe('12.3%');
    });

    it('should format numbers', () => {
      expect(component.formatNumber(1234.567, 0)).toBe('1235');
      expect(component.formatNumber(1234.567, 2)).toBe('1234.57');
    });

    it('should format currency', () => {
      expect(component.formatCurrency(0.0123, 'USD')).toBe('USD 0.0123');
      expect(component.formatCurrency(1.5, 'EUR')).toBe('EUR 1.5000');
    });
  });

  // ========================================================================
  // Component Lifecycle
  // ========================================================================

  describe('Lifecycle', () => {
    it('should clean up on destroy', () => {
      const destroySpy = jest.spyOn(component['destroy$'], 'next');
      const completeSpy = jest.spyOn(component['destroy$'], 'complete');

      component.ngOnDestroy();

      expect(destroySpy).toHaveBeenCalled();
      expect(completeSpy).toHaveBeenCalled();
    });
  });
});
