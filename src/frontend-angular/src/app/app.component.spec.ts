import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { of } from 'rxjs';

import { AppComponent } from './app.component';
import { routes } from './app.routes';
import { SecurityInitializationService } from './core/security/security-initialization.service';
import { SecurityMonitoringService } from './core/security/security-monitoring.service';

// Mock security services to prevent hanging timers
class MockSecurityInitializationService {
  initializeSecurity() {
    return Promise.resolve();
  }
}

class MockSecurityMonitoringService {
  startMonitoring() {
    return of(null);
  }

  stopMonitoring() {
    // No-op
  }

  logSecurityEvent() {
    return of(null);
  }
}

describe('AppComponent', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent, RouterTestingModule, HttpClientTestingModule],
      providers: [
        provideRouter(routes),
        {
          provide: SecurityInitializationService,
          useClass: MockSecurityInitializationService,
        },
        {
          provide: SecurityMonitoringService,
          useClass: MockSecurityMonitoringService,
        },
        { provide: 'API_BASE_URL', useValue: 'http://localhost:8000' },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    fixture.destroy();
    jest.clearAllTimers();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render router outlet', () => {
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('router-outlet')).toBeTruthy();
  });
});
