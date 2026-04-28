import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';

// Angular Material imports
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ConsolidatedMetrics } from '../../api/models/use-case.models';

@Component({
  selector: 'app-execution-metrics',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
    MatChipsModule,
  ],
  templateUrl: './execution-metrics.component.html',
  styleUrls: ['./execution-metrics.component.scss'],
})
export class ExecutionMetricsComponent implements OnInit {
  @Input() metrics?: ConsolidatedMetrics;

  // Computed properties
  confidenceClass = '';
  confidenceIcon = '';
  overallStatusClass = '';
  overallStatusIcon = '';

  // Performance indicators
  performanceIndicators = {
    retrieval: { status: 'success', icon: 'speed', message: 'Ready' },
    guard: { status: 'success', icon: 'security', message: 'Ready' },
    model: { status: 'success', icon: 'psychology', message: 'Ready' },
  };

  ngOnInit(): void {
    if (!this.metrics) {
      return;
    }
    this.updateConfidenceClass();
    this.updateOverallStatus();
    this.updatePerformanceIndicators();
  }

  // ============================================================================
  // Status Updates
  // ============================================================================

  private updateConfidenceClass(): void {
    if (!this.metrics) return;
    const score = this.metrics.confidence_score;

    if (score >= 0.8) {
      this.confidenceClass = 'high';
      this.confidenceIcon = 'check_circle';
    } else if (score >= 0.6) {
      this.confidenceClass = 'medium';
      this.confidenceIcon = 'warning';
    } else {
      this.confidenceClass = 'low';
      this.confidenceIcon = 'error';
    }
  }

  private updateOverallStatus(): void {
    if (!this.metrics) return;
    // Derive overall status from confidence score since backend doesn't provide it
    const confidence = this.metrics.confidence_score;
    if (confidence >= 0.7) {
      this.overallStatusClass = 'success';
      this.overallStatusIcon = 'check_circle';
    } else if (confidence >= 0.4) {
      this.overallStatusClass = 'warning';
      this.overallStatusIcon = 'warning';
    } else {
      this.overallStatusClass = 'error';
      this.overallStatusIcon = 'error';
    }
  }

