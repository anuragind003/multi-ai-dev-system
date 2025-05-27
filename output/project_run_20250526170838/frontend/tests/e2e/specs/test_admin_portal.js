describe('Admin Portal E2E Tests', () => {
  beforeEach(() => {
    // Visit the admin portal page before each test
    // Assuming the admin portal is accessible at /admin
    cy.visit('/admin');

    // If authentication is required, add login steps here, e.g.:
    // cy.get('[data-cy="username-input"]').type('admin');
    // cy.get('[data-cy="password-input"]').type('password');
    // cy.get('[data-cy="login-button"]').click();
    // cy.url().should('include', '/admin'); // Ensure redirection after login
  });

  context('File Upload Functionality (FR35, FR36, FR37, FR38)', () => {
    const uploadEndpoint = '/admin/customer-data/upload';

    // Note: For these tests to run, ensure the following files exist in `cypress/fixtures/`:
    // - `valid_customer_data.csv` (e.g., "mobile,pan,loan_type\n1234567890,ABCDE1234F,Prospect")
    // - `invalid_customer_data.csv` (e.g., "invalid_column,another_invalid\nvalue1,value2")

    it('should successfully upload a valid customer data file and show success', () => {
      // Intercept the POST request to the upload endpoint
      cy.intercept('POST', uploadEndpoint).as('uploadFile');

      // Select the file using the input element and trigger the upload
      // Assumes 'cypress-file-upload' plugin is installed and configured
      cy.get('input[type="file"][data-cy="customer-upload-input"]').selectFile('valid_customer_data.csv', { force: true });

      // Click the upload button
      cy.get('button[data-cy="upload-submit-button"]').click();

      // Wait for the intercepted request to complete and assert its status code
      cy.wait('@uploadFile').its('response.statusCode').should('eq', 200);

      // Assert that a success message is displayed on the UI
      cy.get('[data-cy="upload-status-message"]').should('be.visible').and('contain', 'File uploaded successfully');
      cy.get('[data-cy="upload-status-message"]').should('contain', 'success_count'); // Check for success count display
    });

    it('should display an error for an invalid customer data file upload', () => {
      // Intercept the POST request and simulate an error response from the backend
      cy.intercept('POST', uploadEndpoint, {
        statusCode: 400,
        body: {
          status: 'error',
          message: 'Invalid file format or data errors detected.',
          error_count: 5,
          log_id: 'some-error-log-id'
        },
      }).as('uploadError');

      // Select the invalid file and trigger upload
      cy.get('input[type="file"][data-cy="customer-upload-input"]').selectFile('invalid_customer_data.csv', { force: true });
      cy.get('button[data-cy="upload-submit-button"]').click();

      // Wait for the intercepted error request
      cy.wait('@uploadError').its('response.statusCode').should('eq', 400);

      // Assert that an error message is displayed on the UI
      cy.get('[data-cy="upload-status-message"]').should('be.visible').and('contain', 'Invalid file format or data errors detected.');
      cy.get('[data-cy="upload-status-message"]').should('contain', 'error_count: 5'); // Check for error count display
      // Optionally, check for a link to download the error file
      cy.get('[data-cy="download-error-file-link"]').should('be.visible');
    });
  });

  context('Data Download Functionality (FR31, FR32, FR33, FR34)', () => {
    it('should allow downloading the Moengage format file', () => {
      // Intercept the GET request for Moengage export
      cy.intercept('GET', '/campaigns/moengage-export').as('downloadMoengage');

      // Click the button to initiate download
      cy.get('[data-cy="download-moengage-button"]').click();

      // Wait for the request to complete and assert its status code
      cy.wait('@downloadMoengage').its('response.statusCode').should('eq', 200);
      // Note: Cypress does not directly verify file content of downloads.
      // This test confirms the API call was successfully made.
    });

    it('should allow downloading the Duplicate Data File', () => {
      cy.intercept('GET', '/data/duplicates').as('downloadDuplicates');
      cy.get('[data-cy="download-duplicates-button"]').click();
      cy.wait('@downloadDuplicates').its('response.statusCode').should('eq', 200);
    });

    it('should allow downloading the Unique Data File', () => {
      cy.intercept('GET', '/data/unique').as('downloadUnique');
      cy.get('[data-cy="download-unique-button"]').click();
      cy.wait('@downloadUnique').its('response.statusCode').should('eq', 200);
    });

    it('should allow downloading the Error Excel file', () => {
      cy.intercept('GET', '/data/errors').as('downloadErrors');
      cy.get('[data-cy="download-errors-button"]').click();
      cy.wait('@downloadErrors').its('response.statusCode').should('eq', 200);
    });
  });

  context('Reporting and Customer View Navigation (FR39, FR40)', () => {
    it('should navigate to the daily reports page', () => {
      // Assuming there's a navigation link or button for daily reports
      cy.get('[data-cy="nav-daily-reports-link"]').click();
      // Assert that the URL has changed to the reports page
      cy.url().should('include', '/admin/reports/daily');
      // Assert that a unique element on the reports page is visible
      cy.get('[data-cy="daily-reports-page-title"]').should('be.visible').and('contain', 'Daily Data Tally Reports');
    });

    it('should navigate to the customer-level view page', () => {
      // Assuming there's a navigation link or button for customer view
      cy.get('[data-cy="nav-customer-view-link"]').click();
      // Assert that the URL has changed to the customer view page
      cy.url().should('include', '/admin/customer-view');
      // Assert that a unique element on the customer view page is visible
      cy.get('[data-cy="customer-view-page-title"]').should('be.visible').and('contain', 'Customer Journey View');
    });
  });
});