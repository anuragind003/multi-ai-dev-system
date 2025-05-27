import axios from 'axios';

// Base URL for the backend API
// In a production environment, this should be configured via environment variables
// For development, it defaults to localhost:5000 as per Flask's common default port.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Axios Interceptors for global error handling and request logging
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('API Error Response:', error.response.data);
      console.error('Status:', error.response.status);
      // You might want to throw a more specific error or handle it based on status
      return Promise.reject(error.response.data);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('API Error Request:', error.request);
      return Promise.reject({ message: 'No response from server. Please check your network connection.' });
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('API Error Message:', error.message);
      return Promise.reject({ message: 'An unexpected error occurred.' });
    }
  }
);

/**
 * Sends real-time lead generation data to the backend.
 * Corresponds to API endpoint: POST /api/leads
 * @param {object} data - Lead data (e.g., mobile_number, pan_number, aadhaar_number, loan_type, source_channel)
 * @returns {Promise<object>} - Response data including status and customer_id
 */
export const postLeadData = (data) => {
  return apiClient.post('/api/leads', data);
};

/**
 * Sends real-time eligibility data to the backend.
 * Corresponds to API endpoint: POST /api/eligibility
 * @param {object} data - Eligibility data (e.g., customer_id, offer_id, eligibility_status, loan_amount)
 * @returns {Promise<object>} - Response data including status and message
 */
export const postEligibilityData = (data) => {
  return apiClient.post('/api/eligibility', data);
};

/**
 * Sends real-time application status updates to the backend.
 * Corresponds to API endpoint: POST /api/status-updates
 * @param {object} data - Status update data (e.g., loan_application_number, customer_id, current_stage, status_timestamp)
 * @returns {Promise<object>} - Response data including status and message
 */
export const postStatusUpdate = (data) => {
  return apiClient.post('/api/status-updates', data);
};

/**
 * Uploads a customer details file (e.g., CSV) to the backend.
 * Corresponds to API endpoint: POST /admin/customer-data/upload
 * @param {File} file - The file object to upload.
 * @param {string} loanType - The type of loan (e.g., 'Prospect', 'TW Loyalty', 'Topup', 'Employee loans').
 * @returns {Promise<object>} - Response data including status, log_id, success_count, error_count
 */
export const uploadCustomerData = (file, loanType) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('loan_type', loanType);

  // Axios automatically sets Content-Type to multipart/form-data when FormData is used
  return apiClient.post('/admin/customer-data/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

/**
 * Retrieves a single customer's profile view with associated offers and journey stages.
 * Corresponds to API endpoint: GET /customers/{customer_id}
 * @param {string} customerId - The ID of the customer to retrieve.
 * @returns {Promise<object>} - Customer profile data
 */
export const getCustomerProfile = (customerId) => {
  return apiClient.get(`/customers/${customerId}`);
};

/**
 * Generates and allows download of the Moengage format CSV file for campaigns.
 * Corresponds to API endpoint: GET /campaigns/moengage-export
 * @returns {Promise<Blob>} - The CSV file content as a Blob.
 */
export const downloadMoengageExport = () => {
  return apiClient.get('/campaigns/moengage-export', { responseType: 'blob' });
};

/**
 * Allows download of a file containing identified duplicate customer records.
 * Corresponds to API endpoint: GET /data/duplicates
 * @returns {Promise<Blob>} - The CSV file content as a Blob.
 */
export const downloadDuplicateData = () => {
  return apiClient.get('/data/duplicates', { responseType: 'blob' });
};

/**
 * Allows download of a file containing unique customer records after deduplication.
 * Corresponds to API endpoint: GET /data/unique
 * @returns {Promise<Blob>} - The CSV file content as a Blob.
 */
export const downloadUniqueData = () => {
  return apiClient.get('/data/unique', { responseType: 'blob' });
};

/**
 * Allows download of an Excel file detailing errors from data ingestion processes.
 * Corresponds to API endpoint: GET /data/errors
 * @returns {Promise<Blob>} - The Excel file content as a Blob.
 */
export const downloadErrorFile = () => {
  return apiClient.get('/data/errors', { responseType: 'blob' });
};