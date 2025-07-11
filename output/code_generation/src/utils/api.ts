import axios, { AxiosInstance, AxiosError } from 'axios';
import { getAuthToken, removeAuthToken } from '@utils/auth';
import { ApiResponse } from '@types/index';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for sending cookies with requests
});

// Request interceptor to add authorization token
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for global error handling and token expiration
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiResponse<any>>) => {
    if (error.response) {
      const { status, data } = error.response;
      // Handle specific status codes
      if (status === 401) {
        // Unauthorized - token expired or invalid
        console.error('Unauthorized: Token expired or invalid. Logging out...');
        removeAuthToken(); // Clear invalid token
        // Optionally redirect to login page
        window.location.href = '/login';
      } else if (status === 403) {
        // Forbidden - user does not have necessary permissions
        console.error('Forbidden: You do not have permission to access this resource.');
      } else if (status >= 500) {
        // Server errors
        console.error('Server Error:', data?.message || 'An unexpected server error occurred.');
      }
      // Return a more structured error object
      return Promise.reject({
        message: data?.message || error.message,
        statusCode: status,
        originalError: error,
      });
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received:', error.request);
      return Promise.reject({
        message: 'No response from server. Please check your network connection.',
        originalError: error,
      });
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error setting up request:', error.message);
      return Promise.reject({
        message: error.message,
        originalError: error,
      });
    }
  }
);

export default api;