/**
 * Chunking Analysis Page Component
 *
 * Advanced document chunking strategy analysis workflow for Corpus Managers
 * and AIO Developers. Provides AI-powered recommendations with preflight testing.
 *
 * Follows LAYERED_PAGE_LAYOUT_PATTERN.md:
 * - Layer 2: Page header with minimal controls (NEVER scrolls)
 * - Layer 3: Multi-step workflow content (SCROLLS)
 *
 * Follows ADR-012 (Hybrid CSS Strategy):
 * - Tailwind for layout and spacing
 * - Material for UI primitives
 * - Component SCSS for critical patterns only
 */

import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatStepperModule } from '@angular/material/stepper';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { Collection } from '../../../api/models/collection.models';
import {
  ChunkingConfigOverride,
  ChunkingStrategy,
  PreflightReport,
} from '../../../api/models/preflight.models';
import { CollectionService } from '../../../api/services/collection.service';
import { DocumentService } from '../../../api/services/document.service';
import { PreflightService } from '../../../api/services/preflight.service';
import { ChunkingConfigOverrideComponent } from '../../../components/preflight/chunking-config-override.component';
import { PreflightReportComponent } from '../../../components/preflight/preflight-report.component';
import { StrategyComparisonComponent } from '../../../components/preflight/strategy-comparison.component';

enum AnalysisStep {
  UPLOAD = 'upload',
  ANALYZING = 'analyzing',
  REPORT = 'report',
  CONFIGURE = 'configure',
  COMPLETE = 'complete',
}

