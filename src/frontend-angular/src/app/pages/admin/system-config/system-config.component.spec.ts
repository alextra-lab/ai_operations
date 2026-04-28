/**
 * System Configuration Component Unit Tests
 */

import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarRef } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, Subject, throwError } from 'rxjs';

import { SystemConfigFull } from './models/system-config.models';
import { SystemConfigService } from './services/system-config.service';
import { SystemConfigComponent } from './system-config.component';

describe('SystemConfigComponent', () => {
  let component: SystemConfigComponent;
  let fixture: ComponentFixture<SystemConfigComponent>;
  let mockConfigService: jest.Mocked<SystemConfigService>;
  let mockDialog: jest.Mocked<MatDialog>;
  let mockSnackBar: jest.Mocked<MatSnackBar>;

  const mockConfig: SystemConfigFull = {
    corpus: {
      chunk_size: 512,
      chunk_overlap: 50,
      default_embedding_model: 'test-model',
      max_document_size_mb: 50,
      allowed_file_types: ['pdf', 'txt'],
    },
    auth: {
      session_timeout_minutes: 60,
      refresh_token_ttl_days: 30,
      password_policy: {
        min_length: 8,
        require_uppercase: true,
        require_lowercase: true,
        require_numbers: true,
        require_special: false,
      },
    },
    features: {
      multi_collection_search: false,
      export_functionality: true,
      conversation_cache: true,
      telemetry_enabled: true,
    },
    system: {
      log_level: 'INFO' as const,
      max_workers: 4,
      request_timeout_seconds: 30,
      enable_debug_endpoints: false,
    },
  };

  beforeEach(async () => {
    mockConfigService = {
      getConfig: jest.fn().mockReturnValue(of(mockConfig)),
      getConfigSection: jest.fn(),
      updateConfigSection: jest.fn(),
      getConfigSchema: jest.fn().mockReturnValue(of({ properties: {} })),
      exportConfig: jest.fn(),
      importConfig: jest.fn(),
      validateConfigYaml: jest.fn(),
    } as any;

    const afterOpenedSubject = new Subject<MatDialogRef<any>>();
    const afterAllClosedSubject = new Subject<void>();
    const openDialogsArray: any[] = [];

    const mockDialogRef: Partial<MatDialogRef<any>> = {
      afterClosed: jest.fn(() => of(undefined)),
      close: jest.fn(),
      afterOpened: afterOpenedSubject.asObservable(),
    };

    mockDialog = {
      open: jest.fn((component: any, config?: any) => {
        const dialogRef = mockDialogRef as MatDialogRef<any>;
        openDialogsArray.push(dialogRef);
        // Trigger afterOpened subject
        setTimeout(() => afterOpenedSubject.next(dialogRef), 0);
        return dialogRef;
      }),
      _openDialogs: openDialogsArray,
      afterAllClosed: afterAllClosedSubject.asObservable(),
      afterOpened: afterOpenedSubject.asObservable(),
      openDialogs: openDialogsArray,
      _getAfterAllClosed: jest.fn(() => afterAllClosedSubject),
      _afterAllClosedAtThisLevel: afterAllClosedSubject,
      _afterOpened: afterOpenedSubject,
    } as any;

    const mockSnackBarRef: Partial<MatSnackBarRef<any>> = {
      dismiss: jest.fn(),
    };

    mockSnackBar = {
      open: jest.fn(() => mockSnackBarRef as MatSnackBarRef<any>),
    } as any;

    await TestBed.configureTestingModule({
      imports: [
        SystemConfigComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: SystemConfigService, useValue: mockConfigService },
        { provide: MatDialog, useValue: mockDialog },
        { provide: MatSnackBar, useValue: mockSnackBar },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SystemConfigComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit', () => {
    it('should load configuration on init', () => {
      mockConfigService.getConfig.mockReturnValue(of(mockConfig));

      component.ngOnInit();

      expect(mockConfigService.getConfig).toHaveBeenCalled();
      expect(component.config).toEqual(mockConfig);
      expect(component.isLoading).toBe(false);
    });

    it('should handle load error', (done) => {
      mockConfigService.getConfig.mockReturnValue(
        throwError(() => new Error('Load failed'))
      );
      const snackBarSpy = jest.spyOn(component['snackBar'], 'open');

      component.ngOnInit();

      setTimeout(() => {
        expect(component.error).toBe('Failed to load configuration');
        expect(component.isLoading).toBe(false);
        expect(snackBarSpy).toHaveBeenCalledWith(
          'Failed to load configuration',
          'Close',
          { duration: 5000 }
        );
        snackBarSpy.mockRestore();
        done();
      }, 100);
    });
  });

  describe('getSectionConfig', () => {
    it('should return section configuration', () => {
      component.config = mockConfig;

      const corpusConfig = component.getSectionConfig('corpus');

      expect(corpusConfig).toEqual(mockConfig.corpus);
    });

    it('should return null if no config', () => {
      component.config = null;

      const corpusConfig = component.getSectionConfig('corpus');

      expect(corpusConfig).toBeNull();
    });
  });

  describe('onSectionChange', () => {
    it('should update section and mark as modified', () => {
      component.config = { ...mockConfig };
      const newCorpusConfig = {
        ...mockConfig.corpus,
        chunk_size: 1024,
      };

      component.onSectionChange('corpus', newCorpusConfig);

      expect(component.config.corpus).toEqual(newCorpusConfig);
      expect(component.modifiedSections.has('corpus')).toBe(true);
    });
  });

  describe('saveAll', () => {
    it('should save all modified sections', (done) => {
      component.config = mockConfig;
      component.modifiedSections.add('corpus');

      mockConfigService.updateConfigSection.mockReturnValue(
        of({
          section: 'corpus',
          config: mockConfig.corpus,
          updated_at: '2025-10-27T12:00:00Z',
          restart_required: true,
        })
      );

      component.saveAll();

      setTimeout(() => {
        expect(mockConfigService.updateConfigSection).toHaveBeenCalledWith(
          'corpus',
          mockConfig.corpus
        );
        expect(component.modifiedSections.size).toBe(0);
        expect(component.restartRequired).toBe(true);
        done();
      }, 100);
    });

    it('should show message when no changes', () => {
      component.modifiedSections.clear();
      const snackBarSpy = jest.spyOn(component['snackBar'], 'open');

      component.saveAll();

      expect(snackBarSpy).toHaveBeenCalledWith('No changes to save', 'Close', {
        duration: 3000,
      });
      snackBarSpy.mockRestore();
    });
  });

  describe('resetAll', () => {
    it('should reload configuration and clear changes', () => {
      component.modifiedSections.add('corpus');
      mockConfigService.getConfig.mockReturnValue(of(mockConfig));
      const snackBarSpy = jest.spyOn(component['snackBar'], 'open');

      component.resetAll();

      expect(component.modifiedSections.size).toBe(0);
      expect(mockConfigService.getConfig).toHaveBeenCalled();
      expect(snackBarSpy).toHaveBeenCalledWith('Configuration reset', 'Close', {
        duration: 3000,
      });
      snackBarSpy.mockRestore();
    });
  });

  describe('openExportDialog', () => {
    it('should open export dialog', () => {
      const dialogRef = {
        afterClosed: jest.fn().mockReturnValue(of(null)),
      };
      const dialogSpy = jest
        .spyOn(component['dialog'], 'open')
        .mockReturnValue(dialogRef as any);

      component.openExportDialog();

      expect(dialogSpy).toHaveBeenCalled();
      dialogSpy.mockRestore();
    });
  });

  describe('openImportDialog', () => {
    it('should open import dialog and reload on success', (done) => {
      const dialogRef = {
        afterClosed: jest.fn().mockReturnValue(of({ success: true })),
      };
      const dialogSpy = jest
        .spyOn(component['dialog'], 'open')
        .mockReturnValue(dialogRef as any);
      mockConfigService.getConfig.mockReturnValue(of(mockConfig));

      component.openImportDialog();

      setTimeout(() => {
        expect(dialogSpy).toHaveBeenCalled();
        expect(mockConfigService.getConfig).toHaveBeenCalled();
        dialogSpy.mockRestore();
        done();
      }, 100);
    });
  });

  describe('hasChanges', () => {
    it('should return true when sections modified', () => {
      component.modifiedSections.add('corpus');

      expect(component.hasChanges()).toBe(true);
    });

    it('should return false when no changes', () => {
      component.modifiedSections.clear();

      expect(component.hasChanges()).toBe(false);
    });
  });
});
