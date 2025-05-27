import axios from 'axios';

// Base URL for the backend API
// Using import.meta.env for Vite projects, with a fallback for local development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

/**
 * Converts a File object to a Base64 encoded string.
 * This is used for sending file content as part of a JSON payload.
 * @param {File} file - The File object to convert.
 * @returns {Promise<string>} A promise that resolves with the Base64 string (without the data URI prefix).
 */
const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      // The result will be a data URI (e.g., "data:text/csv;base64,...")
      // We only need the base64 part after the comma.
      resolve(reader.result.split(',')[1]);
    };
    reader.onerror = error => reject(error);
  });
};

/**
 * Retrieves a single customer's profile view with associated offers and journey stages.
 * Corresponds to GET /customers/{customer_id}
 * @param {string} customerId - The ID of the customer to retrieve.
 * @returns {Promise<Object>} A promise that resolves with the customer profile data.
 */
export const getCustomerProfile = async (customerId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/customers/${customerId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching customer profile for ID ${customerId}:`, error);
    throw error; // Re-throw to allow calling component to handle
  }
};

/**
 * Uploads customer details file (Prospect, TW Loyalty, Topup, Employee loans) via Admin Portal.
 * The file content is sent as a base64 encoded string in a JSON payload, as per system design.
 * Corresponds to POST /admin/customer-data/upload
 * @param {File} file - The file object to upload.
 * @param {string} fileName - The name of the file.
 * @param {string} loanType - The type of loan associated with the upload (e.g., 'Prospect', 'TW Loyalty').
 * @returns {Promise<Object>} A promise that resolves with the upload status (e.g., { status, log_id, success_count, error_count }).
 */
export const uploadCustomerData = async (file, fileName, loanType) => {
  try {
    const fileContentBase64 = await fileToBase64(file);

    const payload = {
      file_content: fileContentBase64,
      file_name: fileName,
      loan_type: loanType,
    };

    const response = await axios.post(`${API_BASE_URL}/admin/customer-data/upload`, payload, {
      headers: {
        'Content-Type': 'application/json', // Sending JSON payload
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading customer data:', error);
    throw error;
  }
};

/**
 * Downloads a file containing identified duplicate customer records.
 * Corresponds to GET /data/duplicates
 * @returns {Promise<Blob>} A promise that resolves with the file content as a Blob.
 */
export const downloadDuplicateData = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/data/duplicates`, {
      responseType: 'blob', // Important for file downloads
    });
    return response.data; // This will be a Blob
  } catch (error) {
    console.error('Error downloading duplicate data:', error);
    throw error;
  }
};

/**
 * Downloads a file containing unique customer records after deduplication.
 * Corresponds to GET /data/unique
 * @returns {Promise<Blob>} A promise that resolves with the file content as a Blob.
 */
export const downloadUniqueData = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/data/unique`, {
      responseType: 'blob', // Important for file downloads
    });
    return response.data; // This will be a Blob
  } catch (error) {
    console.error('Error downloading unique data:', error);
    throw error;
  }
};

/**
 * Downloads an Excel file detailing errors from data ingestion processes.
 * Corresponds to GET /data/errors
 * @returns {Promise<Blob>} A promise that resolves with the file content as a Blob.
 */
export const downloadErrorData = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/data/errors`, {
      responseType: 'blob', // Important for file downloads
    });
    return response.data; // This will be a Blob
  } catch (error) {
    console.error('Error downloading error data:', error);
    throw error;
  }
};

/**
 * Helper function to trigger file download in the browser.
 * This function creates a temporary anchor tag, sets its href to a Blob URL,
 * simulates a click, and then cleans up.
 * @param {Blob} blob - The Blob object containing the file data.
 * @param {string} filename - The desired filename for the downloaded file.
 */
export const triggerFileDownload = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url); // Clean up the URL object
  document.body.removeChild(a); // Remove the temporary anchor tag
};