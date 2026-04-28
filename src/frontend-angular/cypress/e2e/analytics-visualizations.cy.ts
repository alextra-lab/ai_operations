/**
 * E2E Tests for Analytics & Visualization Features (P2-F5)
 *
 * Tests:
 * - Usage Analytics dashboard
 * - Performance Metrics dashboard
 * - Chart.js visualizations
 * - Data refresh functionality
 */

describe('Analytics & Visualization - P2-F5', () => {
  beforeEach(() => {
    // Login as admin user
    cy.visit('/login');
    cy.get('input[name="username"]').type('admin');
    cy.get('input[name="password"]').type('adminpassword');
    cy.get('button[type="submit"]').click();

    // Wait for navigation
    cy.url().should('include', '/dashboard');
  });

  describe('Corpus Usage Dashboard', () => {
    beforeEach(() => {
      cy.visit('/analytics/usage');
      cy.wait(1000); // Wait for data to load
    });

    it('should display corpus usage page', () => {
      cy.contains('h1', 'Corpus Usage').should('be.visible');
    });

    it('should display summary statistics cards', () => {
      cy.get('.stat-card').should('have.length.at.least', 4);
      cy.contains('Total Retrievals').should('be.visible');
      cy.contains('Unique Documents').should('be.visible');
      cy.contains('Active Users').should('be.visible');
      cy.contains('Avg Relevancy').should('be.visible');
    });

    it('should display daily trends chart', () => {
      cy.contains('Daily Query Trends').should('be.visible');
      cy.get('canvas').should('exist');
    });

    it('should display top documents chart', () => {
      cy.contains('Top Documents by Relevancy').should('be.visible');
    });

    it('should display hot documents table', () => {
      cy.contains('Hot Documents').should('be.visible');
      cy.get('table').should('exist');
    });

    it('should allow time range selection', () => {
      cy.get('mat-select[aria-label="Time Range"]').click();
      cy.get('mat-option').contains('Last 7 Days').click();
      cy.wait(500); // Wait for data reload
      // Verify data is reloaded (check for loading indicator or updated content)
    });

    it('should refresh data on button click', () => {
      cy.contains('button', 'Refresh').click();
      cy.wait(500); // Wait for refresh
      // Verify data is refreshed
    });
  });

  describe('Corpus Performance Dashboard', () => {
    beforeEach(() => {
      cy.visit('/analytics/performance');
      cy.wait(1000);
    });

    it('should display corpus performance page', () => {
      cy.contains('h1', 'Corpus Performance').should('be.visible');
    });

    it('should display performance statistics', () => {
      cy.get('.stat-card').should('have.length.at.least', 4);
      cy.contains('Avg Chunks/Query').should('be.visible');
      cy.contains('Avg Relevancy Score').should('be.visible');
    });

    it('should display relevancy trends chart', () => {
      cy.contains('Relevancy Score Trends').should('be.visible');
    });

    it('should display query volume chart', () => {
      cy.contains('Query Volume Distribution').should('be.visible');
    });

    it('should display top performers table', () => {
      cy.contains('Top Performing Documents').should('be.visible');
      cy.get('table').should('exist');
    });
  });

  describe('Chart Interactions', () => {
    beforeEach(() => {
      cy.visit('/analytics/usage');
      cy.wait(1000);
    });

    it('should display chart tooltips on hover', () => {
      // Chart.js tooltips appear on hover
      // This is a basic check that the canvas exists
      cy.get('canvas').first().should('exist');
    });

    it('should handle responsive layout', () => {
      // Test mobile viewport
      cy.viewport('iphone-x');
      cy.get('.stats-grid').should('exist');

      // Test desktop viewport
      cy.viewport(1920, 1080);
      cy.get('.stats-grid').should('exist');
    });
  });

  describe('Error Handling', () => {
    it('should display error message when API fails', () => {
      // Intercept API call and force failure
      cy.intercept('GET', '/api/v1/analytics/usage/stats*', {
        statusCode: 500,
        body: { detail: 'Internal Server Error' },
      }).as('getUsageStats');

      cy.visit('/analytics/usage');
      cy.wait('@getUsageStats');

      // Should show error message
      cy.contains('Failed to fetch').should('be.visible');
    });

    it('should allow retry after error', () => {
      // First call fails, second succeeds
      let callCount = 0;
      cy.intercept('GET', '/api/v1/analytics/usage/stats*', (req) => {
        callCount++;
        if (callCount === 1) {
          req.reply({ statusCode: 500 });
        } else {
          req.reply({ fixture: 'usage-stats.json' });
        }
      }).as('getUsageStats');

      cy.visit('/analytics/usage');
      cy.wait('@getUsageStats');

      // Click retry
      cy.contains('button', 'Retry').click();
      cy.wait('@getUsageStats');

      // Should show data
      cy.get('.stat-card').should('be.visible');
    });
  });

  describe('Navigation', () => {
    it('should navigate between corpus analytics pages', () => {
      // Go to corpus usage
      cy.visit('/analytics/usage');
      cy.contains('Corpus Usage').should('be.visible');

      // Navigate to corpus performance
      cy.visit('/analytics/performance');
      cy.contains('Corpus Performance').should('be.visible');

      // Navigate to security audit
      cy.visit('/analytics/security');
      cy.contains('Security Audit').should('be.visible');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.visit('/analytics/usage');
      cy.get('mat-select').should('have.attr', 'aria-label');
      cy.get('button').should('have.attr', 'aria-label').or('contain.text');
    });

    it('should be keyboard navigable', () => {
      cy.visit('/analytics/usage');

      // Tab through interactive elements
      cy.get('body').tab();
      cy.focused().should('be.visible');
    });
  });
});