@Component({
  selector: 'app-chunking-analysis',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatStepperModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    PreflightReportComponent,
  ],
  template: `
    <!-- LAYERED_PAGE_LAYOUT_PATTERN Applied -->
    <div class="page-container">
      <!-- Layer 2: Page Header (NEVER SCROLLS) -->
      <div class="page-header-section">
        <div class="page-title">
          <h1 class="flex items-center gap-3">
            <lucide-icon name="chart-column"></lucide-icon>
            Document Chunking Analysis
          </h1>
          <p class="subtitle">
            Manual chunking optimization workflow with visible metrics, strategy
            comparison, and quality analysis. For Corpus Managers and UC
            Developers who need full control and transparency.
          </p>
        </div>

        <!-- Step Indicator -->
        <div class="page-controls">
          <div class="controls-container">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4">
                <div
                  class="flex items-center gap-2"
                  [class.text-blue-600]="currentStep === 'upload'"
                  [class.font-medium]="currentStep === 'upload'"
                >
                  <lucide-icon
                    [class.text-blue-600]="currentStep === 'upload'"
                    [name]="getStepIcon('upload')"
                  ></lucide-icon>
                  <span class="text-sm">Upload</span>
                </div>
                <lucide-icon
                  class="text-gray-400"
                  name="chevron-right"
                ></lucide-icon>
                <div
                  class="flex items-center gap-2"
                  [class.text-blue-600]="currentStep === 'analyzing'"
                  [class.font-medium]="currentStep === 'analyzing'"
                >
                  <lucide-icon
                    [class.text-blue-600]="currentStep === 'analyzing'"
                    [name]="getStepIcon('analyzing')"
                  ></lucide-icon>
                  <span class="text-sm">Analyze</span>
                </div>
                <lucide-icon
                  class="text-gray-400"
                  name="chevron-right"
                ></lucide-icon>
                <div
                  class="flex items-center gap-2"
                  [class.text-blue-600]="currentStep === 'report'"
                  [class.font-medium]="currentStep === 'report'"
                >
                  <lucide-icon
                    [class.text-blue-600]="currentStep === 'report'"
                    [name]="getStepIcon('report')"
                  ></lucide-icon>
                  <span class="text-sm">Report</span>
                </div>
                <lucide-icon
                  class="text-gray-400"
                  name="chevron-right"
                ></lucide-icon>
                <div
                  class="flex items-center gap-2"
                  [class.text-blue-600]="currentStep === 'configure'"
                  [class.font-medium]="currentStep === 'configure'"
                >
                  <lucide-icon
                    [class.text-blue-600]="currentStep === 'configure'"
                    [name]="getStepIcon('configure')"
                  ></lucide-icon>
                  <span class="text-sm">Configure</span>
                </div>
              </div>

              <button
                mat-button
                (click)="reset()"
                *ngIf="currentStep !== 'upload'"
              >
                <lucide-icon name="refresh-cw"></lucide-icon>
                Start Over
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Layer 3: Content Area (SCROLLS) -->
      <div class="content-area">
        <!-- Step 1: Upload Document -->
        <mat-card *ngIf="currentStep === 'upload'" class="mb-6">
          <mat-card-header>
            <mat-card-title>Upload Document for Analysis</mat-card-title>
            <mat-card-subtitle
              >Select a document to analyze its structure and find the optimal
              chunking strategy</mat-card-subtitle
            >
          </mat-card-header>

          <!-- When to Use This -->
          <div
            class="mx-6 mt-4 p-3 bg-amber-50 border border-amber-200 rounded flex items-start gap-2 text-sm"
          >
            <lucide-icon
              class="text-amber-700 text-base mt-0.5"
              name="lightbulb"
            ></lucide-icon>
            <div>
              <div class="font-medium text-amber-900 mb-1">
                When to use this tool:
              </div>
              <ul class="text-amber-800 text-xs space-y-1 ml-4 list-disc">
                <li>
                  You want to
                  <strong>see metrics and compare strategies</strong> before
                  uploading
                </li>
                <li>
                  You're creating <strong>reusable presets</strong> for document
                  types
                </li>
                <li>
                  You need to <strong>manually control</strong> chunking
                  configuration
                </li>
                <li>Regular uploads with "Auto" mode aren't performing well</li>
              </ul>
              <div class="mt-2 text-xs text-amber-700">
                💡 <strong>Tip:</strong> For normal uploads, use "Upload
                Documents" with Auto-Detect mode. The system will optimize
                automatically without manual intervention.
              </div>
            </div>
          </div>

          <mat-card-content class="mt-4">
            <form [formGroup]="uploadForm" class="flex flex-col gap-4">
              <!-- File Upload Area -->
              <div
                class="upload-area-compact flex-1"
                [class.drag-over]="isDragOver"
                (dragover)="onDragOver($event)"
                (dragleave)="onDragLeave($event)"
                (drop)="onDrop($event)"
                (click)="fileInput.click()"
              >
                <div class="flex items-center gap-3">
                  <lucide-icon
                    class="text-blue-600 text-4xl w-10 h-10"
                    name="cloud-upload"
                  ></lucide-icon>
                  <div class="flex-1">
                    <p class="m-0 font-medium">
                      {{
                        selectedFile
                          ? selectedFile.name
                          : 'Drag & drop file or click to browse'
                      }}
                    </p>
                    <p class="m-0 text-xs text-gray-600">
                      {{
                        selectedFile
                          ? formatFileSize(selectedFile.size)
                          : 'PDF, DOC, DOCX, TXT, RTF, ODT (max 50MB)'
                      }}
                    </p>
                  </div>
                  <button
                    mat-raised-button
                    color="primary"
                    type="button"
                    class="shrink-0"
                  >
                    <lucide-icon name="folder-open"></lucide-icon>
                    Browse
                  </button>
                </div>

                <input
                  #fileInput
                  type="file"
                  accept=".pdf,.doc,.docx,.txt,.rtf,.odt"
                  (change)="onFileSelected($event)"
                  style="display: none;"
                />
              </div>

              <!-- Collection Selection -->
              <div class="flex gap-4">
                <mat-form-field appearance="outline" class="flex-1">
                  <mat-label>Target Collection</mat-label>
                  <mat-select formControlName="collection" required>
                    <mat-option
                      *ngFor="let collection of availableCollections"
                      [value]="collection.name"
                    >
                      <div class="flex items-center justify-between w-full">
                        <span class="font-medium">{{ collection.name }}</span>
                        <span class="text-xs text-gray-500"
                          >({{ collection.document_count }} docs)</span
                        >
                      </div>
                    </mat-option>
                  </mat-select>
                  <mat-hint
                    >Documents will use this collection's embedding
                    model</mat-hint
                  >
                </mat-form-field>
              </div>

              <!-- Advanced Options -->
              <div
                class="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded"
              >
                <div class="flex items-center gap-2">
                  <lucide-icon
                    class="text-gray-600"
                    name="sliders-horizontal"
                  ></lucide-icon>
                  <span class="text-sm font-medium">Test Suite (Optional)</span>
                </div>
                <mat-form-field appearance="outline" class="w-64">
                  <mat-label>Test Suite for Quality Metrics</mat-label>
                  <mat-select formControlName="testSuiteId">
                    <mat-option [value]="null"
                      >None - Structure Analysis Only</mat-option
                    >
                    <!-- Test suites would be loaded here -->
                  </mat-select>
                  <mat-hint>Enables retrieval quality metrics</mat-hint>
                </mat-form-field>
              </div>
            </form>
          </mat-card-content>

          <mat-card-actions class="flex justify-end gap-2">
            <button mat-button routerLink="/documents/library">Cancel</button>
            <button
              mat-raised-button
              color="primary"
              [disabled]="!selectedFile || !uploadForm.valid"
              (click)="startAnalysis()"
            >
              <lucide-icon name="play"></lucide-icon>
              Start Analysis
            </button>
          </mat-card-actions>
        </mat-card>

        <!-- Step 2: Analyzing -->
        <mat-card *ngIf="currentStep === 'analyzing'" class="mb-6">
          <mat-card-header>
            <mat-card-title class="flex items-center gap-2">
              <mat-spinner diameter="24"></mat-spinner>
              Analyzing Document Structure
            </mat-card-title>
            <mat-card-subtitle
              >Testing multiple chunking strategies and evaluating quality
              metrics...</mat-card-subtitle
            >
          </mat-card-header>

          <mat-card-content class="mt-4">
            <div class="flex flex-col gap-4">
              <div>
                <div class="flex justify-between items-center mb-2">
                  <span class="text-sm font-medium">{{ analysisStatus }}</span>
                  <span class="text-sm text-gray-600"
                    >{{ analysisProgress }}%</span
                  >
                </div>
                <mat-progress-bar
                  mode="determinate"
                  [value]="analysisProgress"
                ></mat-progress-bar>
              </div>

              <div class="grid grid-cols-2 gap-4 mt-4">
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-600 mb-1">Document Size</div>
                  <div class="text-sm font-medium">
                    {{ selectedFile ? formatFileSize(selectedFile.size) : '-' }}
                  </div>
                </div>
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-600 mb-1">Estimated Time</div>
                  <div class="text-sm font-medium">15-30 seconds</div>
                </div>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Step 3: Preflight Report -->
        <div *ngIf="currentStep === 'report' && preflightReport">
          <app-preflight-report
            [report]="preflightReport"
            (accept)="acceptRecommendation($event)"
            (override)="openOverrideDialog()"
            (viewDetails)="openStrategyComparison()"
            (strategyOverride)="selectAlternativeStrategy($event)"
          >
          </app-preflight-report>
        </div>

        <!-- Step 4: Configuration Preview -->
        <mat-card
          *ngIf="currentStep === 'configure' && selectedConfig"
          class="mb-6"
        >
          <mat-card-header>
            <mat-card-title>Chunking Configuration</mat-card-title>
            <mat-card-subtitle
              >Review and apply the selected chunking
              strategy</mat-card-subtitle
            >
          </mat-card-header>

          <mat-card-content class="mt-4">
            <div class="flex flex-col gap-4">
              <!-- Strategy Info -->
              <div class="p-4 bg-blue-50 border border-blue-200 rounded">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-medium text-blue-900">
                      Selected Strategy
                    </div>
                    <div class="text-lg font-semibold text-blue-700">
                      {{ formatStrategyName(selectedConfig.strategy) }}
                    </div>
                  </div>
                  <button mat-button color="primary" (click)="backToReport()">
                    <lucide-icon name="pencil"></lucide-icon>
                    Change
                  </button>
                </div>
              </div>

              <!-- Configuration Details -->
              <div class="grid grid-cols-2 gap-4">
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-600 mb-1">Chunk Size</div>
                  <div class="text-sm font-medium">
                    {{ selectedConfig.chunk_size }} tokens
                  </div>
                </div>
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-600 mb-1">Overlap</div>
                  <div class="text-sm font-medium">
                    {{ selectedConfig.chunk_overlap }} tokens
                  </div>
                </div>
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-600 mb-1">Min Chunk Size</div>
                  <div class="text-sm font-medium">
                    {{ selectedConfig.min_chunk_size }} tokens
                  </div>
                </div>
                <div class="p-3 bg-gray-50 rounded">
                  <div class="text-xs text-gray-600 mb-1">Max Chunk Size</div>
                  <div class="text-sm font-medium">
                    {{ selectedConfig.max_chunk_size }} tokens
                  </div>
                </div>
              </div>

              <!-- Save as Preset Option -->
              <div
                class="flex items-center gap-3 p-3 border border-gray-200 rounded"
              >
                <lucide-icon
                  class="text-gray-600"
                  name="bookmark"
                ></lucide-icon>
                <div class="flex-1">
                  <div class="text-sm font-medium">Save as Preset</div>
                  <div class="text-xs text-gray-600">
                    Reuse this configuration for future uploads
                  </div>
                </div>
                <button mat-button color="primary" (click)="savePreset()">
                  Save Preset
                </button>
              </div>
            </div>
          </mat-card-content>

          <mat-card-actions class="flex justify-between">
            <button mat-button (click)="backToReport()">
              <lucide-icon name="arrow-left"></lucide-icon>
              Back to Report
            </button>
            <div class="flex gap-2">
              <button mat-button (click)="reset()">Cancel</button>
              <button
                mat-raised-button
                color="primary"
                (click)="applyConfiguration()"
              >
                <lucide-icon name="circle-check"></lucide-icon>
                Apply & Upload
              </button>
            </div>
          </mat-card-actions>
        </mat-card>
      </div>
    </div>
  `,
  styles: [
    `
      /**
         * Chunking Analysis Styles
         * ADR-012 Compliant: Material + Tailwind + Component SCSS
         * LAYERED_PAGE_LAYOUT_PATTERN Applied
         */

      // ========================================================================
      // CRITICAL LAYERED PATTERN (Cannot be done with Tailwind utilities)
      // ========================================================================

      .page-container {
        display: flex;
        flex-direction: column;
        height: calc(100vh - var(--chrome-h));
        margin: -24px -32px;
        padding: 0;
        overflow: hidden; // CRITICAL: Prevents double scrollbars
      }

      .page-header-section {
        flex: 0 0 auto; // CRITICAL: Never grow/shrink
        z-index: 100;
        background: white;
        border-bottom: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

        .page-title {
          padding: 24px 24px 16px 24px;

          h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 500;
          }

          .subtitle {
            margin: 8px 0 0 0;
            color: #666;
            font-size: 14px;
          }
        }

        .page-controls {
          padding: 0 24px 16px 24px;

          .controls-container {
            background: #f5f5f5;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            padding: 16px 20px;
          }
        }
      }

      .content-area {
        flex: 1; // CRITICAL: Take remaining space
        overflow-y: auto; // CRITICAL: Enable scrolling
        overflow-x: hidden;
        padding: 24px;
        min-height: 0; // CRITICAL: Allows flex child to shrink
        background: #fafafa;
      }

      // ========================================================================
      // COMPONENT-SPECIFIC STYLES (Complex states that need SCSS)
      // ========================================================================

      .upload-area-compact {
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
        background-color: #fafafa;

        &:hover,
        &.drag-over {
          border-color: #1976d2;
          background-color: #e3f2fd;
        }
      }
    `,
  ],
})
export class ChunkingAnalysisComponent implements OnInit {
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  // Form
  uploadForm: FormGroup;

