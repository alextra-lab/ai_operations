/**
 * Provider Management Service Tests
 */

import { HttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import {
  CreateProviderRequest,
  ProviderConfig,
  ProviderListResponse,
} from '../models/provider-management.models';
import { ProviderManagementService } from './provider-management.service';

describe('ProviderManagementService', () => {
  let service: ProviderManagementService;
  let httpClientMock: jest.Mocked<HttpClient>;

  beforeEach(() => {
    httpClientMock = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
    } as any;

    TestBed.configureTestingModule({
      providers: [
        ProviderManagementService,
        { provide: HttpClient, useValue: httpClientMock },
      ],
    });

    service = TestBed.inject(ProviderManagementService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('listProviders', () => {
    it('should fetch providers list', (done) => {
      const mockResponse: ProviderListResponse = {
        items: [
          {
            id: '123',
            name: 'OpenAI',
            provider_type: 'openai',
            base_url: 'https://api.openai.com/v1',
            is_enabled: true,
            status: 'active',
            priority: 100,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      };

      httpClientMock.get.mockReturnValue(of(mockResponse));

      service.listProviders({ limit: 20 }).subscribe({
        next: (response) => {
          expect(response).toEqual(mockResponse);
          expect(httpClientMock.get).toHaveBeenCalledWith(
            '/api/admin/gateway/providers',
            expect.any(Object)
          );
          done();
        },
      });
    });
  });

  describe('getProvider', () => {
    it('should fetch a single provider', (done) => {
      const mockProvider: ProviderConfig = {
        id: '123',
        name: 'OpenAI',
        provider_type: 'openai',
        base_url: 'https://api.openai.com/v1',
        is_enabled: true,
        status: 'active',
        priority: 100,
      };

      httpClientMock.get.mockReturnValue(of(mockProvider));

      service.getProvider('123').subscribe({
        next: (provider) => {
          expect(provider).toEqual(mockProvider);
          expect(httpClientMock.get).toHaveBeenCalledWith(
            '/api/admin/gateway/providers/123'
          );
          done();
        },
      });
    });
  });

  describe('createProvider', () => {
    it('should create a new provider', (done) => {
      const request: CreateProviderRequest = {
        name: 'New Provider',
        provider_type: 'mistral',
        base_url: 'https://api.mistral.ai',
        is_enabled: true,
      };

      const mockResponse: ProviderConfig = {
        ...request,
        id: '456',
        status: 'testing',
        priority: 100,
      };

      httpClientMock.post.mockReturnValue(of(mockResponse));

      service.createProvider(request).subscribe({
        next: (provider) => {
          expect(provider).toEqual(mockResponse);
          expect(httpClientMock.post).toHaveBeenCalledWith(
            '/api/admin/gateway/providers',
            request
          );
          done();
        },
      });
    });
  });

  describe('updateProvider', () => {
    it('should update an existing provider', (done) => {
      const request = { is_enabled: false };
      const mockResponse: ProviderConfig = {
        id: '123',
        name: 'OpenAI',
        provider_type: 'openai',
        base_url: 'https://api.openai.com/v1',
        is_enabled: false,
        status: 'disabled',
        priority: 100,
      };

      httpClientMock.put.mockReturnValue(of(mockResponse));

      service.updateProvider('123', request).subscribe({
        next: (provider) => {
          expect(provider).toEqual(mockResponse);
          expect(httpClientMock.put).toHaveBeenCalledWith(
            '/api/admin/gateway/providers/123',
            request
          );
          done();
        },
      });
    });
  });

  describe('deleteProvider', () => {
    it('should delete a provider', (done) => {
      httpClientMock.delete.mockReturnValue(of(undefined));

      service.deleteProvider('123').subscribe({
        next: () => {
          expect(httpClientMock.delete).toHaveBeenCalledWith(
            '/api/admin/gateway/providers/123'
          );
          done();
        },
      });
    });
  });

  describe('testProvider', () => {
    it('should test provider connectivity', (done) => {
      const mockResult = {
        success: true,
        status_code: 200,
        latency_ms: 150,
        message: 'Provider responded in 150ms',
      };

      httpClientMock.post.mockReturnValue(of(mockResult));

      service.testProvider('123').subscribe({
        next: (result) => {
          expect(result).toEqual(mockResult);
          expect(httpClientMock.post).toHaveBeenCalledWith(
            '/api/admin/gateway/providers/123/test',
            {}
          );
          done();
        },
      });
    });
  });
});
