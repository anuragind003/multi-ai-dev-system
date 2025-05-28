describe('Data Download Functionality', () => {
  beforeEach(() => {
    // Assuming the download buttons are on a specific page, e.g., '/downloads' or '/reports'
    // You might need to log in first if the page is protected.
    // For a basic E2E test, we'll assume the page is accessible without prior login.
    cy.visit('/downloads'); // Adjust this path to the actual page where download links/buttons are located
  });

  it('should allow downloading the Moengage-formatted CSV file (FR30)', () => {
    // Intercept the API call for the Moengage file download
    cy.intercept('GET', '/api/exports/moengage-campaign-file').as('downloadMoengageFile');

    // Click the button/link that triggers the Moengage file download
    // Assuming a data-testid attribute for robust selection
    cy.get('[data-testid="download-moengage-btn"]').click();

    // Wait for the intercepted request to complete and assert its status
    cy.wait('@downloadMoengageFile').its('response.statusCode').should('eq', 200);

    // Further assertions could involve checking the downloaded file's content or name,
    // but this often requires specific Cypress plugins (e.g., cypress-downloadfile)
    // or mocking the download process, which is beyond a basic E2E test setup.
    // For now, verifying the API call was made successfully is sufficient.
  });

  it('should allow downloading the Duplicate Data File (FR31)', () => {
    // Intercept the API call for the Duplicate Data file download
    cy.intercept('GET', '/api/exports/duplicate-customers').as('downloadDuplicateFile');

    // Click the button/link that triggers the Duplicate Data file download
    cy.get('[data-testid="download-duplicate-btn"]').click();

    // Wait for the intercepted request to complete and assert its status
    cy.wait('@downloadDuplicateFile').its('response.statusCode').should('eq', 200);
  });

  it('should allow downloading the Unique Data File (FR32)', () => {
    // Intercept the API call for the Unique Data file download
    cy.intercept('GET', '/api/exports/unique-customers').as('downloadUniqueFile');

    // Click the button/link that triggers the Unique Data file download
    cy.get('[data-testid="download-unique-btn"]').click();

    // Wait for the intercepted request to complete and assert its status
    cy.wait('@downloadUniqueFile').its('response.statusCode').should('eq', 200);
  });

  it('should allow downloading the Error Excel file for data uploads (FR33)', () => {
    // Intercept the API call for the Error Excel file download
    cy.intercept('GET', '/api/exports/data-errors').as('downloadErrorFile');

    // Click the button/link that triggers the Error Excel file download
    cy.get('[data-testid="download-error-btn"]').click();

    // Wait for the intercepted request to complete and assert its status
    cy.wait('@downloadErrorFile').its('response.statusCode').should('eq', 200);
  });
});