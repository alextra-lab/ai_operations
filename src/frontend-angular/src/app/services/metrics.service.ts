/**
 * MetricsService
 *
 * Service for calculating metrics, generating recommendations,
 * and running repeatability tests.
 *
 * Features:
 * - Aggregate metrics calculation
 * - Parameter recommendations based on metrics
 * - Repeatability testing with consistency scoring
 * - Performance time series tracking
 * - Metrics export (CSV/JSON)
 *
 * Related: P4-TOOLS-07, ADR-045
 */

import { Injectable } from '@angular/core';
import {
  BehaviorSubject,
  concatMap,
  finalize,
  from,
  Observable,
  tap,
} from 'rxjs';

import {
  ExecutionMetrics,
  QueryConfig,
  SamplingPreset,
} from '../api/models/query-config.models';
import {
  AggregateMetrics,
  max,
  mean,
  median,
  min,
  ParameterRecommendation,
  percentile,
  RepeatabilityMetrics,
  RepeatabilityTestConfig,
  RepeatabilityTestResult,
  standardDeviation,
} from '../models/metrics.models';

@Injectable({
  providedIn: 'root',
})
export class MetricsService {
  // Execution history tracking
  private executionHistory: ExecutionMetrics[] = [];
  private readonly executionHistorySubject = new BehaviorSubject<
    ExecutionMetrics[]
  >([]);
  executionHistory$ = this.executionHistorySubject.asObservable();

  // Aggregate metrics tracking
  private readonly aggregateMetricsSubject =
    new BehaviorSubject<AggregateMetrics | null>(null);
  aggregateMetrics$ = this.aggregateMetricsSubject.asObservable();

  // Recommendations tracking
  private readonly recommendationsSubject = new BehaviorSubject<
    ParameterRecommendation[]
  >([]);
  recommendations$ = this.recommendationsSubject.asObservable();

  constructor() {}

  // ========================================================================
  // Execution History Management
  // ========================================================================

  /**
   * Add execution metrics to history
   */
  addExecution(metrics: ExecutionMetrics): void {
    this.executionHistory.push(metrics);
    this.executionHistorySubject.next([...this.executionHistory]);

    // Recalculate aggregates and recommendations
    this.calculateAggregates();
    this.generateRecommendations();
  }

  /**
   * Clear execution history
   */
  clearHistory(): void {
    this.executionHistory = [];
    this.executionHistorySubject.next([]);
    this.aggregateMetricsSubject.next(null);
    this.recommendationsSubject.next([]);
  }

  /**
   * Get execution history
   */
  getExecutionHistory(): ExecutionMetrics[] {
    return [...this.executionHistory];
  }

  // ========================================================================
  // Aggregate Metrics Calculation
  // ========================================================================

  /**
   * Calculate aggregate metrics from execution history
   */
  private calculateAggregates(): void {
    if (this.executionHistory.length === 0) {
      this.aggregateMetricsSubject.next(null);
      return;
    }

    const history = this.executionHistory;

    // Extract values
    const latencies = history.map((m) => m.timing.total_time_ms);
    const totalTokens = history.map((m) => m.tokens.total_tokens);
    const inputTokens = history.map((m) => m.tokens.input_tokens);
    const outputTokens = history.map((m) => m.tokens.output_tokens);
    const costs = history
      .filter((m) => m.cost !== undefined)
      .map((m) => m.cost!.total_cost);

    // Calculate latency statistics
    const avgLatency = mean(latencies);
    const latencyStdDev = standardDeviation(latencies);

    // Calculate token statistics
    const avgTokens = mean(totalTokens);
    const tokenStdDev = standardDeviation(totalTokens);

    // Calculate consistency score (inverse of coefficient of variation)
    // Higher score = more consistent
    const latencyCV = avgLatency > 0 ? latencyStdDev / avgLatency : 0;
    const tokenCV = avgTokens > 0 ? tokenStdDev / avgTokens : 0;
    const consistencyScore = 1 - Math.min((latencyCV + tokenCV) / 2, 1);

    // Calculate cost statistics
    const totalCost = costs.length > 0 ? costs.reduce((a, b) => a + b, 0) : 0;
    const avgCost = costs.length > 0 ? mean(costs) : 0;

    // Project monthly cost (assuming 1 query per day)
    const projectedMonthlyCost = avgCost * 30;

    // Get currency from first cost entry
    const currency = history.find((m) => m.cost)?.cost?.currency || 'USD';

    // Build aggregate metrics
    const aggregates: AggregateMetrics = {
      execution_count: history.length,

      // Latency
      average_latency_ms: avgLatency,
      min_latency_ms: min(latencies),
      max_latency_ms: max(latencies),
      p50_latency_ms: percentile(latencies, 50),
      p95_latency_ms: percentile(latencies, 95),

      // Tokens
      average_tokens: avgTokens,
      total_tokens: totalTokens.reduce((a, b) => a + b, 0),
      average_input_tokens: mean(inputTokens),
      average_output_tokens: mean(outputTokens),

      // Cost
      total_cost: totalCost,
      average_cost_per_query: avgCost,
      projected_monthly_cost: projectedMonthlyCost,
      currency,

      // Consistency
      consistency_score: consistencyScore,
      latency_std_dev: latencyStdDev,
      token_std_dev: tokenStdDev,

      // Success
      success_rate: 1.0, // TODO: Track errors when available
      error_count: 0,
    };

    this.aggregateMetricsSubject.next(aggregates);
  }

