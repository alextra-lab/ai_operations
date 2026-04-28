import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
} from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  ChunkingConfigOverride,
  ChunkingStrategy,
} from '../../api/models/preflight.models';

/**
 * Chunking Config Override Component
 *
 * Expert mode configuration form for overriding chunking strategy parameters.
 * Allows fine-grained control over chunking behavior.
 *
 * Follows ADR-012 (Hybrid CSS Strategy) and WCAG 2.1 AA guidelines.
 */
@Component({
  selector: 'app-chunking-config-override',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatCheckboxModule,
    MatDividerModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="chunking-config-override">
      <div class="flex items-center gap-2 mb-4">
        <mat-icon class="text-orange-600">warning</mat-icon>
        <h3 class="text-base font-medium">
          Expert Mode: Override Chunking Configuration
        </h3>
      </div>

      <p class="text-sm text-gray-600 mb-4">
        Customize chunking parameters. These settings override the recommended
        configuration. Use with caution as incorrect settings may degrade
        retrieval quality.
      </p>

      <form [formGroup]="configForm" class="space-y-4">
        <!-- Strategy Selection -->
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Chunking Strategy</mat-label>
          <mat-select formControlName="strategy" required>
            <mat-option
              *ngFor="let strategy of availableStrategies"
              [value]="strategy"
            >
              {{ formatStrategyName(strategy) }}
            </mat-option>
          </mat-select>
          <mat-hint>Select chunking strategy to configure</mat-hint>
        </mat-form-field>

        <!-- Common Parameters -->
        <div class="grid grid-cols-2 gap-4">
          <mat-form-field appearance="outline">
            <mat-label>Chunk Size (tokens)</mat-label>
            <input
              matInput
              type="number"
              formControlName="chunk_size"
              min="128"
              max="8192"
              [attr.aria-describedby]="'chunk-size-hint'"
            />
            <mat-hint id="chunk-size-hint">128-8192 tokens</mat-hint>
            <mat-error *ngIf="configForm.get('chunk_size')?.hasError('min')">
              Minimum: 128 tokens
            </mat-error>
            <mat-error *ngIf="configForm.get('chunk_size')?.hasError('max')">
              Maximum: 8192 tokens
            </mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Overlap (tokens)</mat-label>
            <input
              matInput
              type="number"
              formControlName="overlap"
              min="0"
              max="1024"
              [attr.aria-describedby]="'overlap-hint'"
            />
            <mat-hint id="overlap-hint"
              >0-1024 tokens (10-20% recommended)</mat-hint
            >
            <mat-error *ngIf="configForm.get('overlap')?.hasError('min')">
              Minimum: 0 tokens
            </mat-error>
            <mat-error *ngIf="configForm.get('overlap')?.hasError('max')">
              Maximum: 1024 tokens
            </mat-error>
          </mat-form-field>
        </div>

        <!-- Strategy-Specific Parameters -->
        <mat-divider></mat-divider>

        <!-- Heading Aware Parameters -->
        <div *ngIf="isHeadingAware()" class="space-y-4">
          <h4 class="text-sm font-medium text-gray-700">
            Heading-Aware Parameters
          </h4>

          <div class="flex items-center gap-4">
            <mat-checkbox formControlName="heading_level_1">H1</mat-checkbox>
            <mat-checkbox formControlName="heading_level_2">H2</mat-checkbox>
            <mat-checkbox formControlName="heading_level_3">H3</mat-checkbox>
            <mat-checkbox formControlName="heading_level_4">H4</mat-checkbox>
          </div>
        </div>

        <!-- Size Constraints -->
        <div class="space-y-4">
          <h4 class="text-sm font-medium text-gray-700">Size Constraints</h4>

          <div class="grid grid-cols-2 gap-4">
            <mat-form-field appearance="outline">
              <mat-label>Min Chunk Size (tokens)</mat-label>
              <input
                matInput
                type="number"
                formControlName="min_chunk_size"
                min="64"
                max="2048"
              />
              <mat-hint>64-2048 tokens</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>Max Chunk Size (tokens)</mat-label>
              <input
                matInput
                type="number"
                formControlName="max_chunk_size"
                min="256"
                max="8192"
              />
              <mat-hint>256-8192 tokens</mat-hint>
            </mat-form-field>
          </div>
        </div>

        <!-- Override Reasoning -->
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Override Reasoning</mat-label>
          <textarea
            matInput
            formControlName="override_reasoning"
            rows="3"
            placeholder="Explain why you're overriding the recommendation..."
            [attr.aria-label]="'Reasoning for configuration override'"
          ></textarea>
          <mat-hint>Document your rationale for future reference</mat-hint>
        </mat-form-field>
      </form>

      <div class="flex gap-2 justify-end mt-6">
        <button mat-button (click)="onCancel()" aria-label="Cancel override">
          Cancel
        </button>
        <button
          mat-raised-button
          color="primary"
          [disabled]="!configForm.valid"
          (click)="onApply()"
          aria-label="Apply configuration override"
        >
          Apply Override
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .chunking-config-override {
        padding: 16px;
        max-width: 600px;
      }

      mat-form-field {
        width: 100%;
      }

      /* Ensure proper focus indicators */
      button:focus-visible,
      input:focus-visible,
      select:focus-visible,
      textarea:focus-visible {
        outline: 2px solid var(--mat-primary);
        outline-offset: 2px;
      }
    `,
  ],
})
export class ChunkingConfigOverrideComponent implements OnInit {
  @Input() currentStrategy?: ChunkingStrategy;
  @Input() recommendedStrategy?: ChunkingStrategy;
  @Output() apply = new EventEmitter<ChunkingConfigOverride>();
  @Output() cancel = new EventEmitter<void>();

  configForm!: FormGroup;
  availableStrategies = Object.values(ChunkingStrategy);

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initializeForm();
  }

  /**
   * Initialize form with default values
   */
  private initializeForm(): void {
    this.configForm = this.fb.group({
      strategy: [
        this.currentStrategy ||
          this.recommendedStrategy ||
          ChunkingStrategy.FIXED_TOKEN,
        Validators.required,
      ],
      chunk_size: [1024, [Validators.min(128), Validators.max(8192)]],
      overlap: [128, [Validators.min(0), Validators.max(1024)]],
      min_chunk_size: [256, [Validators.min(64), Validators.max(2048)]],
      max_chunk_size: [2048, [Validators.min(256), Validators.max(8192)]],
      heading_level_1: [true],
      heading_level_2: [true],
      heading_level_3: [true],
      heading_level_4: [false],
      override_reasoning: [''],
    });
  }

  /**
   * Check if heading-aware strategy is selected
   */
  isHeadingAware(): boolean {
    return (
      this.configForm.get('strategy')?.value === ChunkingStrategy.HEADING_AWARE
    );
  }

  /**
   * Format strategy enum to human-readable name
   */
  formatStrategyName(strategy: ChunkingStrategy): string {
    const names: Record<ChunkingStrategy, string> = {
      [ChunkingStrategy.FIXED_TOKEN]: 'Fixed Token',
      [ChunkingStrategy.SLIDING_TOKEN]: 'Sliding Token',
      [ChunkingStrategy.HEADING_AWARE]: 'Heading Aware',
      [ChunkingStrategy.SENTENCE_PARAGRAPH]: 'Sentence/Paragraph',
      [ChunkingStrategy.TABLE_AWARE]: 'Table Aware',
      [ChunkingStrategy.SEMANTIC_ADAPTIVE]: 'Semantic Adaptive',
      [ChunkingStrategy.PAGE_BLOCK]: 'Page Block',
      [ChunkingStrategy.RECURSIVE]: 'Recursive',
    };
    return names[strategy] || strategy;
  }

  /**
   * Handle apply override
   */
  onApply(): void {
    if (!this.configForm.valid) {
      return;
    }

    const formValue = this.configForm.value;
    const heading_levels: number[] = [];

    if (this.isHeadingAware()) {
      if (formValue.heading_level_1) heading_levels.push(1);
      if (formValue.heading_level_2) heading_levels.push(2);
      if (formValue.heading_level_3) heading_levels.push(3);
      if (formValue.heading_level_4) heading_levels.push(4);
    }

    const override: ChunkingConfigOverride = {
      strategy: formValue.strategy,
      chunk_size: formValue.chunk_size,
      overlap: formValue.overlap,
      min_chunk_size: formValue.min_chunk_size,
      max_chunk_size: formValue.max_chunk_size,
      heading_levels: heading_levels.length > 0 ? heading_levels : undefined,
      metadata: {
        override_reasoning: formValue.override_reasoning,
        overridden_at: new Date().toISOString(),
      },
    };

    this.apply.emit(override);
  }

  /**
   * Handle cancel
   */
  onCancel(): void {
    this.cancel.emit();
  }
}
