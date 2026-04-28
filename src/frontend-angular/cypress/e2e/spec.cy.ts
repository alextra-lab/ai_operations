describe('AI Operations Platform (AIOP) UI smoke test', () => {
  it('renders the hero section', () => {
    cy.visit('/');
    cy.findByRole('banner').within(() => {
      cy.contains('AI Operations Platform (AIOP) AI Assist').should('be.visible');
    });
    cy.findByRole('main').within(() => {
      cy.contains('Security Operations Center Assistant').should('be.visible');
      cy.contains('View Phase Plan');
      cy.contains('Start Authentication');
    });
  });
});
