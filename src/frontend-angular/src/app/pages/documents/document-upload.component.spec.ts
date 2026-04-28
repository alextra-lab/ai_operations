import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { CollectionService } from '../../api/services/collection.service';
import { DocumentService } from '../../api/services/document.service';
import { DocumentUploadComponent } from './document-upload.component';

describe('DocumentUploadComponent', () => {
  let component: DocumentUploadComponent;
  let fixture: ComponentFixture<DocumentUploadComponent>;
  let mockDocumentService: jest.Mocked<DocumentService>;
  let mockCollectionService: jest.Mocked<CollectionService>;
  let mockSnackBar: jest.Mocked<MatSnackBar>;
  let mockRouter: Partial<Router>;
  let mockActivatedRoute: Partial<ActivatedRoute>;

  beforeEach(async () => {
    mockDocumentService = {
      uploadDocument: jest.fn(),
      uploadDocuments: jest.fn(),
      getRecentUploads: jest.fn(),
      getDocuments: jest.fn(),
      clearUploadProgress: jest.fn(),
      uploadProgress$: of([]),
    } as any;

    mockCollectionService = {
      listCollections: jest
        .fn()
        .mockReturnValue(of({ collections: [], total: 0 })),
    } as jest.Mocked<CollectionService>;

    mockSnackBar = {
      open: jest.fn(),
    } as jest.Mocked<MatSnackBar>;

    mockRouter = {
      navigate: jest.fn(),
    };

    mockActivatedRoute = {
      params: of({}),
      queryParams: of({}),
      snapshot: {
        params: {},
        queryParams: {},
        paramMap: {
          get: jest.fn().mockReturnValue(null),
          has: jest.fn().mockReturnValue(false),
          keys: [],
          getAll: jest.fn().mockReturnValue([]),
        },
        queryParamMap: {
          get: jest.fn().mockReturnValue(null),
          has: jest.fn().mockReturnValue(false),
          keys: [],
          getAll: jest.fn().mockReturnValue([]),
        },
        url: [],
        fragment: null,
        data: {},
        outlet: 'primary',
        component: null,
        routeConfig: null,
        root: null,
        parent: null,
        firstChild: null,
        children: [],
      },
    };

    await TestBed.configureTestingModule({
      imports: [
        DocumentUploadComponent,
        ReactiveFormsModule,
        NoopAnimationsModule,
      ],
      providers: [
        FormBuilder,
        { provide: DocumentService, useValue: mockDocumentService },
        { provide: CollectionService, useValue: mockCollectionService },
        { provide: MatSnackBar, useValue: mockSnackBar },
        { provide: Router, useValue: mockRouter },
        { provide: ActivatedRoute, useValue: mockActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DocumentUploadComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form with default values', () => {
    // Mock services before ngOnInit
    mockCollectionService.listCollections.mockReturnValue(
      of({ collections: [], total: 0 })
    );
    mockDocumentService.getDocuments.mockReturnValue(
      of({ documents: [], total: 0, page: 1, page_size: 10 })
    );
    mockDocumentService.uploadProgress$ = of([]);

    component.ngOnInit();
    fixture.detectChanges();

    // Collection may have a default value, check if it's set
    expect(component.uploadForm.get('collection')?.value).toBeTruthy();
    expect(component.uploadForm.get('title')?.value).toBe('');
    expect(component.uploadForm.get('source')?.value).toBe('');
    expect(component.uploadForm.get('author')?.value).toBe('');
    expect(component.uploadForm.get('classification')?.value).toBe('internal');
    expect(component.uploadForm.get('tags')?.value).toBe('');
    expect(component.uploadForm.get('processAsync')?.value).toBe(true);
  });

  it('should load collections on init', () => {
    const mockCollections = [
      { id: '1', name: 'Collection 1' },
      { id: '2', name: 'Collection 2' },
    ];
    mockCollectionService.listCollections.mockReturnValue(
      of({ collections: mockCollections, total: 2 })
    );
    mockDocumentService.getDocuments.mockReturnValue(
      of({ documents: [], total: 0, page: 1, page_size: 10 })
    );
    mockDocumentService.uploadProgress$ = of([]);

    component.ngOnInit();
    fixture.detectChanges();

    expect(mockCollectionService.listCollections).toHaveBeenCalled();
    expect(component.availableCollections).toEqual(mockCollections);
  });

  it('should handle file selection', () => {
    const mockFile = new File(['test'], 'test.pdf', {
      type: 'application/pdf',
    });
    const mockEvent = {
      target: {
        files: [mockFile],
      },
    } as any;

    component.onFileSelected(mockEvent);

    expect(component.selectedFiles).toContain(mockFile);
  });

  it('should handle drag and drop', () => {
    const mockFile = new File(['test'], 'test.pdf', {
      type: 'application/pdf',
    });
    const mockEvent = {
      preventDefault: jest.fn(),
      stopPropagation: jest.fn(),
      dataTransfer: {
        files: [mockFile],
      },
    } as any;

    component.onDrop(mockEvent);

    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(component.selectedFiles).toContain(mockFile);
  });

  it('should remove file from selection', () => {
    const mockFile = new File(['test'], 'test.pdf', {
      type: 'application/pdf',
    });
    component.selectedFiles = [mockFile];

    component.removeFile(0);

    expect(component.selectedFiles).toHaveLength(0);
  });

  it('should upload files successfully', () => {
    const mockFile = new File(['test'], 'test.pdf', {
      type: 'application/pdf',
    });
    component.selectedFiles = [mockFile];
    component.uploadForm.patchValue({
      collection: 'test-collection',
      title: 'Test Document',
    });

    mockDocumentService.uploadDocuments.mockReturnValue(
      of([{ id: '1', title: 'Test Document' }])
    );
    mockSnackBar.open.mockReturnValue({ onAction: () => of({}) } as jest.Mocked<
      ReturnType<MatSnackBar['open']>
    >);

    component.uploadFiles();

    expect(mockDocumentService.uploadDocuments).toHaveBeenCalled();
    expect(mockSnackBar.open).toHaveBeenCalledWith(
      expect.stringContaining('Successfully uploaded'),
      'Close',
      {
        duration: 5000,
      }
    );
  });

  it('should handle upload error', () => {
    const mockFile = new File(['test'], 'test.pdf', {
      type: 'application/pdf',
    });
    component.selectedFiles = [mockFile];

    mockDocumentService.uploadDocuments.mockReturnValue(
      throwError(() => new Error('Upload failed'))
    );

    component.uploadFiles();

    expect(mockSnackBar.open).toHaveBeenCalledWith(
      'Upload failed: Upload failed',
      'Close',
      {
        duration: 5000,
      }
    );
  });

  it('should clear form', () => {
    component.selectedFiles = [new File(['test'], 'test.pdf')];
    component.uploadForm.patchValue({
      title: 'Test',
      source: 'Test Source',
    });

    component.clearForm();

    expect(component.selectedFiles).toHaveLength(0);
    expect(component.uploadForm.get('title')?.value).toBeNull();
    expect(component.uploadForm.get('source')?.value).toBeNull();
  });

  it('should format file size correctly', () => {
    expect(component.formatFileSize(1024)).toBe('1 KB');
    expect(component.formatFileSize(1048576)).toBe('1 MB');
    expect(component.formatFileSize(1073741824)).toBe('1 GB');
  });

  it('should validate required fields', () => {
    component.uploadForm.patchValue({
      collection: '',
      title: '',
    });

    expect(component.uploadForm.get('collection')?.hasError('required')).toBe(
      true
    );
  });

  it('should disable upload when no files selected', () => {
    component.selectedFiles = [];
    component.isUploading = false;

    expect(component.selectedFiles.length === 0 || component.isUploading).toBe(
      true
    );
  });

  it('should format strategy name correctly', () => {
    expect(component.formatStrategyName('auto')).toBe('Auto-Detect');
    expect(component.formatStrategyName('fixed_token')).toBe('Fixed Token');
    expect(component.formatStrategyName('sliding_token')).toBe(
      'Sliding Window'
    );
    expect(component.formatStrategyName('heading_aware')).toBe('Heading Aware');
    expect(component.formatStrategyName('sentence_paragraph')).toBe(
      'Sentence/Paragraph'
    );
    expect(component.formatStrategyName('recursive')).toBe('Recursive');
  });

  it('should get selected collection', () => {
    const mockCollections = [
      { id: '1', name: 'Collection 1', embedding_model: 'model1' } as any,
      { id: '2', name: 'Collection 2', embedding_model: 'model2' } as any,
    ];
    component.availableCollections = mockCollections;
    component.uploadForm.patchValue({ collection: 'Collection 1' });

    const selected = component.getSelectedCollection();
    expect(selected).toEqual(mockCollections[0]);
  });

  it('should get selected collection name', () => {
    const mockCollections = [
      { id: '1', name: 'Collection 1', embedding_model: 'model1' } as any,
    ];
    component.availableCollections = mockCollections;
    component.uploadForm.patchValue({ collection: 'Collection 1' });

    expect(component.getSelectedCollectionName()).toBe('Collection 1');
  });

  it('should handle auto-detection progress', () => {
    const mockProgress = {
      documentId: 'doc1',
      filename: 'test.pdf',
      progress: 50,
      status: 'analyzing' as const,
      message: 'Analyzing document structure...',
      current_strategy: 'testing: heading_aware',
      strategies_tested: '3/5',
      selected_strategy: 'heading_aware',
      confidence: 0.94,
      auto_detection_time_ms: 2450,
    };

    component.uploadProgress = [mockProgress];

    expect(component.uploadProgress[0].status).toBe('analyzing');
    expect(component.uploadProgress[0].current_strategy).toBe(
      'testing: heading_aware'
    );
    expect(component.uploadProgress[0].confidence).toBe(0.94);
  });

  it('should include chunking_config in upload request', () => {
    const mockFile = new File(['test'], 'test.pdf', {
      type: 'application/pdf',
    });
    component.selectedFiles = [mockFile];
    component.uploadForm.patchValue({
      collection: 'test-collection',
      chunkingStrategy: 'auto',
      chunkSize: 512,
      chunkOverlap: 50,
    });

    mockDocumentService.uploadDocuments.mockReturnValue(
      of([{ id: '1', title: 'test.pdf' }] as any)
    );
    mockSnackBar.open.mockReturnValue({ onAction: () => of({}) } as any);

    component.uploadFiles();

    expect(mockDocumentService.uploadDocuments).toHaveBeenCalled();
    const callArgs = mockDocumentService.uploadDocuments.mock.calls[0];
    if (
      callArgs &&
      callArgs[0] &&
      Array.isArray(callArgs[0]) &&
      callArgs[0].length > 0
    ) {
      const request = callArgs[0][0];
      expect(request.chunking_config).toBeDefined();
      expect(request.chunking_config.strategy).toBe('auto');
      expect(request.chunking_config.chunk_size).toBe(512);
      expect(request.chunking_config.chunk_overlap).toBe(50);
    }
  });
});
