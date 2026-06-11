import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { LucideAngularModule } from 'lucide-angular';
import {
  ModelPriceChangeRequest,
  ModelPriceCurrentResponse,
  ModelPriceHistoryEntry,
} from '../../../../api/models/pricing.models';
import { AdminPricingService } from '../../../../api/services/admin-pricing.service';

export interface ModelPricingDialogData {
  modelId: string; // external model_id string
}

@Component({
  selector: 'app-model-pricing-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="pricing-dialog">
      <h2 mat-dialog-title>
        <lucide-icon name="euro"></lucide-icon>
        Model Pricing
      </h2>

      <mat-dialog-content>
        @if (current) {
          <section class="current">
            <h3>Current Price</h3>
            <div class="grid">
              <div>
                <label>Input (per 1M)</label>
                <div class="value">
                  € {{ current.input_price_per_million | number: '1.2-4' }}
                </div>
              </div>
              <div>
                <label>Output (per 1M)</label>
                <div class="value">
                  € {{ current.output_price_per_million | number: '1.2-4' }}
                </div>
              </div>
              <div>
                <label>Effective From</label>
                <div class="value">{{ current.effective_from || 'now' }}</div>
              </div>
              <div>
                <label>Effective To</label>
                <div class="value">{{ current.effective_to || '—' }}</div>
              </div>
            </div>
          </section>
        } @else {
          <div class="loading">
            <mat-spinner diameter="40"></mat-spinner>
          </div>
        }

        @if (history.length) {
          <section class="history">
            <h3>Price History</h3>
            <table mat-table [dataSource]="history" class="history-table">
              <ng-container matColumnDef="effective_from">
                <th mat-header-cell *matHeaderCellDef>From</th>
                <td mat-cell *matCellDef="let row">{{ row.effective_from }}</td>
              </ng-container>
              <ng-container matColumnDef="effective_to">
                <th mat-header-cell *matHeaderCellDef>To</th>
                <td mat-cell *matCellDef="let row">
                  {{ row.effective_to || '—' }}
                </td>
              </ng-container>
              <ng-container matColumnDef="input">
                <th mat-header-cell *matHeaderCellDef>Input €/1M</th>
                <td mat-cell *matCellDef="let row">
                  € {{ row.input_price_per_million | number: '1.2-4' }}
                </td>
              </ng-container>
              <ng-container matColumnDef="output">
                <th mat-header-cell *matHeaderCellDef>Output €/1M</th>
                <td mat-cell *matCellDef="let row">
                  € {{ row.output_price_per_million | number: '1.2-4' }}
                </td>
              </ng-container>
              <ng-container matColumnDef="reason">
                <th mat-header-cell *matHeaderCellDef>Reason</th>
                <td mat-cell *matCellDef="let row">
                  {{ row.change_reason || '—' }}
                </td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
            </table>
          </section>
        }

        <section class="change-form">
          <h3>Change Price</h3>
          <form [formGroup]="priceForm">
            <div class="row">
              <mat-form-field appearance="outline">
                <mat-label>Input €/1M</mat-label>
                <span matPrefix>€&nbsp;</span>
                <input
                  matInput
                  type="number"
                  step="0.00001"
                  formControlName="input_price_per_million"
                  cdkFocusInitial
                />
              </mat-form-field>
              <mat-form-field appearance="outline">
                <mat-label>Output €/1M</mat-label>
                <span matPrefix>€&nbsp;</span>
                <input
                  matInput
                  type="number"
                  step="0.00001"
                  formControlName="output_price_per_million"
                />
              </mat-form-field>
            </div>
            <mat-form-field appearance="outline" class="full">
              <mat-label>Change Reason (optional)</mat-label>
              <input matInput formControlName="change_reason" />
            </mat-form-field>
          </form>
        </section>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button (click)="close()">Close</button>
        <button
          mat-raised-button
          color="primary"
          (click)="save()"
          [disabled]="priceForm.invalid || saving"
        >
          <lucide-icon name="save"></lucide-icon>
          {{ saving ? 'Saving...' : 'Save Price' }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [
    `
      .pricing-dialog {
        min-width: 700px;
        max-width: 900px;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
      }
      .value {
        font-weight: 600;
      }
      .history-table {
        width: 100%;
        margin-top: 8px;
      }
      .row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .full {
        width: 100%;
      }
      h3 {
        margin: 16px 0 8px 0;
        font-size: 16px;
      }
      .loading {
        display: flex;
        justify-content: center;
        padding: 24px;
      }
    `,
  ],
})
export class ModelPricingDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  priceForm!: FormGroup;
  current: ModelPriceCurrentResponse | null = null;
  history: ModelPriceHistoryEntry[] = [];
  displayedColumns = [
    'effective_from',
    'effective_to',
    'input',
    'output',
    'reason',
  ];
  saving = false;

  constructor(
    private fb: FormBuilder,
    private pricing: AdminPricingService,
    public dialogRef: MatDialogRef<ModelPricingDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ModelPricingDialogData
  ) {}

  ngOnInit(): void {
    this.priceForm = this.fb.group({
      input_price_per_million: [0, [Validators.required, Validators.min(0)]],
      output_price_per_million: [0, [Validators.required, Validators.min(0)]],
      change_reason: [''],
    });
    this.load();
  }

  load(): void {
    this.pricing.getCurrent(this.data.modelId).subscribe({
      next: (c) => (this.current = c),
    });
    this.pricing.getHistory(this.data.modelId).subscribe({
      next: (h) => (this.history = h),
    });
  }

  save(): void {
    if (this.priceForm.invalid) return;
    this.saving = true;
    const body: ModelPriceChangeRequest = {
      input_price_per_million: this.priceForm.value.input_price_per_million,
      output_price_per_million: this.priceForm.value.output_price_per_million,
      change_reason: this.priceForm.value.change_reason || null,
    };
    this.pricing.setPrice(this.data.modelId, body).subscribe({
      next: (resp) => {
        this.current = resp;
        this.saving = false;
        queueMicrotask(() => this.cdr.detectChanges());
        this.load();
      },
      error: () => (this.saving = false),
    });
  }

  close(): void {
    this.dialogRef.close();
  }
}
