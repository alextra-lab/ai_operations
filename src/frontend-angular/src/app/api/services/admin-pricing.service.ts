import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  ModelPriceChangeRequest,
  ModelPriceCurrentResponse,
  ModelPriceHistoryEntry,
} from '../models/pricing.models';

@Injectable({ providedIn: 'root' })
export class AdminPricingService {
  private readonly baseUrl = '/api/v1/admin/pricing';

  constructor(private http: HttpClient) {}

  getCurrent(modelId: string): Observable<ModelPriceCurrentResponse> {
    return this.http.get<ModelPriceCurrentResponse>(
      `${this.baseUrl}/models/${encodeURIComponent(modelId)}/pricing/current`
    );
  }

  getHistory(modelId: string): Observable<ModelPriceHistoryEntry[]> {
    return this.http.get<ModelPriceHistoryEntry[]>(
      `${this.baseUrl}/models/${encodeURIComponent(modelId)}/pricing/history`
    );
  }

  setPrice(
    modelId: string,
    body: ModelPriceChangeRequest
  ): Observable<ModelPriceCurrentResponse> {
    return this.http.post<ModelPriceCurrentResponse>(
      `${this.baseUrl}/models/${encodeURIComponent(modelId)}/pricing/change`,
      body
    );
  }
}
