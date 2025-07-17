import axios, { AxiosError } from 'axios';
import { User, Recording, FilterParams } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for global error handling (optional, can be handled per-call)
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('API Error:', error.response.data);
      console.error('Status:', error.response.status);
      console.error('Headers:', error.response.headers);
      if (error.response.status === 401) {
        // Handle unauthorized, e.g., redirect to login
        console.warn('Unauthorized access. Redirecting to login...');
        // This should ideally be handled by AuthContext or a global error handler
        // For now, just log.
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error setting up request:', error.message);
    }
    return Promise.reject(error);
  }
);

// --- Auth Service ---
interface LoginResponse {
  token: string;
  user: {
    id: string;
    username: string;
    email: string;
  };
}

export const loginUser = async (credentials: { username: string; password: string }): Promise<LoginResponse> => {
  try {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
};

// --- Recordings Service ---
interface GetRecordingsResponse {
  data: Recording[];
  total: number;
  page: number;
  limit: number;
}

export const getRecordings = async (params: FilterParams = {}): Promise<GetRecordingsResponse> => {
  try {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.category) queryParams.append('category', params.category);
    if (params.minDuration) queryParams.append('minDuration', params.minDuration.toString());
    if (params.maxDuration) queryParams.append('maxDuration', params.maxDuration.toString());
    if (params.startDate) queryParams.append('startDate', params.startDate);
    if (params.endDate) queryParams.append('endDate', params.endDate);
    if (params.tags && params.tags.length > 0) queryParams.append('tags', params.tags.join(','));
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.limit) queryParams.append('limit', params.limit.toString());

    const response = await apiClient.get<GetRecordingsResponse>(`/recordings?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch recordings:', error);
    throw error;
  }
};

export default apiClient;