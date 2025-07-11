import axios, { AxiosInstance, AxiosError } from 'axios';
import { AuthCredentials, User } from '@/context/AuthContext'; // Import types from AuthContext

// Create an Axios instance
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for sending cookies (e.g., session IDs)
});

// Request interceptor to add authorization token (if using Bearer tokens)
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken'); // Example: get token from localStorage
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
  (error: AxiosError) => {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('API Error Response:', error.response.data);
      console.error('Status:', error.response.status);
      console.error('Headers:', error.response.headers);

      if (error.response.status === 401) {
        // Unauthorized: token expired or invalid, redirect to login
        console.warn('Unauthorized access. Redirecting to login...');
        // In a real app, you might want to dispatch a logout action here
        // window.location.href = '/login'; // Or use history.push if not in a React component
      }
      // Re-throw the error with a more user-friendly message
      const errorMessage = (error.response.data as any)?.message || 'An unexpected error occurred.';
      return Promise.reject(new Error(errorMessage));
    } else if (error.request) {
      // The request was made but no response was received
      console.error('API Error Request:', error.request);
      return Promise.reject(new Error('No response from server. Please check your internet connection.'));
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('API Error Message:', error.message);
      return Promise.reject(new Error(`Request setup error: ${error.message}`));
    }
  }
);

// --- API Service Functions ---

/**
 * Simulates user login.
 * @param credentials - User's authentication credentials.
 * @returns A promise that resolves with user data on success.
 */
export const login = async (credentials: AuthCredentials): Promise<User> => {
  try {
    // In a real app: const response = await api.post('/auth/login', credentials);
    // Simulate API call delay and response
    await new Promise(resolve => setTimeout(resolve, 1000));
    if (credentials.email === 'user@example.com' && credentials.password === 'password123') {
      const user: User = {
        id: '1',
        username: 'testuser',
        email: 'user@example.com',
        firstName: 'Test',
        lastName: 'User',
        role: 'user',
      };
      localStorage.setItem('authToken', 'fake-jwt-token'); // Simulate token storage
      return user;
    } else if (credentials.email === 'admin@example.com' && credentials.password === 'admin123') {
      const user: User = {
        id: '2',
        username: 'adminuser',
        email: 'admin@example.com',
        firstName: 'Admin',
        lastName: 'User',
        role: 'admin',
      };
      localStorage.setItem('authToken', 'fake-admin-token');
      return user;
    } else {
      throw new Error('Invalid credentials');
    }
  } catch (error) {
    console.error('Login API error:', error);
    throw error; // Re-throw for AuthContext to handle
  }
};

/**
 * Simulates user logout.
 */
export const logout = async (): Promise<void> => {
  try {
    // In a real app: await api.post('/auth/logout');
    await new Promise(resolve => setTimeout(resolve, 500));
    localStorage.removeItem('authToken'); // Clear token
  } catch (error) {
    console.error('Logout API error:', error);
    throw error;
  }
};

/**
 * Checks the current authentication status.
 * @returns A promise that resolves with user data if authenticated, otherwise null.
 */
export const checkAuthStatus = async (): Promise<User | null> => {
  try {
    // In a real app: const response = await api.get('/auth/status');
    await new Promise(resolve => setTimeout(resolve, 500));
    const token = localStorage.getItem('authToken');
    if (token === 'fake-jwt-token') {
      return { id: '1', username: 'testuser', email: 'user@example.com', firstName: 'Test', lastName: 'User', role: 'user' };
    } else if (token === 'fake-admin-token') {
      return { id: '2', username: 'adminuser', email: 'admin@example.com', firstName: 'Admin', lastName: 'User', role: 'admin' };
    }
    return null;
  } catch (error) {
    console.error('Check auth status API error:', error);
    return null; // Return null on error, indicating not authenticated
  }
};

/**
 * Simulates updating user profile.
 * @param userData - The user data to update.
 * @returns A promise that resolves with the updated user data.
 */
export const updateUserProfile = async (userData: User): Promise<User> => {
  try {
    // In a real app: const response = await api.put(`/users/${userData.id}`, userData);
    await new Promise(resolve => setTimeout(resolve, 700));
    console.log('Simulated profile update for:', userData);
    return userData; // Return the updated data
  } catch (error) {
    console.error('Update profile API error:', error);
    throw error;
  }
};

// You can add more API functions here (e.g., for dashboard data, settings, etc.)
// export const getDashboardData = async (): Promise<any> => {
//   const response = await api.get('/dashboard');
//   return response.data;
// };