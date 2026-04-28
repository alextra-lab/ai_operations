/**
 * Gateway Metrics Service
 *
 * Handles API communication for Inference Gateway metrics.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  GatewayMetrics,
  MetricsFilters,
  ModelMetrics,
  ProviderMetrics,
  TimeSeriesData,
} from '../models/gateway-metrics.models';

@Injectable({
  providedIn: 'root',
})
export class GatewayMetricsService {
  private readonly baseUrl = '/api/admin/gateway/metrics';

  constructor(private http: HttpClient) {}

  /**
   * Get aggregate metrics
   */
  getAggregateMetrics(filters: MetricsFilters): Observable<GatewayMetrics> {
    let params = new HttpParams().set('hours', filters.hours.toString());

    if (filters.provider) {
      params = params.set('provider', filters.provider);
    }

    return this.http.get<GatewayMetrics>(`${this.baseUrl}/aggregate`, {
      params,
    });
  }

  /**
   * Get time-series data for charts
   */
  getTimeSeriesData(filters: MetricsFilters): Observable<TimeSeriesData> {
    let params = new HttpParams()
      .set('hours', filters.hours.toString())
      .set(
        'interval_minutes',
        this.calculateInterval(filters.hours).toString()
      );

    if (filters.provider) {
      params = params.set('provider', filters.provider);
    }

    return this.http.get<TimeSeriesData>(`${this.baseUrl}/timeseries`, {
      params,
    });
  }

  /**
   * Get metrics by provider
   */
  getMetricsByProvider(hours: number): Observable<ProviderMetrics[]> {
    const params = new HttpParams().set('hours', hours.toString());
    return this.http.get<ProviderMetrics[]>(`${this.baseUrl}/by-provider`, {
      params,
    });
  }

  /**
   * Get metrics by model
   */
  getMetricsByModel(hours: number): Observable<ModelMetrics[]> {
    const params = new HttpParams().set('hours', hours.toString());
    return this.http.get<ModelMetrics[]>(`${this.baseUrl}/by-model`, {
      params,
    });
  }

  /**
   * Export metrics data as CSV
   */
  exportMetricsCSV(filters: MetricsFilters): string {
    // Will be implemented with data from aggregate metrics
    return '';
  }

  /**
   * Export metrics data as JSON
   */
  exportMetricsJSON(filters: MetricsFilters): string {
    // Will be implemented with data from aggregate metrics
    return '';
  }

  /**
   * Calculate appropriate interval based on time range
   */
  private calculateInterval(hours: number): number {
    if (hours <= 1) {
      return 5; // 5-minute intervals for 1 hour
    } else if (hours <= 6) {
      return 15; // 15-minute intervals for 6 hours
    } else if (hours <= 24) {
      return 60; // 1-hour intervals for 24 hours
    } else if (hours <= 168) {
      return 360; // 6-hour intervals for 7 days
    } else {
      return 1440; // 24-hour intervals for 30 days
    }
  }
}
