import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { SecurityMonitoringService } from '../../core/security/security-monitoring.service';
import { SecurityHeadersService } from '../../core/services/security-headers.service';
import { SecurityDashboardComponent } from './security-dashboard.component';

describe('SecurityDashboardComponent', () => {
  let component: SecurityDashboardComponent;
  let fixture: ComponentFixture<SecurityDashboardComponent>;
  let mockSecurityMonitoring: Partial<SecurityMonitoringService>;
  let mockSecurityHeaders: Partial<SecurityHeadersService>;

  beforeEach(async () => {
    const securityMonitoringSpy = {
      getSecurityEvents: jest.fn(),
      getSecurityAlerts: jest.fn(),
      getSecurityMetrics: jest.fn(),
      clearSecurityData: jest.fn(),
      logSecurityEvent: jest.fn(),
    };

    const securityHeadersSpy = {
      validateSecurityHeaders: jest.fn(),
      validateCSP: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [SecurityDashboardComponent, NoopAnimationsModule],
      providers: [
        { provide: SecurityMonitoringService, useValue: securityMonitoringSpy },
        { provide: SecurityHeadersService, useValue: securityHeadersSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SecurityDashboardComponent);
    component = fixture.componentInstance;
    mockSecurityMonitoring = TestBed.inject(SecurityMonitoringService) as any;
    mockSecurityHeaders = TestBed.inject(SecurityHeadersService) as any;

    // Setup default mock return values
    mockSecurityMonitoring.getSecurityEvents.mockReturnValue(of([]));
    mockSecurityMonitoring.getSecurityAlerts.mockReturnValue(of([]));
    mockSecurityMonitoring.getSecurityMetrics.mockReturnValue({
      totalEvents: 0,
      recentEvents: 0,
      totalAlerts: 0,
      recentAlerts: 0,
      violationCount: 0,
      riskLevel: 'low',
      lastUpdated: new Date().toISOString(),
    });
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load security data on init', () => {
    component.ngOnInit();
    expect(mockSecurityMonitoring.getSecurityEvents).toHaveBeenCalled();
    expect(mockSecurityMonitoring.getSecurityAlerts).toHaveBeenCalled();
    expect(mockSecurityMonitoring.getSecurityMetrics).toHaveBeenCalled();
  });

  it('should refresh security data', () => {
    component.refreshSecurityData();
    expect(mockSecurityMonitoring.getSecurityEvents).toHaveBeenCalled();
    expect(mockSecurityMonitoring.getSecurityAlerts).toHaveBeenCalled();
    expect(mockSecurityMonitoring.getSecurityMetrics).toHaveBeenCalled();
  });

  it('should clear security data', () => {
    component.clearSecurityData();
    expect(mockSecurityMonitoring.clearSecurityData).toHaveBeenCalled();
  });

  it('should test security features', () => {
    component.testSecurityFeatures();
    expect(mockSecurityMonitoring.logSecurityEvent).toHaveBeenCalledTimes(2);
  });

  it('should get correct score color', () => {
    expect(component.getScoreColor(95)).toBe('primary');
    expect(component.getScoreColor(75)).toBe('accent');
    expect(component.getScoreColor(50)).toBe('warn');
  });

  it('should get correct risk color', () => {
    expect(component.getRiskColor('low')).toBe('primary');
    expect(component.getRiskColor('medium')).toBe('accent');
    expect(component.getRiskColor('high')).toBe('warn');
    expect(component.getRiskColor('critical')).toBe('warn');
  });
});
