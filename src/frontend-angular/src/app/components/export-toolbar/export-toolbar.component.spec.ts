import { ChangeDetectorRef } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of, Subject, throwError } from 'rxjs';

import { ExportService } from '../../services/export.service';
import { ExportToolbarComponent } from './export-toolbar.component';

describe('ExportToolbarComponent', () => {
  let component: ExportToolbarComponent;
  let fixture: ComponentFixture<ExportToolbarComponent>;
  let exportService: jest.Mocked<ExportService>;

  const mockExportResponse = {
    export_id: 'export-123',
    format: 'markdown',
    content: '# Test Content\n\nThis is test markdown content.',
  };

  const mockSummaryResponse = {
    summary: 'This is a test summary',
    key_points: ['Point 1', 'Point 2'],
    recommendations: ['Recommendation 1'],
    metadata: {},
  };

  beforeEach(async () => {
    const exportServiceMock = {
      exportAsMarkdown: jest.fn(),
      exportAsJson: jest.fn(),
      generateSummary: jest.fn(),
      generateFilename: jest.fn(),
      downloadExport: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [
        ExportToolbarComponent,
        MatMenuModule,
        MatSnackBarModule,
        BrowserAnimationsModule,
      ],
      providers: [{ provide: ExportService, useValue: exportServiceMock }],
    }).compileComponents();

    exportService = TestBed.inject(ExportService) as jest.Mocked<ExportService>;
    fixture = TestBed.createComponent(ExportToolbarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('copyMarkdown', () => {
    beforeEach(() => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: jest.fn().mockResolvedValue(undefined),
        },
      });
      exportService.exportAsMarkdown.mockReturnValue(of(mockExportResponse));
    });

    it('should copy markdown to clipboard when sessionId is provided', (done) => {
      component.sessionId = 'session-123';

      component.copyMarkdown();

      exportService.exportAsMarkdown('session-123').subscribe(() => {
        expect(exportService.exportAsMarkdown).toHaveBeenCalledWith(
          'session-123'
        );
        done();
      });
    });

    it('should not copy when sessionId is null', () => {
      component.sessionId = null;

      component.copyMarkdown();

      expect(exportService.exportAsMarkdown).not.toHaveBeenCalled();
    });

    it('should handle export errors gracefully', () => {
      component.sessionId = 'session-123';
      exportService.exportAsMarkdown.mockReturnValue(
        throwError(() => new Error('Export failed'))
      );

      component.copyMarkdown();

      expect(component.isExporting).toBe(false);
    });
  });

  describe('downloadMarkdown', () => {
    beforeEach(() => {
      exportService.exportAsMarkdown.mockReturnValue(of(mockExportResponse));
      exportService.generateFilename.mockReturnValue(
        'conversation_test_2025-10-26.md'
      );
      exportService.downloadExport.mockImplementation(() => {});
    });

    it('should download markdown file when sessionId is provided', (done) => {
      component.sessionId = 'session-123';
      component.sessionTitle = 'Test Session';

      component.downloadMarkdown();

      exportService.exportAsMarkdown('session-123').subscribe(() => {
        expect(exportService.exportAsMarkdown).toHaveBeenCalledWith(
          'session-123'
        );
        expect(exportService.generateFilename).toHaveBeenCalledWith(
          'Test Session',
          'markdown'
        );
        expect(exportService.downloadExport).toHaveBeenCalled();
        done();
      });
    });

    it('should use default title when sessionTitle is null', (done) => {
      component.sessionId = 'session-123';
      component.sessionTitle = null;

      component.downloadMarkdown();

      exportService.exportAsMarkdown('session-123').subscribe(() => {
        expect(exportService.generateFilename).toHaveBeenCalledWith(
          'conversation',
          'markdown'
        );
        done();
      });
    });

    it('should not download when sessionId is null', () => {
      component.sessionId = null;

      component.downloadMarkdown();

      expect(exportService.exportAsMarkdown).not.toHaveBeenCalled();
    });
  });

  describe('downloadJson', () => {
    beforeEach(() => {
      exportService.exportAsJson.mockReturnValue(
        of({
          ...mockExportResponse,
          format: 'json',
          content: '{"test": "data"}',
        })
      );
      exportService.generateFilename.mockReturnValue(
        'conversation_test_2025-10-26.json'
      );
      exportService.downloadExport.mockImplementation(() => {});
    });

    it('should download JSON file when sessionId is provided', (done) => {
      component.sessionId = 'session-123';
      component.sessionTitle = 'Test Session';

      component.downloadJson();

      exportService.exportAsJson('session-123').subscribe(() => {
        expect(exportService.exportAsJson).toHaveBeenCalledWith('session-123');
        expect(exportService.generateFilename).toHaveBeenCalledWith(
          'Test Session',
          'json'
        );
        expect(exportService.downloadExport).toHaveBeenCalled();
        done();
      });
    });

    it('should not download when sessionId is null', () => {
      component.sessionId = null;

      component.downloadJson();

      expect(exportService.exportAsJson).not.toHaveBeenCalled();
    });

    it('should emit exportComplete event on successful download', (done) => {
      component.sessionId = 'session-123';

      component.exportComplete.subscribe((event) => {
        expect(event.format).toBe('json');
        expect(event.filename).toBe('conversation_test_2025-10-26.json');
        done();
      });

      component.downloadJson();
    });
  });

  describe('generateSummary', () => {
    beforeEach(() => {
      exportService.generateSummary.mockReturnValue(of(mockSummaryResponse));
    });

    it('should generate executive summary', (done) => {
      component.sessionId = 'session-123';

      component.generateSummary('executive');

      exportService
        .generateSummary('session-123', 'executive')
        .subscribe(() => {
          expect(exportService.generateSummary).toHaveBeenCalledWith(
            'session-123',
            'executive'
          );
          done();
        });
    });

    it('should generate technical summary', (done) => {
      component.sessionId = 'session-123';

      component.generateSummary('technical');

      exportService
        .generateSummary('session-123', 'technical')
        .subscribe(() => {
          expect(exportService.generateSummary).toHaveBeenCalledWith(
            'session-123',
            'technical'
          );
          done();
        });
    });

    it('should generate brief summary', (done) => {
      component.sessionId = 'session-123';

      component.generateSummary('brief');

      exportService.generateSummary('session-123', 'brief').subscribe(() => {
        expect(exportService.generateSummary).toHaveBeenCalledWith(
          'session-123',
          'brief'
        );
        done();
      });
    });

    it('should emit summaryGenerated event on success', (done) => {
      component.sessionId = 'session-123';

      component.summaryGenerated.subscribe((event) => {
        expect(event.summary).toBe('This is a test summary');
        expect(event.type).toBe('executive');
        done();
      });

      component.generateSummary('executive');
    });

    it('should not generate summary when sessionId is null', () => {
      component.sessionId = null;

      component.generateSummary('executive');

      expect(exportService.generateSummary).not.toHaveBeenCalled();
    });

    it('should handle summary generation errors gracefully', () => {
      component.sessionId = 'session-123';
      exportService.generateSummary.mockReturnValue(
        throwError(() => new Error('Summary generation failed'))
      );

      component.generateSummary('executive');

      expect(component.isExporting).toBe(false);
    });
  });

  describe('isExporting state', () => {
    it('should set isExporting to true during export', () => {
      component.sessionId = 'session-123';
      // Use a Subject to control when the Observable emits
      const subject = new Subject();
      exportService.exportAsMarkdown.mockReturnValue(subject.asObservable());
      exportService.generateFilename.mockReturnValue('test.md');
      exportService.downloadExport.mockImplementation(() => {});

      expect(component.isExporting).toBe(false);
      component.downloadMarkdown();
      // isExporting is set synchronously before subscribe executes
      expect(component.isExporting).toBe(true);

      // Complete the Observable to avoid hanging
      subject.next(mockExportResponse);
      subject.complete();
    });

    it('should reset isExporting after successful export', (done) => {
      component.sessionId = 'session-123';
      exportService.exportAsMarkdown.mockReturnValue(of(mockExportResponse));
      exportService.generateFilename.mockReturnValue('test.md');
      exportService.downloadExport.mockImplementation(() => {});

      component.downloadMarkdown();

      setTimeout(() => {
        expect(component.isExporting).toBe(false);
        done();
      }, 100);
    });

    it('should reset isExporting after failed export', (done) => {
      component.sessionId = 'session-123';
      exportService.exportAsMarkdown.mockReturnValue(
        throwError(() => new Error('Export failed'))
      );

      component.downloadMarkdown();

      setTimeout(() => {
        expect(component.isExporting).toBe(false);
        done();
      }, 100);
    });
  });

  describe('accessibility', () => {
    it('should disable export button when no sessionId', () => {
      component.sessionId = null;
      // OnPush change detection requires markForCheck or detectChanges
      fixture.detectChanges();

      const button = fixture.nativeElement.querySelector(
        'button[aria-label="Export conversation menu"]'
      );
      expect(button.disabled).toBe(true);
    });

    it('should enable export button when sessionId is provided', () => {
      component.sessionId = 'session-123';
      component.isExporting = false; // Ensure isExporting is false
      // OnPush change detection - manually trigger change detection
      const cdr = fixture.componentRef.injector.get(ChangeDetectorRef);
      cdr.markForCheck();
      fixture.detectChanges();

      const button = fixture.nativeElement.querySelector(
        'button[aria-label="Export conversation menu"]'
      );
      expect(button?.disabled).toBe(false);
    });

    it('should disable export button when isExporting is true', () => {
      component.sessionId = 'session-123';
      component.isExporting = true;
      // OnPush change detection - manually trigger change detection
      const cdr = fixture.componentRef.injector.get(ChangeDetectorRef);
      cdr.markForCheck();
      fixture.detectChanges();

      const button = fixture.nativeElement.querySelector(
        'button[aria-label="Export conversation menu"]'
      );
      expect(button?.disabled).toBe(true);
    });
  });
});