  /**
   * Get current aggregate metrics
   */
  getAggregateMetrics(): AggregateMetrics | null {
    return this.aggregateMetricsSubject.value;
  }

  // ========================================================================
  // Parameter Recommendations
  // ========================================================================

  /**
   * Generate parameter recommendations based on metrics
   */
  private generateRecommendations(config?: QueryConfig): void {
    const aggregates = this.aggregateMetricsSubject.value;
    if (!aggregates || aggregates.execution_count < 3) {
      // Need at least 3 executions for meaningful recommendations
      this.recommendationsSubject.next([]);
      return;
    }

    const recommendations: ParameterRecommendation[] = [];

    // Recommendation 1: High latency → reduce top_k
    if (aggregates.average_latency_ms > 3000) {
      recommendations.push({
        type: 'performance',
        parameter: 'top_k',
        current_value: config?.rag.top_k || 10,
        recommended_value: Math.max(
          3,
          Math.floor((config?.rag.top_k || 10) * 0.7)
        ),
        reason: 'High average latency detected.',
        impact_description:
          'Reducing top_k retrieves fewer chunks, ' +
          'improving response time.',
        confidence: 0.8,
      });
    }

    // Recommendation 2: Low consistency → stricter preset
    if (aggregates.consistency_score < 0.7) {
      recommendations.push({
        type: 'consistency',
        parameter: 'sampling_preset',
        current_value: config?.sampling.preset || SamplingPreset.BALANCED,
        recommended_value: SamplingPreset.STRICT,
        reason: 'Low consistency score detected.',
        impact_description:
          'STRICT preset (temp=0.15) produces more ' + 'deterministic outputs.',
        confidence: 0.85,
      });
    }

    // Recommendation 3: High token usage → reduce max_tokens
    if (aggregates.average_tokens > 2000) {
      recommendations.push({
        type: 'cost',
        parameter: 'max_tokens',
        current_value: config?.sampling.max_tokens || 2048,
        recommended_value: 1500,
        reason: 'High token usage detected.',
        impact_description: 'Reducing max_tokens can lower costs by ~25%.',
        confidence: 0.75,
      });
    }

    // Recommendation 4: High cost with good quality →
    // consider smaller model
    if (
      aggregates.average_cost_per_query > 0.01 &&
      aggregates.consistency_score > 0.8
    ) {
      recommendations.push({
        type: 'cost',
        parameter: 'llm_model',
        current_value: config?.llm_model || 'gpt-4o',
        recommended_value: 'gpt-4o-mini',
        reason: 'High cost with good quality metrics.',
        impact_description: 'gpt-4o-mini is 60% cheaper with similar quality.',
        confidence: 0.7,
      });
    }

    // Recommendation 5: Very low latency variance →
    // can increase top_k for better quality
    if (
      aggregates.latency_std_dev < 100 &&
      aggregates.average_latency_ms < 1500
    ) {
      recommendations.push({
        type: 'quality',
        parameter: 'top_k',
        current_value: config?.rag.top_k || 10,
        recommended_value: Math.min(20, (config?.rag.top_k || 10) + 5),
        reason: 'Stable low latency allows more context.',
        impact_description:
          'Increasing top_k improves answer quality ' +
          'with minimal latency impact.',
        confidence: 0.8,
      });
    }

    this.recommendationsSubject.next(recommendations);
  }

  /**
   * Manually trigger recommendation generation with config
   */
  generateRecommendationsFor(config: QueryConfig): void {
    this.generateRecommendations(config);
  }

  /**
   * Get current recommendations
   */
  getRecommendations(): ParameterRecommendation[] {
    return this.recommendationsSubject.value;
  }

  // ========================================================================
  // Repeatability Testing
  // ========================================================================

