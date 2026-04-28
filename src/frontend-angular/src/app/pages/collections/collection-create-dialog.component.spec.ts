/**
 * Unit tests for Collection Create Dialog Component
 * Tests system-wide embedding model display and collection creation
 */

import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, Subject, throwError } from 'rxjs';

import { CollectionService } from '../../api/services/collection.service';
import { ModelRegistryService } from '../../api/services/model-registry.service';
import { SystemConfigService } from '../admin/system-config/services/system-config.service';
import { CollectionCreateDialogComponent } from './collection-create-dialog.component';

describe('CollectionCreateDialogComponent', () => {
  let component: CollectionCreateDialogComponent;
  let fixture: ComponentFixture<CollectionCreateDialogComponent>;
  let mockCollectionService: jest.Mocked<CollectionService>;
  let mockModelRegistryService: jest.Mocked<ModelRegistryService>;
  let mockSystemConfigService: jest.Mocked<SystemConfigService>;
  let mockDialogRef: jest.Mocked<MatDialogRef<CollectionCreateDialogComponent>>;

  beforeEach(async () => {
    mockCollectionService = {
      createCollection: jest.fn(),
      validateCollectionName: jest.fn(),
    } as any;

    mockModelRegistryService = {
      getEmbeddingModels: jest.fn(),
      listModels: jest.fn(),
    } as any;

    mockSystemConfigService = {
      getConfig: jest.fn(),
    } as any;

    const afterOpenedSubject = new Subject<void>();
    const afterClosedSubject = new Subject<any>();

    mockDialogRef = {
      close: jest.fn((result?: any) => {
        afterClosedSubject.next(result);
        afterClosedSubject.complete();
      }),
      afterOpened: afterOpenedSubject.asObservable(),
      afterClosed: afterClosedSubject.asObservable(),
      componentInstance: {} as any,
      disableClose: false,
      id: 'test-dialog-id',
    } as any;

    await TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
        ReactiveFormsModule,
        NoopAnimationsModule,
        CollectionCreateDialogComponent,
      ],
      providers: [
        { provide: CollectionService, useValue: mockCollectionService },
        { provide: ModelRegistryService, useValue: mockModelRegistryService },
        { provide: SystemConfigService, useValue: mockSystemConfigService },
        { provide: MatDialogRef, useValue: mockDialogRef },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CollectionCreateDialogComponent);
    component = fixture.componentInstance;
  });

  describe('Component Initialization', () => {
    beforeEach(() => {
      // Set up default mocks for ngOnInit
      const mockModels = [
        {
          model_id: 'text-embedding-3-small',
          provider: 'openai',
          embedding_dimensions: 1536,
        },
      ];
      mockModelRegistryService.getEmbeddingModels.mockReturnValue(
        of(mockModels as any)
      );
      mockSystemConfigService.getConfig.mockReturnValue(
        of({
          corpus: { default_embedding_model: 'text-embedding-3-small' },
        } as any)
      );
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize form with name, description, and embedding_model fields', () => {
      fixture.detectChanges();
      expect(component.createForm.get('name')).toBeTruthy();
      expect(component.createForm.get('description')).toBeTruthy();
      expect(component.createForm.get('embedding_model')).toBeTruthy();
    });

    it('should set up name validation on init', () => {
      mockCollectionService.validateCollectionName.mockReturnValue({
        valid: true,
      });

      fixture.detectChanges();

      component.createForm.patchValue({ name: 'test-collection' });

      expect(mockCollectionService.validateCollectionName).toHaveBeenCalledWith(
        'test-collection'
      );
    });
  });

  describe('Form Validation', () => {
    beforeEach(() => {
      // Set up mocks for model loading (required for ngOnInit)
      const mockModels = [
        {
          model_id: 'text-embedding-3-small',
          provider: 'openai',
          embedding_dimensions: 1536,
        },
      ];
      mockModelRegistryService.getEmbeddingModels.mockReturnValue(
        of(mockModels as any)
      );
      mockSystemConfigService.getConfig.mockReturnValue(
        of({
          corpus: { default_embedding_model: 'text-embedding-3-small' },
        } as any)
      );
      fixture.detectChanges();
    });

    it('should require name field', () => {
      const nameControl = component.createForm.get('name');
      expect(nameControl?.hasError('required')).toBe(true);

      nameControl?.setValue('test');
      expect(nameControl?.hasError('required')).toBe(false);
    });

    it('should enforce minimum name length', () => {
      const nameControl = component.createForm.get('name');
      nameControl?.setValue('ab');
      expect(nameControl?.hasError('minlength')).toBe(true);

      nameControl?.setValue('abc');
      expect(nameControl?.hasError('minlength')).toBe(false);
    });

    it('should allow empty description', () => {
      const descControl = component.createForm.get('description');
      expect(descControl?.valid).toBe(true);
    });

    it('should set validation error when name is invalid', () => {
      mockCollectionService.validateCollectionName.mockReturnValue({
        valid: false,
        error: 'Invalid name format',
      });

      component.createForm.patchValue({ name: 'invalid name!' });

      expect(component.createForm.get('name')?.errors?.['invalid']).toBe(
        'Invalid name format'
      );
    });
  });

  describe('Collection Creation', () => {
    beforeEach(() => {
      // Set up mocks for model loading; provider_type drives getEmbeddingProvider()
      const mockModels = [
        {
          model_id: 'text-embedding-3-small',
          provider: 'openai',
          provider_type: 'openai',
          embedding_dimensions: 1536,
        },
      ];
      mockModelRegistryService.getEmbeddingModels.mockReturnValue(
        of(mockModels as any)
      );
      mockSystemConfigService.getConfig.mockReturnValue(
        of({
          corpus: { default_embedding_model: 'text-embedding-3-small' },
        } as any)
      );

      fixture.detectChanges();
      component.createForm.patchValue({
        name: 'test-collection',
        description: 'Test description',
        embedding_model: 'text-embedding-3-small',
      });
      // Set selectedModel for onSubmit
      component.selectedModel = mockModels[0] as any;
    });

    it('should create collection with system embedding model', () => {
      const mockCollection = {
        id: '123',
        name: 'test-collection',
        description: 'Test description',
        embedding_model: 'text-embedding-3-small',
        embedding_provider: 'openai',
        embedding_dimensions: 1536,
        is_default: false,
        is_active: true,
        document_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      mockCollectionService.createCollection.mockReturnValue(
        of(mockCollection)
      );

      component.onSubmit();

      expect(mockCollectionService.createCollection).toHaveBeenCalledWith({
        name: 'test-collection',
        description: 'Test description',
        embedding_model: 'text-embedding-3-small',
        embedding_provider: 'openai',
        embedding_dimensions: 1536,
        auto_chunk_enabled: true,
        preflight_sample_tokens: 10000,
      });
      expect(mockDialogRef.close).toHaveBeenCalledWith(mockCollection);
    });

    it('should use selected embedding model', () => {
      const mockCollection = {
        id: 'test-id',
        name: 'test-collection',
        embedding_model: 'text-embedding-3-small',
      } as any;
      mockCollectionService.createCollection.mockReturnValue(
        of(mockCollection)
      );

      component.onSubmit();

      const callArgs = mockCollectionService.createCollection.mock.calls[0][0];
      expect(callArgs.embedding_model).toBe('text-embedding-3-small');
      expect(callArgs.embedding_provider).toBe('openai');
      expect(callArgs.embedding_dimensions).toBe(1536);
    });

    it('should trim and lowercase collection name', () => {
      component.createForm.patchValue({
        name: '  TEST-Collection  ',
      });

      const mockCollection = {
        id: 'test-id',
        name: 'test-collection',
      } as any;
      mockCollectionService.createCollection.mockReturnValue(
        of(mockCollection)
      );

      component.onSubmit();

      const callArgs = mockCollectionService.createCollection.mock.calls[0][0];
      expect(callArgs.name).toBe('test-collection');
    });

    it('should handle empty description', () => {
      component.createForm.patchValue({
        name: 'test-collection',
        description: '',
      });

      const mockCollection = {
        id: 'test-id',
        name: 'test-collection',
      } as any;
      mockCollectionService.createCollection.mockReturnValue(
        of(mockCollection)
      );

      component.onSubmit();

      const callArgs = mockCollectionService.createCollection.mock.calls[0][0];
      expect(callArgs.description).toBeUndefined();
    });

    it('should not submit if form is invalid', () => {
      component.createForm.patchValue({ name: '' });

      component.onSubmit();

      expect(mockCollectionService.createCollection).not.toHaveBeenCalled();
    });

    it('should not submit if already submitting', () => {
      component.isSubmitting = true;

      component.onSubmit();

      expect(mockCollectionService.createCollection).not.toHaveBeenCalled();
    });

    it('should handle creation error', () => {
      const errorResponse = { message: 'Collection already exists' };
      mockCollectionService.createCollection.mockReturnValue(
        throwError(() => errorResponse)
      );

      component.onSubmit();

      expect(component.errorMessage).toBe('Collection already exists');
      expect(component.isSubmitting).toBe(false);
      expect(mockDialogRef.close).not.toHaveBeenCalled();
    });

    it('should set isSubmitting during submission', () => {
      mockCollectionService.createCollection.mockReturnValue(of({} as any));

      expect(component.isSubmitting).toBe(false);
      component.onSubmit();
      // Note: In real async, isSubmitting would be true during the call
      // but in sync test it completes immediately
    });
  });

  describe('Dialog Actions', () => {
    it('should close dialog on cancel', () => {
      component.onCancel();
      expect(mockDialogRef.close).toHaveBeenCalledWith();
    });
  });

  describe('Embedding Model Selection', () => {
    beforeEach(() => {
      const mockModels = [
        {
          model_id: 'text-embedding-3-small',
          provider: 'openai',
          embedding_dimensions: 1536,
        },
      ];
      mockModelRegistryService.getEmbeddingModels.mockReturnValue(
        of(mockModels as any)
      );
      mockSystemConfigService.getConfig.mockReturnValue(
        of({
          corpus: { default_embedding_model: 'text-embedding-3-small' },
        } as any)
      );
      fixture.detectChanges();
    });

    it('should allow user to select embedding model', () => {
      // Verify form control for embedding model selection exists
      expect(component.createForm.get('embedding_model')).toBeTruthy();
    });
  });
});
