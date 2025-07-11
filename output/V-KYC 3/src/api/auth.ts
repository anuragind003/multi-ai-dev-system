import axios, { AxiosInstance, AxiosError } from 'axios';

// Define types for API responses and requests
export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface LoginPayload {
  username?: string;
  email?: string;
  password?: string;
}

// Create an Axios instance
const axiosInstance: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 seconds
});

// Request interceptor to add authorization token
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

// Response interceptor for global error handling (e.g., 401 Unauthorized)
axiosInstance.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const { status, data } = error.response;
      console.error(`API Error - Status: ${status}, Data:`, data);

      if (status === 401) {
        // Handle unauthorized access, e.g., redirect to login
        console.warn('Unauthorized access. Redirecting to login...');
        localStorage.removeItem('authToken');
        // Optionally, dispatch a global event or use a context to trigger logout
        // window.location.href = '/login'; // Or use react-router-dom's navigate
      }
      // You can add more specific error handling here (e.g., 403, 404, 500)
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

/**
 * Authenticates a user with the provided credentials.
 * @param payload - User login credentials (username/email and password).
 * @returns A promise that resolves with AuthResponse on success.
 */
export const loginUser = async (payload: LoginPayload): Promise<AuthResponse> => {
  try {
    const response = await axiosInstance.post<AuthResponse>('/auth/login', payload);
    return response.data;
  } catch (error) {
    console.error('Login API call failed:', error);
    throw error; // Re-throw to be handled by the caller
  }
};

/**
 * Fetches the profile of the currently authenticated user.
 * @returns A promise that resolves with User data on success.
 */
export const getProfile = async (): Promise<User> => {
  try {
    const response = await axiosInstance.get<User>('/user/profile');
    return response.data;
  } catch (error) {
    console.error('Get profile API call failed:', error);
    throw error;
  }
};

export default axiosInstance; // Export the instance for other API calls if needed