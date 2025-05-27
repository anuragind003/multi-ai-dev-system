describe('Admin Portal Functionality', () => {
  beforeEach(() => {
    // Assuming the admin portal is accessible at '/admin-portal'
    // Adjust this URL based on your actual frontend routing
    cy.visit('/admin-portal');
    // Optionally, if authentication is required, add login steps here:
    // cy.login('adminUser', 'adminPassword');
  });

  it('should display the Admin Portal dashboard/upload section', () => {
    // Assuming there's a main heading or a specific element that indicates the admin portal page
    cy.get('h1').should('contain', 'Admin Portal');
    cy.contains('Upload Customer Data').should('be.visible');
    cy.contains('Download Reports').should('be.visible');
    cy.contains('View Reports').should('be.visible');
  });

  context('Customer Data Upload', () => {
    const uploadEndpoint = '/admin/customer-data/upload';
    const successFileName = 'prospect_customers.csv';
    const errorFileName = 'invalid_customers.csv';

    it('should successfully upload a customer data file and display success message', () => {
      // Mock the successful API response for file upload
      cy.intercept('POST', uploadEndpoint, {
        statusCode: 200,
        body: {
          status: 'success',
          log_id: 'a1b2c3d4-e5f6-7890-1234-567890abcdef',
          success_count: 100,
          error_count: 0,
          message: 'File uploaded and processed successfully.'
        }
      }).as('uploadSuccess');

      // Create dummy CSV content for a successful upload
      const fileContent = `mobile_number,pan_number,loan_type,name
1234567890,ABCDE1234F,Prospect,John Doe
0987654321,FGHIJ5678K,TW Loyalty,Jane Smith`;

      // Select the file input element and attach the dummy file
      // Use data-cy attributes for robust selectors if available in your actual HTML
      cy.get('input[type="file"][data-cy="customer-upload-input"]').selectFile({
        contents: Cypress.Buffer.from(fileContent),
        fileName: successFileName,
        mimeType: 'text/csv',
        lastModified: Date.now(),
      }, { force: true }); // force: true can be used if the input is hidden or covered by another element

      // Select the loan type (assuming a dropdown or radio buttons)
      cy.get('[data-cy="loan-type-select"]').select('Prospect'); // Or click a radio button like cy.get('[data-cy="loan-type-prospect"]').click();

      // Click the upload button
      cy.get('[data-cy="upload-button"]').click();

      // Wait for the mocked API call to complete and assert its properties
      cy.wait('@uploadSuccess').its('request.body').should('include', 'file_name');
      cy.wait('@uploadSuccess').its('request.body').should('include', 'loan_type');

      // Assert that success messages are displayed on the UI
      cy.contains('File uploaded and processed successfully.').should('be.visible');
      cy.contains('Success Count: 100').should('be.visible');
      cy.contains('Error Count: 0').should('be.visible');
    });

    it('should display an error message for a failed file upload', () => {
      // Mock the failed API response for file upload
      cy.intercept('POST', uploadEndpoint, {
        statusCode: 400,
        body: {
          status: 'error',
          message: 'Invalid file format or data validation errors.',
          error_details: [
            { row: 2, column: 'mobile_number', description: 'Invalid mobile number format' },
            { row: 3, column: 'pan_number', description: 'PAN number missing' }
          ]
        }
      }).as('uploadFailure');

      // Create dummy CSV content for a failed upload
      const fileContent = `mobile_number,pan_number,loan_type,name
INVALID_MOBILE,,Prospect,Test User`;

      cy.get('input[type="file"][data-cy="customer-upload-input"]').selectFile({
        contents: Cypress.Buffer.from(fileContent),
        fileName: errorFileName,
        mimeType: 'text/csv',
        lastModified: Date.now(),
      }, { force: true });

      cy.get('[data-cy="loan-type-select"]').select('Prospect');
      cy.get('[data-cy="upload-button"]').click();

      // Wait for the mocked API call to complete
      cy.wait('@uploadFailure');

      // Assert that error messages are displayed on the UI
      cy.contains('File upload failed: Invalid file format or data validation errors.').should('be.visible');
      cy.contains('Invalid mobile number format').should('be.visible');
      cy.contains('PAN number missing').should('be.visible');
    });
  });

  context('Data Download Functionality', () => {
    it('should allow downloading the Moengage format file', () => {
      // Mock the API response for Moengage export
      cy.intercept('GET', '/campaigns/moengage-export', {
        statusCode: 200,
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': 'attachment; filename="moengage_export.csv"'
        },
        body: 'customer_id,mobile,offer_id,campaign_name\n1,1234567890,O1,CampaignA\n2,0987654321,O2,CampaignB'
      }).as('downloadMoengage');

      // Click the download button for Moengage file
      cy.get('[data-cy="download-moengage-button"]').click();

      // Verify that the API call was made successfully
      cy.wait('@downloadMoengage').its('response.statusCode').should('eq', 200);
      // Note: Cypress cannot directly verify the downloaded file content or save location.
      // This test primarily verifies the frontend action triggers the correct backend call.
    });

    it('should allow downloading the Duplicate Data File', () => {
      // Mock the API response for duplicate data download
      cy.intercept('GET', '/data/duplicates', {
        statusCode: 200,
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': 'attachment; filename="duplicate_data.csv"'
        },
        body: 'customer_id,mobile,pan,reason\n1,123,ABC,DuplicateMobile\n3,456,DEF,DuplicatePAN'
      }).as('downloadDuplicates');

      // Click the download button for duplicate data
      cy.get('[data-cy="download-duplicates-button"]').click();
      cy.wait('@downloadDuplicates').its('response.statusCode').should('eq', 200);
    });

    it('should allow downloading the Unique Data File', () => {
      // Mock the API response for unique data download
      cy.intercept('GET', '/data/unique', {
        statusCode: 200,
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': 'attachment; filename="unique_data.csv"'
        },
        body: 'customer_id,mobile,pan\n10,111,XYZ\n11,222,PQR'
      }).as('downloadUnique');

      // Click the download button for unique data
      cy.get('[data-cy="download-unique-button"]').click();
      cy.wait('@downloadUnique').its('response.statusCode').should('eq', 200);
    });

    it('should allow downloading the Error Excel file', () => {
      // Mock the API response for error file download
      cy.intercept('GET', '/data/errors', {
        statusCode: 200,
        headers: {
          'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'Content-Disposition': 'attachment; filename="error_log.xlsx"'
        },
        // In a real test, you might provide a base64 encoded Excel file content.
        // For a mock, just ensuring the headers are correct is often sufficient.
        body: 'dummy excel content representing an XLSX file'
      }).as('downloadErrors');

      // Click the download button for error file
      cy.get('[data-cy="download-errors-button"]').click();
      cy.wait('@downloadErrors').its('response.statusCode').should('eq', 200);
    });
  });

  context('Reporting Views', () => {
    it('should navigate to and display daily reports for data tally', () => {
      // Assuming there's a link or button to navigate to daily reports
      cy.get('[data-cy="view-daily-reports-button"]').click();
      cy.url().should('include', '/admin-portal/daily-reports');
      cy.get('h2').should('contain', 'Daily Data Tally Reports');
      // Further assertions for report content can be added here, e.g., checking table presence
      cy.get('[data-cy="daily-report-table"]').should('be.visible');
    });

    it('should navigate to and display customer-level view with stages', () => {
      // Assuming there's a link or button to navigate to customer view
      cy.get('[data-cy="view-customer-level-button"]').click();
      cy.url().should('include', '/admin-portal/customer-view');
      cy.get('h2').should('contain', 'Customer Journey View');

      // Mock the API response for customer details
      cy.intercept('GET', '/customers/*', {
        statusCode: 200,
        body: {
          customer_id: 'cust-123',
          mobile_number: '9876543210',
          pan_number: 'ABCDE1234F',
          segment: 'C1',
          dnd_flag: false,
          current_offers: [
            { offer_id: 'offer-1', offer_type: 'Fresh', offer_status: 'Active', propensity: 'High', start_date: '2023-01-01', end_date: '2023-12-31' }
          ],
          journey_stages: [
            { event_type: 'LOAN_LOGIN', event_timestamp: '2023-05-01T10:00:00Z', source: 'LOS' },
            { event_type: 'EKYC_ACHIEVED', event_timestamp: '2023-05-01T10:30:00Z', source: 'LOS' }
          ]
        }
      }).as('getCustomerDetails');

      // Simulate searching for a customer
      cy.get('[data-cy="customer-search-input"]').type('9876543210');
      cy.get('[data-cy="customer-search-button"]').click();

      // Wait for the API call and assert customer details are displayed
      cy.wait('@getCustomerDetails');
      cy.get('[data-cy="customer-details-card"]').should('be.visible');
      cy.get('[data-cy="customer-mobile"]').should('contain', '9876543210');
      cy.get('[data-cy="customer-segment"]').should('contain', 'C1');
      cy.get('[data-cy="customer-offers"]').should('contain', 'Active');
      cy.get('[data-cy="customer-journey-stages"]').should('contain', 'LOAN_LOGIN');
      cy.get('[data-cy="customer-journey-stages"]').should('contain', 'EKYC_ACHIEVED');
    });
  });
});