  // State
  currentStep: AnalysisStep = AnalysisStep.UPLOAD;
  selectedFile: File | null = null;
  isDragOver = false;
  availableCollections: Collection[] = [];
  preflightReport: PreflightReport | null = null;
  selectedConfig: ChunkingConfigOverride | null = null;
  analysisProgress = 0;
  analysisStatus = 'Initializing...';

  constructor(
    private fb: FormBuilder,
    private collectionService: CollectionService,
    private preflightService: PreflightService,
    private documentService: DocumentService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private router: Router
  ) {
    this.uploadForm = this.fb.group({
      collection: ['default', Validators.required],
      testSuiteId: [null],
    });
  }

  ngOnInit(): void {
    this.loadCollections();
  }

  loadCollections(): void {
    this.collectionService.listCollections(true).subscribe({
      next: (response) => {
        this.availableCollections = response.collections;
        const defaultCollection = this.availableCollections.find(
          (c) => c.is_default
        );
        if (defaultCollection) {
          this.uploadForm.patchValue({ collection: defaultCollection.name });
        }
      },
      error: (error) => {
        console.error('Failed to load collections:', error);
        this.snackBar.open('Failed to load collections', 'Close', {
          duration: 5000,
        });
      },
    });
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.selectedFile = files[0];
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
    }
  }

  startAnalysis(): void {
    if (!this.selectedFile) return;

    this.currentStep = AnalysisStep.ANALYZING;
    this.analysisProgress = 0;
    this.analysisStatus = 'Uploading document...';

    // Simulate progress
    const progressInterval = setInterval(() => {
      this.analysisProgress += 10;
      if (this.analysisProgress === 30) {
        this.analysisStatus = 'Analyzing document structure...';
      } else if (this.analysisProgress === 60) {
        this.analysisStatus = 'Testing chunking strategies...';
      } else if (this.analysisProgress === 90) {
        this.analysisStatus = 'Generating recommendations...';
      }

      if (this.analysisProgress >= 100) {
        clearInterval(progressInterval);
      }
    }, 500);

    // Call preflight analysis
    this.preflightService
      .analyzeDocument(
        this.selectedFile,
        this.uploadForm.value.collection,
        undefined, // All strategies
        this.uploadForm.value.testSuiteId
      )
      .subscribe({
        next: (report) => {
          clearInterval(progressInterval);
          this.analysisProgress = 100;
          this.preflightReport = report;
          this.currentStep = AnalysisStep.REPORT;
        },
        error: (error) => {
          clearInterval(progressInterval);
          this.snackBar.open(error.message || 'Analysis failed', 'Close', {
            duration: 5000,
          });
          this.currentStep = AnalysisStep.UPLOAD;
        },
      });
  }

  acceptRecommendation(strategy: ChunkingStrategy): void {
    // Get default config for recommended strategy
    this.preflightService.getStrategyDefaultConfig(strategy).subscribe({
      next: (config) => {
        this.selectedConfig = config;
        this.currentStep = AnalysisStep.CONFIGURE;
      },
      error: () => {
        this.snackBar.open('Failed to load strategy configuration', 'Close', {
          duration: 3000,
        });
      },
    });
  }

  selectAlternativeStrategy(strategy: ChunkingStrategy): void {
    this.acceptRecommendation(strategy);
  }

  openOverrideDialog(): void {
    const dialogRef = this.dialog.open(ChunkingConfigOverrideComponent, {
      width: '700px',
      data: {
        currentStrategy: this.preflightReport?.recommendation.strategy,
        recommendedStrategy: this.preflightReport?.recommendation.strategy,
      },
    });

    dialogRef.componentInstance.apply.subscribe(
      (config: ChunkingConfigOverride) => {
        this.selectedConfig = config;
        this.currentStep = AnalysisStep.CONFIGURE;
        dialogRef.close();
      }
    );

    dialogRef.componentInstance.cancel.subscribe(() => {
      dialogRef.close();
    });
  }

  openStrategyComparison(): void {
    if (!this.preflightReport) return;

    const dialogRef = this.dialog.open(StrategyComparisonComponent, {
      width: '1200px',
      maxWidth: '95vw',
      data: {
        results: this.preflightReport.strategy_results,
        recommendedStrategy: this.preflightReport.recommendation.strategy,
      },
    });

    dialogRef.componentInstance.select.subscribe(
      (strategy: ChunkingStrategy) => {
        this.acceptRecommendation(strategy);
        dialogRef.close();
      }
    );

    dialogRef.componentInstance.close.subscribe(() => {
      dialogRef.close();
    });
  }

  backToReport(): void {
    this.currentStep = AnalysisStep.REPORT;
  }

  savePreset(): void {
    // TODO: Implement save preset dialog
    this.snackBar.open('Save preset feature coming soon', 'Close', {
      duration: 3000,
    });
  }

  applyConfiguration(): void {
    if (!this.selectedFile || !this.selectedConfig) return;

    // TODO: Apply configuration and upload document
    this.snackBar.open(
      'Uploading document with optimized chunking configuration...',
      'Close',
      { duration: 3000 }
    );

    // Navigate back to document library after short delay
    setTimeout(() => {
      this.router.navigate(['/documents/library']);
    }, 1500);
  }

  reset(): void {
    this.currentStep = AnalysisStep.UPLOAD;
    this.selectedFile = null;
    this.preflightReport = null;
    this.selectedConfig = null;
    this.analysisProgress = 0;
    this.uploadForm.reset({
      collection: 'default',
      testSuiteId: null,
    });
  }

  getStepIcon(step: string): string {
    const icons: Record<string, string> = {
      upload:
        this.currentStep === 'upload'
          ? 'file-up'
          : this.getStepIndex(step) < this.getStepIndex(this.currentStep)
            ? 'circle-check'
            : 'circle',
      analyzing:
        this.currentStep === 'analyzing'
          ? 'hourglass'
          : this.getStepIndex(step) < this.getStepIndex(this.currentStep)
            ? 'circle-check'
            : 'circle',
      report:
        this.currentStep === 'report'
          ? 'chart-column'
          : this.getStepIndex(step) < this.getStepIndex(this.currentStep)
            ? 'circle-check'
            : 'circle',
      configure:
        this.currentStep === 'configure'
          ? 'settings'
          : this.getStepIndex(step) < this.getStepIndex(this.currentStep)
            ? 'circle-check'
            : 'circle',
    };
    return icons[step] || 'circle';
  }

  private getStepIndex(step: string): number {
    const steps = ['upload', 'analyzing', 'report', 'configure'];
    return steps.indexOf(step);
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  }

  formatStrategyName(strategy: ChunkingStrategy): string {
    return this.preflightService.formatStrategyName(strategy);
  }
}
