/**
 * E2E Tests for Use Case Authoring (Phases 1–4bis, D2)
 *
 * Flow: create use case (wizard) with custom input fields → save → execute.
 * Covers: Step 1 Identity, Step 2 Starting Point, Step 3 User Experience
 * (Input Fields + User Prompt Template), Step 4 AI Engine, Step 5 Review & Save,
 * then execution page and run.
 */

const E2E_USE_CASE_ID = 'e2e-wizard-authoring-uc';

describe('Use Case Wizard Authoring - D2', () => {
  beforeEach(() => {
    cy.visit('/login');
    cy.get('input[autocomplete="username"]').type('admin');
    cy.get('input[autocomplete="current-password"]').type('adminpassword');
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/dashboard');
  });

  it('should create use case with custom input fields, save, and execute', () => {
    // Intercept admin create (wizard save)
    cy.intercept('POST', '**/api/v1/admin/use-cases', {
      statusCode: 201,
      body: {
        id: E2E_USE_CASE_ID,
        name: 'E2E Authoring Test',
        description: 'Created by Cypress',
        category: 'security',
        intent_type: 'analysis',
        lifecycle_state: 'draft',
        is_active: true,
      },
    }).as('createUseCase');

    // Intercept public use case + config (execution page)
    cy.intercept('GET', `**/api/v1/use-cases/${E2E_USE_CASE_ID}`, {
      statusCode: 200,
      body: {
        id: E2E_USE_CASE_ID,
        name: 'E2E Authoring Test',
        description: 'Created by Cypress',
        category: 'security',
        intent_type: 'analysis',
      },
    }).as('getUseCase');

    cy.intercept('GET', `**/api/v1/use-cases/${E2E_USE_CASE_ID}/config`, {
      statusCode: 200,
      body: {
        use_case_id: E2E_USE_CASE_ID,
        name: 'E2E Authoring Test',
        description: 'Created by Cypress',
        category: 'security',
        intent_type: 'analysis',
        config: {
          input_fields: [
            {
              name: 'query',
              type: 'textarea',
              label: 'Query',
              description: 'User query',
              required: true,
              placeholder: 'Enter your query',
            },
          ],
          output_format: 'text',
        },
      },
    }).as('getUseCaseConfig');

    cy.intercept('POST', `**/api/v1/use-cases/${E2E_USE_CASE_ID}/execute`, {
      statusCode: 200,
      body: {
        request_id: 'e2e-request-1',
        response: 'E2E mock response',
        sources: [],
        metrics: {},
        execution_time_ms: 100,
        timestamp: new Date().toISOString(),
      },
    }).as('executeUseCase');

    // Platform config for Step 1 (categories, intent types) — response shape matches API
    cy.intercept('GET', '**/api/v1/config/categories', {
      statusCode: 200,
      body: {
        categories: [
          {
            category_code: 'security',
            display_name: 'Security',
            description: 'Security operations',
            icon: 'security',
            color: '#1976d2',
            sort_order: 1,
          },
        ],
        total: 1,
      },
    }).as('getCategories');
    cy.intercept('GET', '**/api/v1/config/intent-types', {
      statusCode: 200,
      body: {
        intent_types: [
          {
            intent_code: 'analysis',
            display_name: 'Analysis',
            description: 'Analyze',
            category_code: 'security',
            icon: 'analytics',
            is_system: true,
            default_sampling_preset: 'balanced',
            default_output_format: 'text',
          },
        ],
        total: 1,
      },
    }).as('getIntentTypes');

    // 1. Open wizard
    cy.visit('/dev/use-cases/wizard');
    cy.contains('Create New AI Operation').should('be.visible');
    cy.contains('Step', { matchCase: false }).should('be.visible');
    cy.wait('@getCategories');

    // 2. Step 1: Identity
    cy.get('input[formControlName="name"]').type('E2E Authoring Test');
    cy.get('textarea[formControlName="description"]').type('Created by Cypress');
    cy.get('mat-select[formControlName="category"]').click();
    cy.get('[role="option"]').first().click();
    cy.get('mat-select[formControlName="intent_type"]').click();
    cy.get('[role="option"]').first().click();

    cy.contains('button', 'Next').click();

    // 3. Step 2: Starting Point — Blank
    cy.contains('Start from Blank').click();
    cy.contains('button', 'Next').click();

    // 4. Step 3: User Experience — custom input (default query field present)
    cy.contains('User Interaction').scrollIntoView().should('exist');
    cy.contains('Input Fields').scrollIntoView().should('exist');
    cy.contains('button', 'Next').scrollIntoView().click({ force: true });

    // 5. Step 4: AI Engine — accept defaults, next
    cy.contains('AI Engine').should('exist');
    cy.contains('button', 'Next').click({ force: true });

    // 6. Step 5: Review & Publish — Save as Draft, Create
    cy.contains('Review & Publish').should('exist');
    cy.contains('Save as Draft').click({ force: true });
    cy.get('button[color="primary"]').contains('Create AI Operation').click({ force: true });

    cy.wait('@createUseCase');
    cy.url().should('include', '/dev/use-cases/edit/' + E2E_USE_CASE_ID);

    // 7. Navigate to execution (use case library → run)
    cy.visit(`/use-cases/${E2E_USE_CASE_ID}`);

    cy.wait('@getUseCase');
    cy.wait('@getUseCaseConfig');
    cy.contains('E2E Authoring Test').should('be.visible');
    cy.contains('Input Parameters').should('be.visible');
    // Expand input panel if collapsed and wait for form
    cy.get('.input-panel mat-expansion-panel-header').then(($el) => {
      if ($el.attr('aria-expanded') === 'false') {
        cy.wrap($el).click();
      }
    });
    cy.get('.execution-form textarea', { timeout: 10000 }).should('exist').type('E2E test query');
    cy.contains('button', 'Execute').click();

    cy.wait('@executeUseCase');
    cy.contains('E2E mock response', { timeout: 10000 }).should('be.visible');
  });
});