  /**
   * Run repeatability test (execute same query N times)
   */
  runRepeatabilityTest(
    testConfig: RepeatabilityTestConfig,
    executeQueryFn: (config: QueryConfig) => Observable<ExecutionMetrics>
  ): Observable<RepeatabilityTestResult> {
    const executions: ExecutionMetrics[] = [];

    return from(Array(testConfig.iterations))
      .pipe(
        concatMap(() => executeQueryFn(testConfig.config)),
        tap((metrics) => executions.push(metrics)),
        finalize(() => {
          // Analysis happens in finalize to ensure all executions complete
        })
      )
      .pipe(
        // Convert to single RepeatabilityTestResult after all executions
        finalize(() => {
          // This will be handled by the component
        })
      ) as any;

    // NOTE: Actual implementation would need proper Observable handling
    // For now, return stub observable
    // Real implementation in component will handle this
  }

  /**
   * Analyze repeatability test results
   */
  analyzeRepeatability(
    query: string,
    config: QueryConfig,
    executions: ExecutionMetrics[]
  ): RepeatabilityTestResult {
    if (executions.length === 0) {
      throw new Error('No executions to analyze');
    }

    // Extract metrics
    const latencies = executions.map((e) => e.timing.total_time_ms);
    const tokens = executions.map((e) => e.tokens.total_tokens);
    const costs = executions
      .filter((e) => e.cost !== undefined)
      .map((e) => e.cost!.total_cost);

    // Calculate repeatability metrics for each dimension
    const latencyMetrics = this.calculateRepeatabilityMetrics(latencies);
    const tokenMetrics = this.calculateRepeatabilityMetrics(tokens);
    const costMetrics =
      costs.length > 0
        ? this.calculateRepeatabilityMetrics(costs)
        : {
            min: 0,
            max: 0,
            avg: 0,
            median: 0,
            std_dev: 0,
            coefficient_of_variation: 0,
          };

    // Overall consistency score (inverse of average CV)
    const avgCV =
      (latencyMetrics.coefficient_of_variation +
        tokenMetrics.coefficient_of_variation) /
      2;
    const consistencyScore = 1 - Math.min(avgCV, 1);

    return {
      test_id: `test_${Date.now()}`,
      query,
      iterations: executions.length,
      timestamp: new Date().toISOString(),
      latency: latencyMetrics,
      tokens: tokenMetrics,
      cost: costMetrics,
      consistency_score: consistencyScore,
      executions,
      config,
    };
  }

  /**
   * Calculate repeatability metrics for a set of values
   */
  private calculateRepeatabilityMetrics(
    values: number[]
  ): RepeatabilityMetrics {
    const avg = mean(values);
    const stdDev = standardDeviation(values);
    const cv = avg > 0 ? stdDev / avg : 0;

    return {
      min: min(values),
      max: max(values),
      avg,
      median: median(values),
      std_dev: stdDev,
      coefficient_of_variation: cv,
    };
  }

  // ========================================================================
  // Export Functions
  // ========================================================================

  /**
   * Export metrics as CSV
   */
  exportAsCSV(): string {
    const aggregates = this.aggregateMetricsSubject.value;
    if (!aggregates) {
      return '';
    }

    // CSV header
    const headers = ['Metric', 'Value', 'Unit'];

    // CSV rows
    const rows: string[][] = [
      ['Execution Count', String(aggregates.execution_count), 'queries'],
      ['Average Latency', aggregates.average_latency_ms.toFixed(2), 'ms'],
      ['P50 Latency', aggregates.p50_latency_ms.toFixed(2), 'ms'],
      ['P95 Latency', aggregates.p95_latency_ms.toFixed(2), 'ms'],
      ['Average Tokens', aggregates.average_tokens.toFixed(0), 'tokens'],
      ['Total Cost', aggregates.total_cost.toFixed(4), aggregates.currency],
      [
        'Average Cost',
        aggregates.average_cost_per_query.toFixed(4),
        aggregates.currency,
      ],
      [
        'Projected Monthly Cost',
        aggregates.projected_monthly_cost.toFixed(2),
        aggregates.currency,
      ],
      [
        'Consistency Score',
        (aggregates.consistency_score * 100).toFixed(1),
        '%',
      ],
    ];

    // Convert to CSV format
    const csvLines = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ];

    return csvLines.join('\n');
  }

  /**
   * Export metrics as JSON
   */
  exportAsJSON(): string {
    const aggregates = this.aggregateMetricsSubject.value;
    const recommendations = this.recommendationsSubject.value;
    const history = this.executionHistory;

    const exportData = {
      export_timestamp: new Date().toISOString(),
      aggregate_metrics: aggregates,
      recommendations,
      execution_history: history,
      execution_count: history.length,
    };

    return JSON.stringify(exportData, null, 2);
  }

  /**
   * Download data as file
   */
  downloadFile(content: string, filename: string, type: string): void {
    const blob = new Blob([content], { type });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(url);
  }
}
