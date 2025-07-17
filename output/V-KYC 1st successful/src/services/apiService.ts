import axios from 'axios';
import { LoginCredentials, AuthResponse, UploadResponse, BulkUploadRequest } from '../utils/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001/api';

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
axiosInstance.interceptors.request.use(
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

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    let errorMessage = 'An unexpected error occurred.';
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      errorMessage = error.response.data.message || error.response.statusText || errorMessage;
      if (error.response.status === 401) {
        // Unauthorized, e.g., token expired
        localStorage.removeItem('authToken');
        // Optionally redirect to login page
        window.location.href = '/login';
      }
    } else if (error.request) {
      // The request was made but no response was received
      errorMessage = 'No response from server. Please check your network connection.';
    } else {
      // Something happened in setting up the request that triggered an Error
      errorMessage = error.message;
    }
    return Promise.reject(new Error(errorMessage));
  }
);

export const apiService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    // Simulate API call
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (credentials.username === 'demo' && credentials.password === 'password123') {
          resolve({ token: 'mock-auth-token-123', userId: 'user-123' });
        } else if (credentials.username === 'admin' && credentials.password === 'adminpass') {
          resolve({ token: 'mock-admin-token-456', userId: 'admin-456' });
        } else {
          reject(new Error('Invalid credentials'));
        }
      }, 500);
    });
    // return axiosInstance.post<AuthResponse>('/auth/login', credentials);
  },

  uploadFile: async (formData: FormData): Promise<UploadResponse> => {
    // Simulate API call
    console.log('Simulating file upload:', formData.get('file'));
    return new Promise((resolve) => {
      setTimeout(() => {
        const requestId = `req-${Date.now()}`;
        resolve({ requestId, message: 'File upload initiated successfully.' });
      }, 1500);
    });
    // return axiosInstance.post<UploadResponse>('/uploads', formData, {
    //   headers: {
    //     'Content-Type': 'multipart/form-data',
    //   },
    // });
  },

  getUploadResults: async (requestId: string): Promise<BulkUploadRequest> => {
    // Simulate API call
    console.log(`Simulating fetching results for request ID: ${requestId}`);
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const mockResults = [
          { rowId: 1, status: 'SUCCESS', message: 'Record created.', data: { name: 'Item A', value: 100 } },
          { rowId: 2, status: 'FAILED', message: 'Invalid format for field X.', data: { name: 'Item B', value: 'abc' } },
          { rowId: 3, status: 'SUCCESS', message: 'Record updated.', data: { name: 'Item C', value: 200 } },
          { rowId: 4, status: 'FAILED', message: 'Duplicate entry.', data: { name: 'Item D', value: 300 } },
          { rowId: 5, status: 'SUCCESS', message: 'Record created.', data: { name: 'Item E', value: 400 } },
        ];

        const statuses = ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'];
        const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];

        if (Math.random() < 0.1) { // 10% chance of failure
          reject(new Error('Failed to retrieve results due to server error.'));
        } else {
          resolve({
            id: requestId,
            filename: `upload_${requestId}.csv`,
            status: randomStatus, // Simulate status changing over time
            uploadedAt: new Date().toISOString(),
            totalRows: mockResults.length,
            processedRows: mockResults.length,
            successCount: mockResults.filter(r => r.status === 'SUCCESS').length,
            failureCount: mockResults.filter(r => r.status === 'FAILED').length,
            results: randomStatus === 'COMPLETED' || randomStatus === 'FAILED' ? mockResults : [],
          });
        }
      }, 1000);
    });
    // return axiosInstance.get<BulkUploadRequest>(`/uploads/${requestId}/results`);
  },
};