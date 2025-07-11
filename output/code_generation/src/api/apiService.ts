import axios, { AxiosInstance, AxiosError } from 'axios';
import { toast } from 'react-toastify';
import { ApiResponse, User, Record, ApiError } from '@types';

// Base URL for the API. Use environment variables for production.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001/api';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add authorization token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for global error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiResponse<any>>) => {
    let errorMessage = 'An unexpected error occurred.';
    let statusCode = 500;

    if (error.response) {
      statusCode = error.response.status;
      if (error.response.data && error.response.data.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }

      // Specific handling for common HTTP errors
      switch (statusCode) {
        case 401:
          errorMessage = errorMessage || 'Unauthorized. Please log in again.';
          // Optionally, redirect to login page
          // window.location.href = '/login';
          break;
        case 403:
          errorMessage = errorMessage || 'Forbidden. You do not have permission to access this resource.';
          break;
        case 404:
          errorMessage = errorMessage || 'Resource not found.';
          break;
        case 400:
          errorMessage = errorMessage || 'Bad Request. Please check your input.';
          break;
        default:
          errorMessage = errorMessage || `Server Error: ${statusCode}`;
      }
    } else if (error.request) {
      // The request was made but no response was received
      errorMessage = 'No response from server. Please check your network connection.';
    } else {
      // Something happened in setting up the request that triggered an Error
      errorMessage = error.message;
    }

    toast.error(errorMessage); // Display error message using toast

    return Promise.reject({ message: errorMessage, statusCode } as ApiError);
  }
);

// --- API Functions ---

/**
 * Authenticates a user.
 * @param username - User's username.
 * @param password - User's password.
 * @returns A promise that resolves with the API response containing token and user data.
 */
export const login = async (username: string, password: string): Promise<ApiResponse<{ token: string; user: User }>> => {
  const response = await api.post('/auth/login', { username, password });
  return response.data;
};

/**
 * Fetches a list of records.
 * @returns A promise that resolves with the API response containing an array of records.
 */
export const fetchRecords = async (): Promise<ApiResponse<Record[]>> => {
  const response = await api.get('/records');
  return response.data;
};

/**
 * Downloads a specific record file.
 * @param recordId - The ID of the record to download.
 * @returns A promise that resolves when the download is initiated.
 */
export const downloadRecord = async (recordId: string): Promise<void> => {
  try {
    const response = await api.get(`/records/${recordId}/download`, {
      responseType: 'blob', // Important for file downloads
    });

    // Extract filename from Content-Disposition header if available
    const contentDisposition = response.headers['content-disposition'];
    let filename = `record-${recordId}.bin`; // Default filename
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      }
    }

    // Create a Blob from the response data
    const blob = new Blob([response.data], { type: response.headers['content-type'] });

    // Create a link element, set its href to the Blob URL, and click it to trigger download
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url); // Clean up the URL object

    toast.success(`File "${filename}" downloaded successfully!`);
  } catch (error) {
    // Error handling is already done by the interceptor, but we can add specific logic here if needed
    console.error('Download failed:', error);
    // The interceptor will show a toast, so no need to duplicate here unless specific message is required
    throw error; // Re-throw to propagate the error to the caller
  }
};