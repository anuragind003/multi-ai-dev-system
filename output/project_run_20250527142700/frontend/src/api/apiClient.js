import axios from 'axios';

// Base URL for the backend API
// In a production environment, this should be configured via environment variables
// (e.g., process.env.VUE_APP_API_BASE_URL) or a separate configuration file.
const API_BASE_URL = 'http://localhost:5000'; // Assuming Flask backend runs on port 5000

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    // Add any authorization headers here if needed, e.g., 'Authorization': `Bearer ${localStorage.getItem('token')}`
  },
});

/**
 * Fetches a single customer's de-duplicated profile and associated active offers.
 * @param {string} customerId - The UUID of the customer.
 * @returns {Promise<Object>} - A promise that resolves to the customer data.
 */
export const getCustomerProfile = async (customerId) => {
  try {
    const response = await apiClient.get(`/customers/${customerId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching customer profile for ${customerId}:`, error);
    throw error; // Re-throw to allow calling component to handle
  }
};

/**
 * Downloads the Moengage-formatted CSV file for eligible customers.
 * @returns {Promise<Blob>} - A promise that resolves to a Blob containing the CSV data.
 */
export const downloadMoengageCampaignFile = async () => {
  try {
    const response = await apiClient.get('/exports/moengage-campaign-file', {
      responseType: 'blob', // Important for file downloads
    });
    return response.data;
  } catch (error) {
    console.error('Error downloading Moengage campaign file:', error);
    throw error;
  }
};

/**
 * Downloads a file containing identified duplicate customer data.
 * @returns {Promise<Blob>} - A promise that resolves to a Blob containing the CSV data.
 */
export const downloadDuplicateCustomersFile = async () => {
  try {
    const response = await apiClient.get('/exports/duplicate-customers', {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    console.error('Error downloading duplicate customers file:', error);
    throw error;
  }
};

/**
 * Downloads a file containing unique customer data after deduplication.
 * @returns {Promise<Blob>} - A promise that resolves to a Blob containing the CSV data.
 */
export const downloadUniqueCustomersFile = async () => {
  try {
    const response = await apiClient.get('/exports/unique-customers', {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    console.error('Error downloading unique customers file:', error);
    throw error;
  }
};

/**
 * Downloads an Excel file detailing data validation errors from ingestion processes.
 * @returns {Promise<Blob>} - A promise that resolves to a Blob containing the Excel data.
 */
export const downloadDataErrorsFile = async () => {
  try {
    const response = await apiClient.get('/exports/data-errors', {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    console.error('Error downloading data errors file:', error);
    throw error;
  }
};

// You can add more API calls here as needed, e.g., for POST requests
// if the frontend ever needs to trigger ingestion or event logging directly.
// Based on the current BRD and system design, the frontend primarily
// focuses on GET requests for data viewing and file downloads.

export default apiClient;