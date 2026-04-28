/**
 * System Configuration Service
 *
 * Angular service for system configuration management.
 * Wraps backend admin config API endpoints.
 */

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../../environments/environment';
import {
  ConfigExportResponse,
  ConfigImportRequest,
  ConfigImportResponse,
  ConfigSchema,
  ConfigSection,
  ConfigSectionResponse,
  SystemConfigFull,
} from '../models/system-config.models';

@Injectable({
  providedIn: 'root',
})
export class SystemConfigService {
  private readonly baseUrl = `${environment.apiBaseUrl}/admin/config`;

  constructor(private http: HttpClient) {}

  /**
   * Get all system configuration
   */
  getConfig(): Observable<SystemConfigFull> {
    return this.http.get<SystemConfigFull>(`${this.baseUrl}/`);
  }

  /**
   * Get specific configuration section
   */
  getConfigSection(section: ConfigSection): Observable<ConfigSectionResponse> {
    return this.http.get<ConfigSectionResponse>(`${this.baseUrl}/${section}`);
  }

  /**
   * Update configuration section
   */
  updateConfigSection(
    section: ConfigSection,
    config: Record<string, unknown>
  ): Observable<ConfigSectionResponse> {
    return this.http.put<ConfigSectionResponse>(
      `${this.baseUrl}/${section}`,
      config
    );
  }

  /**
   * Get JSON schema for configuration section
   */
  getConfigSchema(section: ConfigSection): Observable<ConfigSchema> {
    return this.http.get<ConfigSchema>(`${this.baseUrl}/schema/${section}`);
  }

  /**
   * Export configuration as YAML
   */
  exportConfig(): Observable<ConfigExportResponse> {
    return this.http.post<ConfigExportResponse>(`${this.baseUrl}/export`, {});
  }

  /**
   * Import configuration from YAML
   */
  importConfig(request: ConfigImportRequest): Observable<ConfigImportResponse> {
    return this.http.post<ConfigImportResponse>(
      `${this.baseUrl}/import`,
      request
    );
  }

  /**
   * Validate configuration YAML without importing
   */
  validateConfigYaml(configYaml: string): Observable<ConfigImportResponse> {
    return this.importConfig({
      config_yaml: configYaml,
      validate_only: true,
    });
  }
}
