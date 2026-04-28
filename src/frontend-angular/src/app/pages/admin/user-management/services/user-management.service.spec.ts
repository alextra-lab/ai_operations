import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../../../environments/environment';
import { UserManagementService } from './user-management.service';

describe('UserManagementService', () => {
  let service: UserManagementService;
  let httpMock: HttpTestingController;
  const apiUrl = `${environment.apiBaseUrl}/auth/users`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [UserManagementService],
    });

    service = TestBed.inject(UserManagementService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should list users', () => {
    const mockResponse = {
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    };

    service.listUsers().subscribe((response) => {
      expect(response).toEqual(mockResponse);
    });

    const req = httpMock.expectOne(apiUrl);
    expect(req.request.method).toBe('GET');
    req.flush(mockResponse);
  });

  it('should create user', () => {
    const mockUser = {
      username: 'newuser',
      password: 'password123',
      full_name: 'New User',
      role: 'user',
    };

    service.createUser(mockUser).subscribe();

    const req = httpMock.expectOne(apiUrl);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(mockUser);
    req.flush({ id: '123', ...mockUser });
  });

  it('should update user', () => {
    const userId = '123';
    const updates = { full_name: 'Updated Name' };

    service.updateUser(userId, updates).subscribe();

    const req = httpMock.expectOne(`${apiUrl}/${userId}`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual(updates);
    req.flush({ success: true });
  });

  it('should deactivate user', () => {
    const userId = '123';

    service.deactivateUser(userId).subscribe();

    const req = httpMock.expectOne(`${apiUrl}/${userId}`);
    expect(req.request.method).toBe('DELETE');
    req.flush({ message: 'User deactivated' });
  });

  it('should get user sessions', () => {
    const userId = '123';
    const mockSessions = [
      {
        id: 'session1',
        created_at: '2025-01-01',
        last_activity: '2025-01-01',
        expires_at: '2025-01-08',
        revoked: false,
      },
    ];

    service.getUserSessions(userId).subscribe((sessions) => {
      expect(sessions).toEqual(mockSessions);
    });

    const req = httpMock.expectOne(`${apiUrl}/${userId}/sessions`);
    expect(req.request.method).toBe('GET');
    req.flush(mockSessions);
  });

  it('should force logout', () => {
    const userId = '123';
    const sessionId = 'session1';

    service.forceLogout(userId, sessionId).subscribe();

    const req = httpMock.expectOne(`${apiUrl}/${userId}/sessions/${sessionId}`);
    expect(req.request.method).toBe('DELETE');
    req.flush({ message: 'Session revoked' });
  });
});
