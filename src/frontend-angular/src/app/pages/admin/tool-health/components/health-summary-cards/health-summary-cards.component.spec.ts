/**
 * Health Summary Cards Component Unit Tests
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { By } from '@angular/platform-browser';

import { HealthSummary } from '../../models/tool-health.models';
import { HealthSummaryCardsComponent } from './health-summary-cards.component';

describe('HealthSummaryCardsComponent', () => {
  let component: HealthSummaryCardsComponent;
  let fixture: ComponentFixture<HealthSummaryCardsComponent>;

  const mockSummary: HealthSummary = {
    total_tools: 10,
    online: 8,
    offline: 2,
    health_percentage: 80.0,
    last_check: '2025-11-24T10:00:00Z',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        HealthSummaryCardsComponent,
        MatCardModule,
        MatIconModule,
        MatProgressSpinnerModule,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HealthSummaryCardsComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('with summary data', () => {
    beforeEach(() => {
      component.summary = mockSummary;
      component.isLoading = false;
      fixture.detectChanges();
    });

    it('should display total tools count', () => {
      const cards = fixture.debugElement.queryAll(By.css('.summary-card'));
      expect(cards.length).toBe(4);

      const totalCard = fixture.debugElement.query(
        By.css('.summary-card:first-child .card-value')
      );
      expect(totalCard.nativeElement.textContent.trim()).toBe('10');
    });

    it('should display online tools count', () => {
      const onlineCard = fixture.debugElement.query(
        By.css('.summary-card.online .card-value')
      );
      expect(onlineCard.nativeElement.textContent.trim()).toBe('8');
    });

    it('should display offline tools count', () => {
      const offlineCard = fixture.debugElement.query(
        By.css('.summary-card.offline .card-value')
      );
      expect(offlineCard.nativeElement.textContent.trim()).toBe('2');
    });

    it('should display health percentage', () => {
      const healthCard = fixture.debugElement.query(
        By.css('.summary-card.health .card-value')
      );
      expect(healthCard.nativeElement.textContent.trim()).toContain('80');
    });

    it('should display last check timestamp', () => {
      const lastCheck = fixture.debugElement.query(
        By.css('.last-check-info .timestamp-text')
      );
      expect(lastCheck.nativeElement.textContent).toContain(
        'Last health check'
      );
    });
  });

  describe('loading state', () => {
    beforeEach(() => {
      component.isLoading = true;
      fixture.detectChanges();
    });

    it('should show spinners when loading', () => {
      const spinners = fixture.debugElement.queryAll(By.css('mat-spinner'));
      expect(spinners.length).toBe(4);
    });

    it('should not show values when loading', () => {
      // Elements with *ngIf="!isLoading" are removed from DOM when loading
      const values = fixture.debugElement.queryAll(By.css('.card-value'));
      expect(values.length).toBe(0);
    });
  });

  describe('getHealthColor', () => {
    it('should return "healthy" for percentage >= 80', () => {
      component.summary = { ...mockSummary, health_percentage: 85 };
      expect(component.getHealthColor()).toBe('healthy');
    });

    it('should return "warning" for percentage between 50 and 80', () => {
      component.summary = { ...mockSummary, health_percentage: 65 };
      expect(component.getHealthColor()).toBe('warning');
    });

    it('should return "critical" for percentage < 50', () => {
      component.summary = { ...mockSummary, health_percentage: 30 };
      expect(component.getHealthColor()).toBe('critical');
    });

    it('should return "neutral" when no summary', () => {
      component.summary = null;
      expect(component.getHealthColor()).toBe('neutral');
    });
  });

  describe('formatLastCheck', () => {
    it('should format timestamp correctly', () => {
      component.summary = mockSummary;
      const result = component.formatLastCheck();
      expect(result).not.toBe('Never checked');
    });

    it('should return "Never checked" when no timestamp', () => {
      component.summary = { ...mockSummary, last_check: null };
      expect(component.formatLastCheck()).toBe('Never checked');
    });

    it('should return "Never checked" when no summary', () => {
      component.summary = null;
      expect(component.formatLastCheck()).toBe('Never checked');
    });
  });

  describe('accessibility', () => {
    beforeEach(() => {
      component.summary = mockSummary;
      component.isLoading = false;
      fixture.detectChanges();
    });

    it('should have aria-label on container', () => {
      const container = fixture.debugElement.query(
        By.css('.summary-cards-container')
      );
      expect(container.attributes['aria-label']).toBe('Tool Health Summary');
    });

    it('should have role="region" on container', () => {
      const container = fixture.debugElement.query(
        By.css('.summary-cards-container')
      );
      expect(container.attributes['role']).toBe('region');
    });
  });
});
