/**
 * Unit tests for RoleManagementService
 */

import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../../../environments/environment';
import { RoleManagementService } from './role-management.service';

describe('RoleManagementService', () => {
  let service: RoleManagementService;
  let httpMock: HttpTestingController;
  const apiUrl = `${environment.apiBaseUrl}/admin/roles`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [RoleManagementService],
    });

    service = TestBed.inject(RoleManagementService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('assignUseCaseToRole', () => {
    it('should POST request to assign use case to role', () => {
      const roleName = 'analyst';
      const request = {
        use_case_id: '123e4567-e89b-12d3-a456-426614174000',
        metadata: { reason: 'test' },
      };
      const mockResponse = { success: true };

      service.assignUseCaseToRole(roleName, request).subscribe();

      const req = httpMock.expectOne(`${apiUrl}/${roleName}/use-cases`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(request);
      req.flush(mockResponse);
    });
  });

  describe('revokeUseCaseFromRole', () => {
    it('should DELETE request to revoke use case', () => {
      const roleName = 'analyst';
      const useCaseId = '123e4567-e89b-12d3-a456-426614174000';
      const mockResponse = { success: true };

      service.revokeUseCaseFromRole(roleName, useCaseId).subscribe();

      const req = httpMock.expectOne(
        `${apiUrl}/${roleName}/use-cases/${useCaseId}?permanent=false`
      );
      expect(req.request.method).toBe('DELETE');
      req.flush(mockResponse);
    });

    it('should include permanent parameter when specified', () => {
      const roleName = 'analyst';
      const useCaseId = '123e4567-e89b-12d3-a456-426614174000';
      const mockResponse = { success: true };

      service.revokeUseCaseFromRole(roleName, useCaseId, true).subscribe();

      const req = httpMock.expectOne(
        `${apiUrl}/${roleName}/use-cases/${useCaseId}?permanent=true`
      );
      expect(req.request.method).toBe('DELETE');
      req.flush(mockResponse);
    });
  });

  describe('getRoleUseCases', () => {
    it('should GET role use cases', () => {
      const roleName = 'analyst';
      const mockResponse = {
        role_name: 'analyst',
        total: 1,
        active: 1,
        assignments: [],
      };

      service.getRoleUseCases(roleName).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        `${apiUrl}/${roleName}/use-cases?include_inactive=false`
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should include inactive assignments when specified', () => {
      const roleName = 'analyst';
      const mockResponse = {
        role_name: 'analyst',
        total: 0,
        active: 0,
        assignments: [],
      };

      service.getRoleUseCases(roleName, true).subscribe();

      const req = httpMock.expectOne(
        `${apiUrl}/${roleName}/use-cases?include_inactive=true`
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });

  describe('getUseCaseRoles', () => {
    it('should GET roles for a use case', () => {
      const useCaseId = '123e4567-e89b-12d3-a456-426614174000';
      const mockRoles = ['admin', 'analyst'];

      service.getUseCaseRoles(useCaseId).subscribe((roles) => {
        expect(roles).toEqual(mockRoles);
      });

      const req = httpMock.expectOne(`${apiUrl}/use-cases/${useCaseId}/roles`);
      expect(req.request.method).toBe('GET');
      req.flush(mockRoles);
    });
  });

  describe('getAvailableUseCases', () => {
    it('should GET available use cases', () => {
      const mockUseCases = [
        { id: '1', name: 'Test UC 1' },
        { id: '2', name: 'Test UC 2' },
      ];
      const mockResponse = {
        total: 2,
        page: 1,
        page_size: 100,
        total_pages: 1,
        use_cases: mockUseCases,
      };

      service.getAvailableUseCases().subscribe((useCases) => {
        expect(useCases).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url.includes('/admin/use-cases') &&
          request.params.get('page_size') === '100'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });
});
