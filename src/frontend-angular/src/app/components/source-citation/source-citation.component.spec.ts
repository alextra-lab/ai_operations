import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SourceMetadata } from '../../api/models/use-case.models';
import { SourceCitationComponent } from './source-citation.component';

describe('SourceCitationComponent', () => {
  let component: SourceCitationComponent;
  let fixture: ComponentFixture<SourceCitationComponent>;

  const mockSource: SourceMetadata = {
    document_id: 'test-doc-123',
    title: 'Test Document',
    source: 'Document Library',
    similarity_score: 0.85,
    chunk_index: 0,
    document_type: 'pdf',
    classification: 'internal',
    created_at: '2025-01-01T00:00:00Z',
    chunk_text: 'This is a test chunk of content that should be displayed.',
    content: 'This is a test chunk of content that should be displayed.',
    author: 'Test Author',
    page_number: 1,
    url: 'https://example.com/doc.pdf',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SourceCitationComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SourceCitationComponent);
    component = fixture.componentInstance;
    component.source = mockSource;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('hasAuthor getter', () => {
    it('should return true when author exists and has length', () => {
      component.source.author = 'John Doe';
      expect(component.hasAuthor).toBe(true);
    });

    it('should return false when author is null', () => {
      component.source.author = null as any;
      expect(component.hasAuthor).toBe(false);
    });

    it('should return false when author is undefined', () => {
      component.source.author = undefined as any;
      expect(component.hasAuthor).toBe(false);
    });

    it('should return false when author is empty string', () => {
      component.source.author = '';
      expect(component.hasAuthor).toBe(false);
    });
  });

  describe('hasUrl getter', () => {
    it('should return true when url exists and has length', () => {
      component.source.url = 'https://example.com';
      expect(component.hasUrl).toBe(true);
    });

    it('should return false when url is null', () => {
      component.source.url = null as any;
      expect(component.hasUrl).toBe(false);
    });

    it('should return false when url is undefined', () => {
      component.source.url = undefined as any;
      expect(component.hasUrl).toBe(false);
    });

    it('should return false when url is empty string', () => {
      component.source.url = '';
      expect(component.hasUrl).toBe(false);
    });
  });

  describe('hasClassification getter', () => {
    it('should return true when classification exists and has length', () => {
      component.source.classification = 'internal';
      expect(component.hasClassification).toBe(true);
    });

    it('should return false when classification is null', () => {
      component.source.classification = null as any;
      expect(component.hasClassification).toBe(false);
    });

    it('should return false when classification is undefined', () => {
      component.source.classification = undefined as any;
      expect(component.hasClassification).toBe(false);
    });

    it('should return false when classification is empty string', () => {
      component.source.classification = '';
      expect(component.hasClassification).toBe(false);
    });
  });

  describe('hasPageNumber getter', () => {
    it('should return true when page_number is defined', () => {
      component.source.page_number = 1;
      expect(component.hasPageNumber).toBe(true);
    });

    it('should return false when page_number is undefined', () => {
      component.source.page_number = undefined as any;
      expect(component.hasPageNumber).toBe(false);
    });
  });

  describe('formatSimilarityScore', () => {
    it('should format similarity score as percentage', () => {
      expect(component.formatSimilarityScore(0.85)).toBe('85.0%');
      expect(component.formatSimilarityScore(0.123)).toBe('12.3%');
      expect(component.formatSimilarityScore(1.0)).toBe('100.0%');
    });

    it('should handle null values', () => {
      expect(component.formatSimilarityScore(null as any)).toBe('N/A');
    });

    it('should handle NaN values', () => {
      expect(component.formatSimilarityScore(NaN)).toBe('N/A');
    });
  });

  describe('formatDate', () => {
    it('should format valid ISO date string', () => {
      const result = component.formatDate('2025-01-01T00:00:00Z');
      expect(result).toContain('2025');
    });

    it('should return original string on invalid date', () => {
      const invalidDate = 'invalid-date';
      expect(component.formatDate(invalidDate)).toBe(invalidDate);
    });
  });

  describe('calculateRelevanceScore', () => {
    it('should set relevanceScore from similarity_score', () => {
      component.source.similarity_score = 0.75;
      component.calculateRelevanceScore();
      expect(component.relevanceScore).toBe(0.75);
    });

    it('should default to 0 when similarity_score is null', () => {
      component.source.similarity_score = null as any;
      component.calculateRelevanceScore();
      expect(component.relevanceScore).toBe(0);
    });
  });

  describe('updateConfidenceLevel', () => {
    it('should set high confidence for score >= 0.8', () => {
      component.source.similarity_score = 0.85;
      component.updateConfidenceLevel();
      expect(component.confidenceLevel).toBe('high');
      expect(component.confidenceClass).toBe('high-confidence');
    });

    it('should set medium confidence for score >= 0.6', () => {
      component.source.similarity_score = 0.65;
      component.updateConfidenceLevel();
      expect(component.confidenceLevel).toBe('medium');
      expect(component.confidenceClass).toBe('medium-confidence');
    });

    it('should set low confidence for score < 0.6', () => {
      component.source.similarity_score = 0.5;
      component.updateConfidenceLevel();
      expect(component.confidenceLevel).toBe('low');
      expect(component.confidenceClass).toBe('low-confidence');
    });
  });

  describe('setDocumentTypeIcon', () => {
    it('should set correct icon for PDF', () => {
      component.source.document_type = 'pdf';
      component.setDocumentTypeIcon();
      expect(component.documentTypeIcon).toBe('picture_as_pdf');
    });

    it('should set correct icon for DOC', () => {
      component.source.document_type = 'docx';
      component.setDocumentTypeIcon();
      expect(component.documentTypeIcon).toBe('description');
    });

    it('should set default icon for unknown types', () => {
      component.source.document_type = 'unknown';
      component.setDocumentTypeIcon();
      expect(component.documentTypeIcon).toBe('insert_drive_file');
    });
  });
});
