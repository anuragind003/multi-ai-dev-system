describe('Admin Portal File Upload Flow', () => {
  beforeEach(() => {
    // Assuming the admin portal upload page is accessible at '/admin/upload'
    // Adjust this path based on the actual frontend routing for the file upload feature.
    cy.visit('/admin/upload');
  });

  it('should successfully upload a valid customer data file for Prospect loans', () => {
    // Load a fixture file for testing a successful upload scenario.
    // This file should be located in `frontend/tests/e2e/fixtures/valid_prospect_data.csv`
    cy.fixture('valid_prospect_data.csv', 'utf-8').then((fileContent) => {
      // Assuming the file input element has a selector like 'input[type="file"]'
      // and the loan type selection element has an ID like '#loan-type-select' (e.g., a dropdown)
      // and the upload button has an ID like '#upload-button'.

      // Attach the file to the input element.
      // `selectFile` is a built-in Cypress command for file uploads.
      cy.get('input[type="file"]').selectFile({
        contents: Cypress.Buffer.from(fileContent),
        fileName: 'valid_prospect_data.csv',
        mimeType: 'text/csv',
      });

      // Select the loan type from the dropdown.
      // If using radio buttons, use `.check()` instead: `cy.get('input[name="loanType"][value="Prospect"]').check();`
      cy.get('#loan-type-select').select('Prospect');

      // Click the upload button to initiate the upload.
      cy.get('#upload-button').click();

      // Assert that a success message is displayed on the UI.
      // The system design indicates success/error counts in the API response,
      // which the frontend should display.
      cy.contains('File uploaded successfully').should('be.visible');
      cy.contains('Success Count:').should('be.visible');
      cy.contains('Error Count: 0').should('be.visible');

      // Optionally, if the UI provides a button/link to download the success file,
      // you can add an assertion here:
      // cy.get('#download-success-file-button').should('be.visible');
    });
  });

  it('should display an error for an invalid customer data file upload', () => {
    // Load a fixture file that represents an invalid data format or content.
    // This file should be located in `frontend/tests/e2e/fixtures/invalid_data.csv`
    cy.fixture('invalid_data.csv', 'utf-8').then((fileContent) => {
      cy.get('input[type="file"]').selectFile({
        contents: Cypress.Buffer.from(fileContent),
        fileName: 'invalid_data.csv',
        mimeType: 'text/csv',
      });

      // Select a loan type, even for an invalid file, as the form might require it.
      cy.get('#loan-type-select').select('Prospect');

      // Click the upload button.
      cy.get('#upload-button').click();

      // Assert that an error message is displayed on the UI.
      // The system design mentions an 'Error Desc' column in the error file,
      // so the frontend should communicate the failure and potentially offer a download.
      cy.contains('File upload failed').should('be.visible');
      cy.contains('Error Description:').should('be.visible'); // Or a more specific error message
      cy.contains('Error Count:').should('be.visible');
      cy.contains('Success Count: 0').should('be.visible');

      // Optionally, if the UI provides a button/link to download the error file,
      // you can add an assertion here:
      // cy.get('#download-error-file-button').should('be.visible');
    });
  });

  it('should successfully upload a valid customer data file for TW Loyalty loans', () => {
    // Test another loan type to ensure the selection mechanism works correctly.
    // This file should be located in `frontend/tests/e2e/fixtures/valid_tw_loyalty_data.csv`
    cy.fixture('valid_tw_loyalty_data.csv', 'utf-8').then((fileContent) => {
      cy.get('input[type="file"]').selectFile({
        contents: Cypress.Buffer.from(fileContent),
        fileName: 'valid_tw_loyalty_data.csv',
        mimeType: 'text/csv',
      });
      cy.get('#loan-type-select').select('TW Loyalty');
      cy.get('#upload-button').click();
      cy.contains('File uploaded successfully').should('be.visible');
      cy.contains('Success Count:').should('be.visible');
      cy.contains('Error Count: 0').should('be.visible');
    });
  });

  // Additional tests can be added here for other loan types (Topup, Employee loans)
  // or specific validation scenarios (e.g., missing required columns, invalid data types).
});