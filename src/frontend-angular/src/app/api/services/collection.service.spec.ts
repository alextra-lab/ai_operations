/**
 * Unit tests for CollectionService
 *
 * Tests HTTP requests, URL construction, and error handling
 * for collection management operations.
 */

import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../environments/environment';
import {
  Collection,
  CollectionCreate,
  CollectionListResponse,
  CollectionUpdate,
} from '../models/collection.models';
import { CollectionService } from './collection.service';

describe('CollectionService', () => {
  let service: CollectionService;
  let httpMock: HttpTestingController;
  const baseUrl = `${environment.apiBaseUrl}/admin/collections/`;
  const publicUrl = `${environment.apiBaseUrl}/admin/collections`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [CollectionService],
    });

    service = TestBed.inject(CollectionService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    // Verify no outstanding HTTP requests
    httpMock.verify();
  });

  describe('URL Structure', () => {
    it('should have baseUrl with trailing slash', () => {
      expect((service as any).baseUrl).toBe(baseUrl);
      expect((service as any).baseUrl.endsWith('/')).toBe(true);
    });

    it('should have publicUrl without trailing slash', () => {
      expect((service as any).publicUrl).toBe(publicUrl);
    });
  });

  describe('listCollections', () => {
    it('should call listAvailableCollections internally', () => {
      // listCollections currently delegates to listAvailableCollections
      // which uses the /available endpoint
      const mockResponse: CollectionListResponse = {
        collections: [],
        total: 0,
        skip: 0,
        limit: 100,
      };

      service.listCollections().subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      // Expects the available endpoint since listCollections delegates to it
      const req = httpMock.expectOne(`${publicUrl}/available`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should ignore parameters since it delegates to listAvailableCollections', () => {
      // Parameters are ignored because the method delegates
      service.listCollections(false, 'test-model', 10, 50).subscribe();

      const req = httpMock.expectOne(`${publicUrl}/available`);
      req.flush({ collections: [], total: 0, skip: 0, limit: 100 });
    });
  });

  describe('getCollection', () => {
    it('should make GET request to correct URL', () => {
      const collectionId = '123e4567-e89b-12d3-a456-426614174000';
      const mockCollection: Collection = {
        id: collectionId,
        name: 'test',
        description: 'Test',
        embedding_model: 'test-model',
        embedding_provider: 'openai',
        embedding_dimensions: 1536,
        qdrant_collection_name: 'fc_test',
        is_default: false,
        is_active: true,
        is_system_managed: false,
        created_by: 'user',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        document_count: 0,
      };

      service.getCollection(collectionId).subscribe((collection) => {
        expect(collection).toEqual(mockCollection);
      });

      const req = httpMock.expectOne(`${baseUrl}${collectionId}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockCollection);
    });
  });

  describe('createCollection', () => {
    it('should make POST request to baseUrl with trailing slash', () => {
      const newCollection: CollectionCreate = {
        name: 'test_collection',
        description: 'Test collection',
        embedding_model: 'text-embedding-3-small',
        embedding_provider: 'openai',
        embedding_dimensions: 1536,
      };

      const mockResponse: Collection = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        ...newCollection,
        qdrant_collection_name: 'fc_test_collection',
        is_default: false,
        is_active: true,
        is_system_managed: false,
        created_by: 'admin',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        document_count: 0,
      };

      service.createCollection(newCollection).subscribe((collection) => {
        expect(collection).toEqual(mockResponse);
      });

      const req = httpMock.expectOne((request) => {
        return request.url === baseUrl && request.method === 'POST';
      });

      // Critical: Verify POST goes to URL with trailing slash
      expect(req.request.url).toBe(baseUrl);
      expect(req.request.url.endsWith('/')).toBe(true);
      expect(req.request.body).toEqual(newCollection);

      req.flush(mockResponse);
    });

    it('should handle validation errors', () => {
      const invalidCollection: CollectionCreate = {
        name: 'ab', // Too short
        description: '',
        embedding_model: 'test',
        embedding_provider: 'openai',
        embedding_dimensions: 1536,
      };

      service.createCollection(invalidCollection).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(422);
        },
      });

      const req = httpMock.expectOne(baseUrl);
      req.flush(
        { detail: 'Validation error' },
        { status: 422, statusText: 'Unprocessable Entity' }
      );
    });
  });

  describe('updateCollection', () => {
    it('should make PUT request to correct URL', () => {
      const collectionId = '123e4567-e89b-12d3-a456-426614174000';
      const update: CollectionUpdate = {
        description: 'Updated description',
        is_active: false,
      };

      const mockResponse: Collection = {
        id: collectionId,
        name: 'test',
        description: 'Updated description',
        embedding_model: 'test-model',
        embedding_provider: 'openai',
        embedding_dimensions: 1536,
        qdrant_collection_name: 'fc_test',
        is_default: false,
        is_active: false,
        is_system_managed: false,
        created_by: 'user',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        document_count: 0,
      };

      service.updateCollection(collectionId, update).subscribe((collection) => {
        expect(collection).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${baseUrl}${collectionId}`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(update);
      req.flush(mockResponse);
    });
  });

  describe('deleteCollection', () => {
    it('should make DELETE request to correct URL', () => {
      const collectionId = '123e4567-e89b-12d3-a456-426614174000';

      service.deleteCollection(collectionId).subscribe(() => {
        // Success
      });

      const req = httpMock.expectOne(`${baseUrl}${collectionId}`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null, { status: 204, statusText: 'No Content' });
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', () => {
      // Use getCollection to test error handling since listCollections
      // delegates to listAvailableCollections
      service.getCollection('test-id').subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(0);
          expect(error.statusText).toBe('Unknown Error');
        },
      });

      const req = httpMock.expectOne(`${baseUrl}test-id`);
      req.error(new ProgressEvent('error'));
    });

    it('should handle 403 Forbidden', () => {
      service.getCollection('test-id').subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(403);
        },
      });

      const req = httpMock.expectOne(`${baseUrl}test-id`);
      req.flush(
        { detail: 'Access denied' },
        { status: 403, statusText: 'Forbidden' }
      );
    });

    it('should handle 500 Internal Server Error', () => {
      service.getCollection('test-id').subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(500);
        },
      });

      const req = httpMock.expectOne(`${baseUrl}test-id`);
      req.flush(
        { detail: 'Internal server error' },
        { status: 500, statusText: 'Internal Server Error' }
      );
    });
  });
});
