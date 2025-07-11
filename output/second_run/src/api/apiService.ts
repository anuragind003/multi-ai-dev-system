import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

// Create an Axios instance with default configuration
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // You can add other default configurations here, like timeout
  timeout: 10000, // 10 seconds
});

// Request interceptor: Add authorization header
api.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    // Check if the request requires authentication
    if (config.headers && !config.headers.Authorization && localStorage.getItem('user')) {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      if (user && user.token) {
        config.headers.Authorization = `Bearer ${user.token}`;
      }
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor: Handle errors globally
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    // Handle different types of errors
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      const { status, data } = error.response;
      switch (status) {
        case 400:
          // Bad Request - Validation errors, etc.
          console.error('Bad Request:', data);
          break;
        case 401:
          // Unauthorized - Token expired, invalid credentials
          console.warn('Unauthorized: Please login again.');
          // Optionally, redirect to login page
          // window.location.href = '/login';
          break;
        case 403:
          // Forbidden - User doesn't have permission
          console.error('Forbidden:', data);
          break;
        case 404:
          // Not Found
          console.error('Not Found:', data);
          break;
        case 500:
          // Internal Server Error
          console.error('Internal Server Error:', data);
          break;
        default:
          console.error('API Error:', data);
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Network Error: No response received.');
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default api;