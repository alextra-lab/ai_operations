import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { AdminPricingService } from './admin-pricing.service';

describe('AdminPricingService', () => {
  let service: AdminPricingService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AdminPricingService],
    });
    service = TestBed.inject(AdminPricingService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('should GET current pricing', () => {
    service.getCurrent('mistral-large').subscribe();
    const req = http.expectOne(
      '/api/v1/admin/pricing/models/mistral-large/pricing/current'
    );
    req.flush({
      model_id: 'mistral-large',
      currency: 'EUR',
      input_price_per_million: 1,
      output_price_per_million: 2,
    });
  });

  it('should GET price history', () => {
    service.getHistory('mistral-large').subscribe();
    const req = http.expectOne(
      '/api/v1/admin/pricing/models/mistral-large/pricing/history'
    );
    req.flush([]);
  });

  it('should POST set price', () => {
    service
      .setPrice('mistral-large', {
        input_price_per_million: 1.23,
        output_price_per_million: 4.56,
        change_reason: 'test',
      })
      .subscribe();
    const req = http.expectOne(
      '/api/v1/admin/pricing/models/mistral-large/pricing/change'
    );
    req.flush({});
  });
});
