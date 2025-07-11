/// <reference types="cypress" />

describe('Frontend Application E2E Tests', () => {
  const FE_URL = Cypress.env('FRONTEND_URL') || 'http://localhost:3000';
  const BE_URL = Cypress.env('BACKEND_URL') || 'http://localhost:8000';

  beforeEach(() => {
    // Visit the frontend application before each test
    cy.visit(FE_URL);
  });

  it('should display the main page title', () => {
    // Check if the main heading exists and contains expected text
    cy.get('h1').should('exist').and('contain', 'Welcome to Next.js!');
  });

  it('should display a link to the API documentation', () => {
    // Check for a link that points to the backend API docs
    cy.get('a[href*="/docs"]').should('exist').and('contain', 'API Docs');
  });

  it('should fetch and display items from the backend', () => {
    // Intercept the API call to the backend to ensure it's made and responds correctly
    cy.intercept('GET', `${BE_URL}/items`).as('getItems');

    // Assuming there's a button or action to trigger fetching items
    // If items are fetched on page load, this part might be implicit
    // For this example, let's assume a button exists to "Load Items"
    // If not, you might need to adjust your frontend to have such a trigger for testing.
    // For now, we'll just wait for the intercept to complete, assuming items load on page.

    cy.wait('@getItems').then((interception) => {
      // Assert that the API call was successful
      expect(interception.response.statusCode).to.eq(200);
      expect(interception.response.body).to.be.an('array').and.not.be.empty;

      // Check if the fetched items are displayed on the page
      // This assumes your frontend renders items in a list or similar structure
      cy.get('[data-cy="item-list"]').should('exist');
      cy.get('[data-cy="item-list-item"]').should('have.length.at.least', 1);
      cy.get('[data-cy="item-list-item"]').first().should('contain', 'Item 1'); // Check for specific item content
    });
  });

  it('should navigate to the API documentation link', () => {
    // Find the API docs link and click it
    cy.get('a[href*="/docs"]').click();

    // Verify that the browser navigated to the backend API docs URL
    cy.url().should('include', '/docs');
    // You might also want to check for specific content on the Swagger UI page
    cy.contains('Swagger UI').should('exist');
  });

  it('should display a health status from the backend', () => {
    // Intercept the health check API call
    cy.intercept('GET', `${BE_URL}/health`).as('getHealth');

    // Assuming there's a UI element that displays health status
    // If not, this test might be more about ensuring the backend is reachable.
    // For this example, let's assume a "Check Health" button.
    // cy.get('[data-cy="check-health-button"]').click();

    cy.wait('@getHealth').then((interception) => {
      expect(interception.response.statusCode).to.eq(200);
      expect(interception.response.body.status).to.eq('ok');
      expect(interception.response.body.message).to.include('healthy');

      // If your frontend displays this, check the UI
      // cy.get('[data-cy="health-status"]').should('contain', 'ok');
    });
  });

  // Example of a test for a non-existent item (if your frontend handles it)
  it('should handle non-existent item gracefully', () => {
    // Mock a 404 response for a specific item ID
    cy.intercept('GET', `${BE_URL}/items/999`, {
      statusCode: 404,
      body: { detail: 'Item not found' },
    }).as('getNonExistentItem');

    // Assuming there's a way to request a specific item, e.g., via a search box or direct link
    // For this example, we'll just trigger the intercept and check for error handling in UI
    // cy.get('[data-cy="item-search-input"]').type('999');
    // cy.get('[data-cy="item-search-button"]').click();

    cy.wait('@getNonExistentItem').then(() => {
      // Check if the frontend displays an appropriate error message
      // cy.get('[data-cy="error-message"]').should('contain', 'Item not found');
    });
  });
});