import axios from 'axios';

// Base URL for your Flask backend API.
// In a production environment, this should be configured via environment variables.
// For development, it defaults to localhost:5000 where the Flask backend is expected to run.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Downloads the Moengage-formatted campaign file (CSV).
 * Corresponds to FR30.
 * @returns {Promise<Blob>} A promise that resolves with the file Blob.
 * @throws {Error} If the API call fails.
 */
export const downloadMoengageCampaignFile = async () => {
  try {
    const response = await apiClient.get('/exports/moengage-campaign-file', {
      responseType: 'blob', // Important for handling binary file data
    });
    return response.data;
  } catch (error) {
    console.error('Error downloading Moengage campaign file:', error);
    throw error; // Re-throw to allow the calling component to handle the error
  }
};

/**
 * Downloads the duplicate customer data file (CSV/Excel).
 * Corresponds to FR31.
 * @returns {Promise<Blob>} A promise that resolves with the file Blob.
 * @throws {Error} If the API call fails.
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
 * Downloads the unique customer data file (CSV/Excel).
 * Corresponds to FR32.
 * @returns {Promise<Blob>} A promise that resolves with the file Blob.
 * @throws {Error} If the API call fails.
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
 * Downloads the data validation errors file (Excel).
 * Corresponds to FR33.
 * @returns {Promise<Blob>} A promise that resolves with the file Blob.
 * @throws {Error} If the API call fails.
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

/**
 * Helper function to trigger a file download in the browser.
 * @param {Blob} blob The Blob object representing the file content.
 * @param {string} filename The desired filename for the downloaded file.
 */
export const triggerFileDownload = (blob, filename) => {
  // Create a URL for the blob
  const url = window.URL.createObjectURL(blob);
  // Create a temporary anchor element
  const a = document.createElement('a');
  a.style.display = 'none'; // Hide the anchor element
  a.href = url;
  a.download = filename; // Set the download filename
  document.body.appendChild(a); // Append to body to make it clickable
  a.click(); // Programmatically click the anchor to trigger download
  window.URL.revokeObjectURL(url); // Clean up the URL object
  document.body.removeChild(a); // Remove the temporary anchor
};