  private updatePerformanceIndicators(): void {
    if (!this.metrics) return;
    // Retrieval performance
    if (this.metrics.retrieval) {
      const avgSim = this.metrics.retrieval.avg_similarity;
      if (avgSim >= 0.8) {
        this.performanceIndicators.retrieval.status = 'success';
      } else if (avgSim >= 0.6) {
        this.performanceIndicators.retrieval.status = 'warning';
      } else {
        this.performanceIndicators.retrieval.status = 'error';
      }
    }

    // Guard performance
    if (this.metrics.guard) {
      const riskScore = this.metrics.guard.risk_score;
      if (riskScore <= 0.3) {
        this.performanceIndicators.guard.status = 'success';
      } else if (riskScore <= 0.6) {
        this.performanceIndicators.guard.status = 'warning';
      } else {
        this.performanceIndicators.guard.status = 'error';
      }
    }

    // Model performance (based on processing time in seconds)
    if (this.metrics.model) {
      // processing_time is in seconds, convert to ms for comparison
      const processingTimeMs = this.metrics.model.processing_time * 1000;
      if (processingTimeMs <= 2000) {
        this.performanceIndicators.model.status = 'success';
      } else if (processingTimeMs <= 5000) {
        this.performanceIndicators.model.status = 'warning';
      } else {
        this.performanceIndicators.model.status = 'error';
      }
    }
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  formatDuration(ms: number): string {
    if (isNaN(ms)) {
      return 'N/A';
    }
    if (ms < 1000) {
      return `${ms}ms`;
    } else if (ms < 60000) {
      return `${(ms / 1000).toFixed(1)}s`;
    } else {
      const minutes = Math.floor(ms / 60000);
      const seconds = Math.floor((ms % 60000) / 1000);
      return `${minutes}m ${seconds}s`;
    }
  }

  formatTokens(tokens: number): string {
    if (isNaN(tokens)) {
      return 'N/A';
    }
    if (tokens < 1000) {
      return tokens.toString();
    } else if (tokens < 1000000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    } else {
      return `${(tokens / 1000000).toFixed(1)}M`;
    }
  }

  formatPercentage(value: number | undefined | null): string {
    if (value == null || isNaN(value)) {
      return 'N/A';
    }
    return `${(value * 100).toFixed(1)}%`;
  }

  formatSimilarity(score: number | undefined | null): string {
    if (score == null || isNaN(score)) {
      return 'N/A';
    }
    return `${(score * 100).toFixed(1)}%`;
  }

  formatRiskScore(score: number | undefined | null): string {
    if (score == null || isNaN(score)) {
      return 'N/A';
    }
    return `${(score * 100).toFixed(1)}%`;
  }

  formatCost(estimate?: number): string {
    if (estimate == null) return 'N/A';
    return `$${estimate.toFixed(4)}`;
  }

  // ============================================================================
  // Template Helpers
  // ============================================================================

  get hasRetrievalMetrics(): boolean {
    return this.metrics?.retrieval != null;
  }

  get hasGuardMetrics(): boolean {
    return this.metrics?.guard != null;
  }

  get hasModelMetrics(): boolean {
    return this.metrics?.model != null;
  }

  get hasHighRisk(): boolean {
    return (this.metrics?.guard?.risk_score ?? 0) > 0.6;
  }

  get hasMediumRisk(): boolean {
    const riskScore = this.metrics?.guard?.risk_score ?? 0;
    return riskScore > 0.3 && riskScore <= 0.6;
  }

  get hasLowRisk(): boolean {
    return (this.metrics?.guard?.risk_score ?? 0) <= 0.3;
  }

  get hasGuardDetails(): boolean {
    return this.hasGuardMetrics && this.metrics?.guard?.details != null;
  }

  get hasContentFiltered(): boolean {
    return (
      this.hasGuardDetails &&
      (this.metrics?.guard?.details as any)?.content_filtered === true
    );
  }

  get hasPIIDetected(): boolean {
    return (
      this.hasGuardDetails &&
      (this.metrics?.guard?.details as any)?.pii_detected === true
    );
  }

  get hasToxicityDetected(): boolean {
    return (
      this.hasGuardDetails &&
      (this.metrics?.guard?.details as any)?.toxicity_detected === true
    );
  }

  get hasJailbreakAttempt(): boolean {
    return (
      this.hasGuardDetails &&
      (this.metrics?.guard?.details as any)?.jailbreak_attempt === true
    );
  }

  get hasSecretsDetected(): boolean {
    return (
      this.hasGuardDetails &&
      (this.metrics?.guard?.details as any)?.secrets_detected === true
    );
  }

  get hasGibberishDetected(): boolean {
    return (
      this.hasGuardDetails &&
      (this.metrics?.guard?.details as any)?.gibberish_detected === true
    );
  }

  get hasInvalidLanguage(): boolean {
    return (
      this.hasGuardDetails &&
      (this.metrics?.guard?.details as any)?.invalid_language === true
    );
  }

  get hasBlockedCategories(): boolean {
    return (
      this.hasGuardDetails &&
      Array.isArray(
        (this.metrics?.guard?.details as any)?.blocked_categories
      ) &&
      (this.metrics?.guard?.details as any).blocked_categories.length > 0
    );
  }

  get blockedCategoriesList(): string[] {
    if (this.hasBlockedCategories && this.metrics?.guard?.details) {
      return (this.metrics.guard.details as any).blocked_categories || [];
    }
    return [];
  }

  get hasCostEstimate(): boolean {
    return (
      this.hasModelMetrics &&
      this.metrics?.model?.metadata?.cost_estimate != null
    );
  }

  get hasCostBreakdown(): boolean {
    return (
      this.hasModelMetrics &&
      this.metrics?.model?.metadata?.cost_breakdown != null
    );
  }

  get hasModelParameters(): boolean {
    return (
      this.hasModelMetrics && this.metrics?.model?.metadata?.parameters != null
    );
  }

  get hasTimingBreakdown(): boolean {
    return (
      this.hasModelMetrics &&
      this.metrics?.model?.metadata?.timing_breakdown != null
    );
  }

  get modelParameters(): any {
    return this.metrics?.model?.metadata?.parameters || {};
  }

  get costBreakdown(): any {
    return this.metrics?.model?.metadata?.cost_breakdown || {};
  }

  get timingBreakdown(): any {
    return this.metrics?.model?.metadata?.timing_breakdown || {};
  }

  get displayModelName(): string {
    if (!this.metrics?.model) {
      return 'N/A';
    }
    // Backend stores actual model ID in metadata["model_id"] if available,
    // otherwise falls back to ModelType enum string in model_id field
    // Check metadata first for the actual model ID (e.g., "gpt-4o-mini", "claude-3-5-sonnet")
    // Use bracket notation because metadata has index signature
    const metadataModelId = this.metrics.model.metadata?.['model_id'] as
      | string
      | undefined;
    if (metadataModelId && metadataModelId !== this.metrics.model.model_id) {
      return metadataModelId;
    }
    // If model_id looks like a ModelType enum (all caps, contains ModelType prefix, or no dashes/underscores)
    const modelId = this.metrics.model.model_id;
    if (
      modelId &&
      (modelId.startsWith('ModelType.') ||
        (modelId === modelId.toUpperCase() &&
          !modelId.includes('-') &&
          !modelId.includes('_')))
    ) {
      // This is likely a ModelType enum, return a cleaned version
      return modelId.replace('ModelType.', '');
    }
    // Otherwise, it's likely an actual model ID
    return modelId || 'N/A';
  }

  // ============================================================================
  // Color and Status Helpers
  // ============================================================================

  getConfidenceColor(): string {
    switch (this.confidenceClass) {
      case 'high':
        return '#4caf50';
      case 'medium':
        return '#ff9800';
      case 'low':
        return '#f44336';
      default:
        return '#666';
    }
  }

  getOverallStatusColor(): string {
    switch (this.overallStatusClass) {
      case 'success':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      case 'error':
        return '#f44336';
      default:
        return '#666';
    }
  }

  getRetrievalStatusColor(): string {
    switch (this.performanceIndicators.retrieval.status) {
      case 'success':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      case 'error':
        return '#f44336';
      default:
        return '#666';
    }
  }

  getGuardStatusColor(): string {
    switch (this.performanceIndicators.guard.status) {
      case 'success':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      case 'error':
        return '#f44336';
      default:
        return '#666';
    }
  }

  getModelStatusColor(): string {
    switch (this.performanceIndicators.model.status) {
      case 'success':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      case 'error':
        return '#f44336';
      default:
        return '#666';
    }
  }
}
