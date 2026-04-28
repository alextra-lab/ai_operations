import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ConsolidatedMetrics } from '../../api/models/use-case.models';
import { ExecutionMetricsComponent } from './execution-metrics.component';

describe('ExecutionMetricsComponent', () => {
  let component: ExecutionMetricsComponent;
  let fixture: ComponentFixture<ExecutionMetricsComponent>;

  const mockMetrics: ConsolidatedMetrics = {
    retrieval: {
      top_k: 10,
      hits: 5,
      avg_similarity: 0.85,
      min_similarity: 0.6,
      max_similarity: 0.9,
      documents_retrieved: 5,
      total_documents_searched: 1000,
      filtered_documents: 50,
    },
    guard: {
      risk_score: 0.2,
      modified: false,
      details: {
        content_filtered: false,
        pii_detected: false,
        toxicity_detected: false,
        jailbreak_attempt: false,
        blocked_categories: [],
      },
    },
    model: {
      model_id: 'gpt-4',
      tokens_in: 100,
      tokens_out: 50,
      total_tokens: 150,
      processing_time: 2.0,
      metadata: {
        cost_estimate: 0.0015,
        cost_breakdown: {
          total_cost: 0.0015,
          input_cost: 0.001,
          output_cost: 0.0005,
          currency: 'USD',
          pricing_source: 'pricing_history',
        },
      },
    } as any,
    confidence_score: 0.85,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExecutionMetricsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ExecutionMetricsComponent);
    component = fixture.componentInstance;
    // Use a deep copy so tests that mutate metrics don't affect others
    component.metrics = JSON.parse(JSON.stringify(mockMetrics));
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize confidence and status classes', () => {
    expect(component.confidenceClass).toBe('high');
    expect(component.confidenceIcon).toBe('check_circle');
    expect(component.overallStatusClass).toBe('success');
    expect(component.overallStatusIcon).toBe('check_circle');
  });

  it('should update confidence level for high score', () => {
    component.metrics.confidence_score = 0.9;
    component.ngOnInit();

    expect(component.confidenceClass).toBe('high');
    expect(component.confidenceIcon).toBe('check_circle');
  });

  it('should update confidence level for medium score', () => {
    component.metrics.confidence_score = 0.7;
    component.ngOnInit();

    expect(component.confidenceClass).toBe('medium');
    expect(component.confidenceIcon).toBe('warning');
  });

  it('should update confidence level for low score', () => {
    component.metrics.confidence_score = 0.4;
    component.ngOnInit();

    expect(component.confidenceClass).toBe('low');
    expect(component.confidenceIcon).toBe('error');
  });

  it('should update overall status for warning', () => {
    component.metrics.confidence_score = 0.65; // Medium confidence = warning
    component.ngOnInit();

    expect(component.overallStatusClass).toBe('warning');
    expect(component.overallStatusIcon).toBe('warning');
  });

  it('should update overall status for error', () => {
    // Component derives status from confidence_score, not overall_status
    component.metrics.confidence_score = 0.3; // Low confidence = error
    component.ngOnInit();

    expect(component.overallStatusClass).toBe('error');
    expect(component.overallStatusIcon).toBe('error');
  });

  it('should format duration correctly', () => {
    expect(component.formatDuration(500)).toBe('500ms');
    expect(component.formatDuration(1500)).toBe('1.5s');
    expect(component.formatDuration(65000)).toBe('1m 5s');
  });

  it('should format tokens correctly', () => {
    expect(component.formatTokens(500)).toBe('500');
    expect(component.formatTokens(1500)).toBe('1.5K');
    expect(component.formatTokens(1500000)).toBe('1.5M');
  });

  it('should format percentage correctly', () => {
    expect(component.formatPercentage(0.85)).toBe('85.0%');
    expect(component.formatPercentage(0.123)).toBe('12.3%');
  });

  it('should format similarity correctly', () => {
    expect(component.formatSimilarity(0.85)).toBe('85.0%');
    expect(component.formatSimilarity(0.123)).toBe('12.3%');
  });

  it('should format risk score correctly', () => {
    expect(component.formatRiskScore(0.2)).toBe('20.0%');
    expect(component.formatRiskScore(0.75)).toBe('75.0%');
  });

  it('should format cost correctly', () => {
    expect(component.formatCost(0.0015)).toBe('$0.0015');
    expect(component.formatCost(0.0)).toBe('$0.0000');
    expect(component.formatCost(0.1234)).toBe('$0.1234');
    expect(component.formatCost(undefined)).toBe('N/A');
    expect(component.formatCost(null as any)).toBe('N/A');
  });

  it('should detect hasRetrievalMetrics correctly', () => {
    expect(component.hasRetrievalMetrics).toBe(true);

    component.metrics.retrieval = undefined as any;
    expect(component.hasRetrievalMetrics).toBe(false);
  });

  it('should detect hasGuardMetrics correctly', () => {
    expect(component.hasGuardMetrics).toBe(true);

    component.metrics.guard = undefined as any;
    expect(component.hasGuardMetrics).toBe(false);
  });

  it('should detect hasModelMetrics correctly', () => {
    expect(component.hasModelMetrics).toBe(true);

    component.metrics.model = undefined as any;
    expect(component.hasModelMetrics).toBe(false);
  });

  it('should detect hasCostEstimate correctly', () => {
    // Component checks hasModelMetrics && model.metadata.cost_estimate
    // Mock has model and metadata.cost_estimate set, so should be true
    expect(component.hasModelMetrics).toBe(true);
    expect(component.hasCostEstimate).toBe(true);

    // Test false case - remove cost_estimate from metadata
    component.metrics.model.metadata = {};
    expect(component.hasCostEstimate).toBe(false);
  });

  it('should detect hasGuardDetails correctly', () => {
    expect(component.hasGuardDetails).toBe(true);

    // Ensure guard object exists before modifying details
    if (!component.metrics.guard) {
      component.metrics.guard = { risk_score: 0.2, modified: false };
    }
    component.metrics.guard.details = undefined;
    expect(component.hasGuardDetails).toBe(false);
  });

  it('should detect high risk correctly', () => {
    // Ensure guard object exists
    if (!component.metrics.guard) {
      component.metrics.guard = { risk_score: 0.2, modified: false };
    }
    component.metrics.guard.risk_score = 0.8;
    expect(component.hasHighRisk).toBe(true);

    component.metrics.guard.risk_score = 0.5;
    expect(component.hasHighRisk).toBe(false);
  });

  it('should detect medium risk correctly', () => {
    // Ensure guard object exists
    if (!component.metrics.guard) {
      component.metrics.guard = { risk_score: 0.2, modified: false };
    }
    component.metrics.guard.risk_score = 0.5;
    expect(component.hasMediumRisk).toBe(true);

    component.metrics.guard.risk_score = 0.2;
    expect(component.hasMediumRisk).toBe(false);

    component.metrics.guard.risk_score = 0.8;
    expect(component.hasMediumRisk).toBe(false);
  });

  it('should detect low risk correctly', () => {
    // Ensure guard object exists
    if (!component.metrics.guard) {
      component.metrics.guard = { risk_score: 0.2, modified: false };
    }
    component.metrics.guard.risk_score = 0.2;
    expect(component.hasLowRisk).toBe(true);

    component.metrics.guard.risk_score = 0.5;
    expect(component.hasLowRisk).toBe(false);
  });

  it('should detect content filtered correctly', () => {
    expect(component.hasContentFiltered).toBe(false);

    // Ensure guard.details exists
    if (!component.metrics.guard.details) {
      component.metrics.guard.details = {};
    }
    component.metrics.guard.details.content_filtered = true;
    expect(component.hasContentFiltered).toBe(true);
  });

  it('should detect PII detected correctly', () => {
    expect(component.hasPIIDetected).toBe(false);

    // Ensure guard.details exists
    if (!component.metrics.guard.details) {
      component.metrics.guard.details = {};
    }
    component.metrics.guard.details.pii_detected = true;
    expect(component.hasPIIDetected).toBe(true);
  });

  it('should detect toxicity detected correctly', () => {
    expect(component.hasToxicityDetected).toBe(false);

    // Ensure guard.details exists
    if (!component.metrics.guard.details) {
      component.metrics.guard.details = {};
    }
    component.metrics.guard.details.toxicity_detected = true;
    expect(component.hasToxicityDetected).toBe(true);
  });

  it('should detect jailbreak attempt correctly', () => {
    expect(component.hasJailbreakAttempt).toBe(false);

    // Ensure guard.details exists
    if (!component.metrics.guard.details) {
      component.metrics.guard.details = {};
    }
    component.metrics.guard.details.jailbreak_attempt = true;
    expect(component.hasJailbreakAttempt).toBe(true);
  });

  it('should detect blocked categories correctly', () => {
    expect(component.hasBlockedCategories).toBe(false);

    // Ensure guard.details exists
    if (!component.metrics.guard.details) {
      component.metrics.guard.details = {};
    }
    component.metrics.guard.details.blocked_categories = ['category1'];
    expect(component.hasBlockedCategories).toBe(true);
  });

  it('should get blocked categories list correctly', () => {
    // Ensure guard.details exists
    if (!component.metrics.guard.details) {
      component.metrics.guard.details = {};
    }
    component.metrics.guard.details.blocked_categories = [
      'category1',
      'category2',
    ];
    expect(component.blockedCategoriesList).toEqual(['category1', 'category2']);

    component.metrics.guard.details.blocked_categories = undefined;
    expect(component.blockedCategoriesList).toEqual([]);
  });

  it('should get confidence color correctly', () => {
    component.confidenceClass = 'high';
    expect(component.getConfidenceColor()).toBe('#4caf50');

    component.confidenceClass = 'medium';
    expect(component.getConfidenceColor()).toBe('#ff9800');

    component.confidenceClass = 'low';
    expect(component.getConfidenceColor()).toBe('#f44336');
  });

  it('should get overall status color correctly', () => {
    component.overallStatusClass = 'success';
    expect(component.getOverallStatusColor()).toBe('#4caf50');

    component.overallStatusClass = 'warning';
    expect(component.getOverallStatusColor()).toBe('#ff9800');

    component.overallStatusClass = 'error';
    expect(component.getOverallStatusColor()).toBe('#f44336');
  });

  it('should get retrieval status color correctly', () => {
    component.performanceIndicators.retrieval.status = 'success';
    expect(component.getRetrievalStatusColor()).toBe('#4caf50');

    component.performanceIndicators.retrieval.status = 'warning';
    expect(component.getRetrievalStatusColor()).toBe('#ff9800');

    component.performanceIndicators.retrieval.status = 'error';
    expect(component.getRetrievalStatusColor()).toBe('#f44336');
  });

  it('should get guard status color correctly', () => {
    component.performanceIndicators.guard.status = 'success';
    expect(component.getGuardStatusColor()).toBe('#4caf50');

    component.performanceIndicators.guard.status = 'warning';
    expect(component.getGuardStatusColor()).toBe('#ff9800');

    component.performanceIndicators.guard.status = 'error';
    expect(component.getGuardStatusColor()).toBe('#f44336');
  });

  it('should get model status color correctly', () => {
    component.performanceIndicators.model.status = 'success';
    expect(component.getModelStatusColor()).toBe('#4caf50');

    component.performanceIndicators.model.status = 'warning';
    expect(component.getModelStatusColor()).toBe('#ff9800');

    component.performanceIndicators.model.status = 'error';
    expect(component.getModelStatusColor()).toBe('#f44336');
  });
});
