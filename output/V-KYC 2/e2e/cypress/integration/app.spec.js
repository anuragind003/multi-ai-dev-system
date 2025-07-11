/// <reference types="cypress" />

describe('Full-Stack Application E2E Tests', () => {
  const FRONTEND_URL = Cypress.env('FRONTEND_URL') || 'http://localhost:3000';
  const BACKEND_URL = Cypress.env('BACKEND_URL') || 'http://localhost:8000';

  beforeEach(() => {
    // Visit the frontend application before each test
    cy.visit(FRONTEND_URL);
  });

  it('should display the main page content', () => {
    cy.contains('Learn React').should('be.visible');
    cy.contains('Edit src/App.js and save to reload.').should('be.visible');
  });

  it('should fetch and display data from the backend', () => {
    // Assuming the frontend makes a request to /api and displays the response
    cy.intercept('GET', `${BACKEND_URL}/`, {
      statusCode: 200,
      body: '<html><body><h1>Hello from Mock Backend!</h1></body></html>',
    }).as('getBackendData');

    // Reload the page to trigger the fetch after intercepting
    cy.reload();

    cy.wait('@getBackendData').its('response.statusCode').should('eq', 200);
    cy.contains('Hello from Mock Backend!').should('be.visible');
  });

  it('should navigate to the backend API docs', () => {
    // This test assumes the frontend has a link or button to the backend docs
    // For this example, we'll directly visit the backend docs URL
    cy.visit(`${BACKEND_URL}/docs`);
    cy.contains('FastAPI Backend API').should('be.visible');
    cy.contains('Swagger UI').should('be.visible');
  });

  it('should verify backend health check', () => {
    cy.request('GET', `${BACKEND_URL}/health`).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.body).to.deep.eq({ status: 'ok', message: 'API is healthy' });
    });
  });

  it('should create an item via backend API', () => {
    const newItem = {
      name: 'E2E Test Item',
      description: 'Created during E2E test',
      price: 99.99,
      tax: 5.00
    };

    cy.request('POST', `${BACKEND_URL}/items/`, newItem).then((response) => {
      expect(response.status).to.eq(201);
      expect(response.body.message).to.eq('Item created successfully');
      expect(response.body.item.name).to.eq(newItem.name);
    });
  });
});