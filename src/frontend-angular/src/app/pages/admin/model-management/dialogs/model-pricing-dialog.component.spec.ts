import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { AdminPricingService } from '../../../../api/services/admin-pricing.service';
import {
  ModelPricingDialogComponent,
  ModelPricingDialogData,
} from './model-pricing-dialog.component';

describe('ModelPricingDialogComponent', () => {
  let fixture: ComponentFixture<ModelPricingDialogComponent>;
  let component: ModelPricingDialogComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ModelPricingDialogComponent, NoopAnimationsModule],
      providers: [
        {
          provide: AdminPricingService,
          useValue: {
            getCurrent: () =>
              of({
                model_id: 'mistral-large',
                currency: 'EUR',
                input_price_per_million: 1,
                output_price_per_million: 2,
                effective_from: null,
                effective_to: null,
              }),
            getHistory: () => of([]),
            setPrice: () => of({}),
          },
        },
        { provide: MatDialogRef, useValue: { close: () => {} } },
        {
          provide: MAT_DIALOG_DATA,
          useValue: { modelId: 'mistral-large' } as ModelPricingDialogData,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ModelPricingDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create and load current pricing', () => {
    expect(component).toBeTruthy();
    expect(component.current?.currency).toBe('EUR');
  });
});
