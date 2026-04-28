/**
 * ParameterConfigPanelComponent Unit Tests
 *
 * Tests for parameter configuration panel.
 * Target: 80%+ coverage
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { Model } from '../../api/models/model-registry.models';
import {
  QueryConfig,
  SamplingPreset,
} from '../../api/models/query-config.models';
import { CollectionService } from '../../api/services/collection.service';
import { ModelRegistryService } from '../../api/services/model-registry.service';
import { ParameterConfigPanelComponent } from './parameter-config-panel.component';

describe('ParameterConfigPanelComponent', () => {
  let component: ParameterConfigPanelComponent;
  let fixture: ComponentFixture<ParameterConfigPanelComponent>;
  let modelService: jest.Mocked<ModelRegistryService>;
  let collectionService: jest.Mocked<CollectionService>;

  const mockModels: Model[] = [
    {
      id: '1',
      model_id: 'gpt-4o-mini',
      name: 'GPT-4o Mini',
      provider: 'OpenAI',
      is_active: true,
      created_at: '2025-01-01',
      updated_at: '2025-01-01',
    } as Model,
    {
      id: '2',
      model_id: 'gpt-4o',
      name: 'GPT-4o',
      provider: 'OpenAI',
      is_active: true,
      created_at: '2025-01-01',
      updated_at: '2025-01-01',
    } as Model,
  ];

  const mockCollections = {
    collections: [
      { name: 'documents', id: '1' },
      { name: 'policies', id: '2' },
    ],
    total: 2,
  };

  beforeEach(async () => {
    // Clear localStorage FIRST before any component creation
    localStorage.clear();

    const modelServiceMock = {
      getLLMModels: jest.fn().mockReturnValue(of(mockModels)),
      getAllModels: jest.fn().mockReturnValue(of(mockModels)),
      getActiveModels: jest.fn().mockReturnValue(of(mockModels)),
    };

    const collectionServiceMock = {
      listCollections: jest.fn().mockReturnValue(of(mockCollections)),
      listAvailableCollections: jest.fn().mockReturnValue(of(mockCollections)),
    };

    await TestBed.configureTestingModule({
      imports: [
        ParameterConfigPanelComponent,
        ReactiveFormsModule,
        BrowserAnimationsModule,
      ],
      providers: [
        { provide: ModelRegistryService, useValue: modelServiceMock },
        { provide: CollectionService, useValue: collectionServiceMock },
      ],
    }).compileComponents();

    modelService = TestBed.inject(
      ModelRegistryService
    ) as jest.Mocked<ModelRegistryService>;
    collectionService = TestBed.inject(
      CollectionService
    ) as jest.Mocked<CollectionService>;

    fixture = TestBed.createComponent(ParameterConfigPanelComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    // Always clean up localStorage after tests
    localStorage.clear();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // ========================================================================
  // Initialization Tests
  // ========================================================================

  describe('Initialization', () => {
    it('should load models on init', () => {
      fixture.detectChanges();

      component.models$.subscribe((models) => {
        expect(models).toEqual(mockModels);
      });

      expect(modelService.getLLMModels).toHaveBeenCalled();
    });

    it('should load collections on init', () => {
      fixture.detectChanges();

      expect(collectionService.listAvailableCollections).toHaveBeenCalled();
    });

    it('should create form with default values', () => {
      fixture.detectChanges();

      expect(component.configForm.get('llm_model')?.value).toBe('gpt-4o-mini');
      expect(component.configForm.get('sampling_preset')?.value).toBe(
        SamplingPreset.BALANCED
      );
      expect(component.configForm.get('top_k')?.value).toBe(10);
    });

    it('should handle collections loading error', () => {
      collectionService.listAvailableCollections.mockReturnValue(
        of({ collections: [], total: 0, error: 'Failed' } as any)
      );
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      fixture.detectChanges();

      // Should handle error gracefully
      expect(collectionService.listAvailableCollections).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });

  // ========================================================================
  // Sampling Preset Tests
  // ========================================================================

  describe('Sampling Presets', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should disable custom params for STRICT preset', () => {
      component.configForm.patchValue({
        sampling_preset: SamplingPreset.STRICT,
      });

      expect(component.configForm.get('temperature')?.disabled).toBe(true);
      expect(component.configForm.get('top_p')?.disabled).toBe(true);
      expect(component.configForm.get('max_tokens')?.disabled).toBe(true);
    });

    it('should enable custom params for CUSTOM preset', () => {
      component.configForm.patchValue({
        sampling_preset: SamplingPreset.CUSTOM,
      });

      expect(component.configForm.get('temperature')?.disabled).toBe(false);
      expect(component.configForm.get('top_p')?.disabled).toBe(false);
      expect(component.configForm.get('max_tokens')?.disabled).toBe(false);
    });

    it('should set preset values for STRICT', () => {
      component.configForm.patchValue({
        sampling_preset: SamplingPreset.STRICT,
      });

      expect(component.configForm.getRawValue().temperature).toBe(0.15);
      expect(component.configForm.getRawValue().top_p).toBe(0.9);
      expect(component.configForm.getRawValue().max_tokens).toBe(1024);
    });

    it('should set preset values for CREATIVE', () => {
      component.configForm.patchValue({
        sampling_preset: SamplingPreset.CREATIVE,
      });

      expect(component.configForm.getRawValue().temperature).toBe(0.85);
      expect(component.configForm.getRawValue().top_p).toBe(0.97);
    });
  });

  // ========================================================================
  // High-Entropy Detection Tests
  // ========================================================================

  describe('High-Entropy Detection', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should show warning for high-entropy config', (done) => {
      component.configForm.patchValue({
        sampling_preset: SamplingPreset.CUSTOM,
        temperature: 0.95,
        top_p: 0.98,
      });

      setTimeout(() => {
        expect(component.showHighEntropyWarning).toBe(true);
        done();
      }, 400);
    });

    it('should not show warning for safe config', (done) => {
      component.configForm.patchValue({
        sampling_preset: SamplingPreset.BALANCED,
      });

      setTimeout(() => {
        expect(component.showHighEntropyWarning).toBe(false);
        done();
      }, 400);
    });
  });

  // ========================================================================
  // Config Management Tests
  // ========================================================================

  describe('Config Management', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should emit config on changes', (done) => {
      component.configChanged.subscribe((config: QueryConfig) => {
        expect(config.llm_model).toBe('gpt-4o');
        expect(config.sampling.preset).toBe(SamplingPreset.CREATIVE);
        done();
      });

      component.configForm.patchValue({
        llm_model: 'gpt-4o',
        sampling_preset: SamplingPreset.CREATIVE,
      });
    });

    it('should patch form from initial config', () => {
      const initialConfig: QueryConfig = {
        llm_model: 'gpt-4o',
        embedding_model: 'text-embedding-3-large',
        sampling: {
          preset: SamplingPreset.STRICT,
          temperature: 0.15,
          top_p: 0.9,
          max_tokens: 1024,
        },
        rag: {
          enabled: true,
          vector_collections: ['policies'],
          top_k: 15,
          similarity_threshold: 0.7,
          hybrid_bm25: true,
        },
        vector_db: {
          ef_search: 256,
          score_normalization: true,
        },
        query_type: 'rag',
      };

      component.initialConfig = initialConfig;
      component.ngOnInit();

      expect(component.configForm.get('llm_model')?.value).toBe('gpt-4o');
      expect(component.configForm.get('top_k')?.value).toBe(15);
      expect(component.configForm.get('hybrid_bm25')?.value).toBe(true);
    });

    it('should reset to defaults', () => {
      component.configForm.patchValue({
        llm_model: 'gpt-4o',
        top_k: 50,
      });

      component.resetToDefaults();

      expect(component.configForm.get('llm_model')?.value).toBe('gpt-4o-mini');
      expect(component.configForm.get('top_k')?.value).toBe(10);
    });
  });

  // ========================================================================
  // RAG Configuration Tests
  // ========================================================================

  describe('RAG Configuration', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should have default vector collections for rag mode', () => {
      component.mode = 'rag';
      fixture.detectChanges();

      // RAG mode has default collections
      expect(component.configForm.get('vector_collections')?.value).toEqual([
        'documents',
      ]);
    });

    it('should have default vector collections for semantic mode', () => {
      component.mode = 'semantic';
      fixture.detectChanges();

      // Semantic mode also has default collections
      expect(component.configForm.get('vector_collections')?.value).toEqual([
        'documents',
      ]);
    });

    it('should validate vector collections required', () => {
      component.configForm.patchValue({
        vector_collections: [],
      });

      expect(component.configForm.get('vector_collections')?.valid).toBe(false);
    });

    it('should validate top_k range', () => {
      const topKControl = component.configForm.get('top_k');

      topKControl?.setValue(0);
      expect(topKControl?.hasError('min')).toBe(true);

      topKControl?.setValue(150);
      expect(topKControl?.hasError('max')).toBe(true);

      topKControl?.setValue(50);
      expect(topKControl?.valid).toBe(true);
    });
  });

  // ========================================================================
  // UI Actions Tests
  // ========================================================================

  describe('UI Actions', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should toggle expanded state', () => {
      fixture.detectChanges();

      // Record initial state and toggle
      const initialState = component.isExpanded;
      component.toggleExpanded();

      // State should be inverted
      expect(component.isExpanded).toBe(!initialState);

      // Clean up localStorage that was set during toggle
      localStorage.removeItem('paramConfigExpanded');
    });

    it('should emit execute event', () => {
      const spy = jest.spyOn(component.execute, 'emit');

      component.onExecute();

      expect(spy).toHaveBeenCalled();
    });

    it('should not execute when form invalid', () => {
      const spy = jest.spyOn(component.execute, 'emit');

      component.configForm.patchValue({
        llm_model: '', // Invalid - required
      });

      component.onExecute();

      expect(spy).not.toHaveBeenCalled();
    });
  });

  // ========================================================================
  // LocalStorage Tests
  // ========================================================================

  describe('LocalStorage', () => {
    it('should have isExpanded property', () => {
      fixture.detectChanges();

      // Component should have isExpanded property
      expect(component.isExpanded).toBeDefined();
      expect(typeof component.isExpanded).toBe('boolean');
    });

    it('should toggle isExpanded on toggleExpanded()', () => {
      fixture.detectChanges();

      const initialValue = component.isExpanded;
      component.toggleExpanded();

      expect(component.isExpanded).toBe(!initialValue);

      // Toggle back
      component.toggleExpanded();
      expect(component.isExpanded).toBe(initialValue);
    });
  });

  // ========================================================================
  // Template Helpers Tests
  // ========================================================================

  describe('Template Helpers', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should return correct isCustomPreset', () => {
      component.configForm.patchValue({
        sampling_preset: SamplingPreset.CUSTOM,
      });
      expect(component.isCustomPreset).toBe(true);

      component.configForm.patchValue({
        sampling_preset: SamplingPreset.BALANCED,
      });
      expect(component.isCustomPreset).toBe(false);
    });

    it('should return correct vector_collections value', () => {
      component.configForm.patchValue({
        vector_collections: ['policies'],
      });
      expect(component.configForm.get('vector_collections')?.value).toEqual([
        'policies',
      ]);

      component.configForm.patchValue({
        vector_collections: [],
      });
      expect(component.configForm.get('vector_collections')?.value).toEqual([]);
    });
  });
});
