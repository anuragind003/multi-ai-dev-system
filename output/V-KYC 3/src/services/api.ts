import axios, { AxiosInstance, AxiosError } from 'axios';

// Define types for API responses and data
export interface User {
  id: string;
  username: string;
  email?: string;
  // Add other user properties as needed
}

interface AuthResponse {
  token: string;
  user: User;
}

interface ApiErrorResponse {
  message: string;
  details?: string;
  statusCode?: number;
}

// Create an Axios instance
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
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
  (error: AxiosError<ApiErrorResponse>) => {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('API Error:', error.response.data);
      console.error('Status:', error.response.status);
      console.error('Headers:', error.response.headers);

      const errorMessage = error.response.data?.message || 'An unexpected error occurred.';
      // Specific handling for 401 Unauthorized
      if (error.response.status === 401) {
        // Optionally, redirect to login or clear auth state
        console.warn('Unauthorized access. Redirecting to login...');
        // Example: window.location.href = '/auth'; // Or use history.push if in a component
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
      }
      return Promise.reject(new Error(errorMessage));
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Network Error:', error.request);
      return Promise.reject(new Error('No response from server. Please check your network connection.'));
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Request Setup Error:', error.message);
      return Promise.reject(new Error(`Request failed: ${error.message}`));
    }
  }
);

// --- API Functions ---

export const loginUser = async (credentials: { username: string; password: string }): Promise<AuthResponse> => {
  const response = await api.post<AuthResponse>('/auth/login', credentials);
  return response.data;
};

export const registerUser = async (credentials: { username: string; password: string }): Promise<AuthResponse> => {
  const response = await api.post<AuthResponse>('/auth/register', credentials);
  return response.data;
};

export const logoutUser = async (): Promise<void> => {
  // In a real application, this would hit a logout endpoint to invalidate the server-side token
  // For this demo, we just simulate it.
  await new Promise(resolve => setTimeout(resolve, 500)); // Simulate API call
  console.log('Simulated logout API call.');
};

export const fetchDashboardData = async (): Promise<{ message: string; data: any }> => {
  const response = await api.get<{ message: string; data: any }>('/dashboard');
  return response.data;
};

// You can add more API functions here
// export const fetchUserProfile = async (): Promise<User> => {
//   const response = await api.get<User>('/user/profile');
//   return response.data;
// };

export default api;