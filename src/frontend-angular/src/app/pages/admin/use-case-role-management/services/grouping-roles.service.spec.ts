import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { GroupingRoleInfo } from '../../role-management/models/role-management.models';
import { GroupingRolesService } from './grouping-roles.service';

describe('GroupingRolesService', () => {
  let service: GroupingRolesService;
  let httpMock: HttpTestingController;

  const apiUrl = '/api/v1/admin/grouping-roles';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [GroupingRolesService],
    });

    service = TestBed.inject(GroupingRolesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should list roles', () => {
    const mockRoles: GroupingRoleInfo[] = [
      {
        role_name: 'threat_hunting',
        user_count: 1,
        use_case_count: 2,
        collection_count: 0,
      },
    ];

    service.listRoles().subscribe((roles) => {
      expect(roles).toEqual(mockRoles);
    });

    const req = httpMock.expectOne(apiUrl);
    expect(req.request.method).toBe('GET');
    req.flush(mockRoles);
  });

  it('should create role', () => {
    const payload = { role_name: 'threat_hunting' };

    service.createRole(payload.role_name).subscribe();

    const req = httpMock.expectOne(apiUrl);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({});
  });

  it('should delete role', () => {
    service.deleteRole('threat_hunting').subscribe();

    const req = httpMock.expectOne(`${apiUrl}/threat_hunting`);
    expect(req.request.method).toBe('DELETE');
    req.flush({});
  });
});
