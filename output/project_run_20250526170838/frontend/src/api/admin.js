import axios from 'axios';

// Define the base URL for the API.
// It tries to use an environment variable (common in Vue/Vite projects)
// and falls back to a default localhost URL if not set.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

/**
 * Uploads a customer data file to the backend.
 * This function is used by the Admin Portal (FR35) to generate leads (FR36).
 *
 * @param {File} file - The file object to upload (e.g., a CSV file).
 * @param {string} loanType - The type of loan associated with the uploaded data
 *                            (e.g., 'Prospect', 'TW Loyalty', 'Topup', 'Employee loans').
 * @returns {Promise<Object>} A promise that resolves with the API response data,
 *                            typically containing log_id, success_count, and error_count (FR37, FR38).
 * @throws {Error} If the API call fails.
 */
export async function uploadCustomerData(file, loanType) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('loan_type', loanType);

  try {
    const response = await axios.post(`${API_BASE_URL}/admin/customer-data/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading customer data:', error.response?.data || error.message);
    throw error; // Re-throw to allow the calling component to handle the error
  }
}

/**
 * Downloads the Moengage format CSV file from the backend (FR31, FR44).
 *
 * @returns {Promise<void>} A promise that resolves when the file download is initiated.
 * @throws {Error} If the API call fails.
 */
export async function downloadMoengageFile() {
  try {
    const response = await axios.get(`${API_BASE_URL}/campaigns/moengage-export`, {
      responseType: 'blob', // Important: tells axios to expect a binary blob response
    });

    // Create a Blob from the response data with the correct MIME type for CSV
    const blob = new Blob([response.data], { type: 'text/csv' });

    // Create a temporary URL for the Blob
    const url = window.URL.createObjectURL(blob);

    // Create a temporary anchor element to trigger the download
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'moengage_campaign_data.csv'); // Set the desired filename
    document.body.appendChild(link); // Append to body to make it clickable in all browsers
    link.click(); // Programmatically click the link to trigger download

    // Clean up: remove the link and revoke the object URL
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error downloading Moengage file:', error.response?.data || error.message);
    throw error;
  }
}

/**
 * Downloads a file containing identified duplicate customer records (FR32).
 *
 * @returns {Promise<void>} A promise that resolves when the file download is initiated.
 * @throws {Error} If the API call fails.
 */
export async function downloadDuplicateData() {
  try {
    const response = await axios.get(`${API_BASE_URL}/data/duplicates`, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'duplicate_customer_data.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error downloading duplicate data:', error.response?.data || error.message);
    throw error;
  }
}

/**
 * Downloads a file containing unique customer records after deduplication (FR33).
 *
 * @returns {Promise<void>} A promise that resolves when the file download is initiated.
 * @throws {Error} If the API call fails.
 */
export async function downloadUniqueData() {
  try {
    const response = await axios.get(`${API_BASE_URL}/data/unique`, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'unique_customer_data.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error downloading unique data:', error.response?.data || error.message);
    throw error;
  }
}

/**
 * Downloads an Excel file detailing errors from data ingestion processes (FR34, FR38).
 *
 * @returns {Promise<void>} A promise that resolves when the file download is initiated.
 * @throws {Error} If the API call fails.
 */
export async function downloadErrorFile() {
  try {
    const response = await axios.get(`${API_BASE_URL}/data/errors`, {
      responseType: 'blob',
    });

    // The system design specifies an Excel file, so use the appropriate MIME type
    const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'data_ingestion_errors.xlsx'); // Suggested filename for Excel
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error downloading error file:', error.response?.data || error.message);
    throw error;
  }
}