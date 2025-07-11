import { apiService } from './apiService';
import { User } from '../types';

const AUTH_API_URL = '/auth'; // Example endpoint

export const login = async (credentials: { email: string; password: string }): Promise<User> => {
  try {
    const response = await apiService(`${AUTH_API_URL}/login`, {
      method: 'POST',
      body: credentials,
    });
    return response as User;
  } catch (error: any) {
    throw new Error(error.message || 'Login failed');
  }
};

export const register = async (credentials: { email: string; password: string }) => {
  try {
    await apiService(`${AUTH_API_URL}/register`, {
      method: 'POST',
      body: credentials,
    });
  } catch (error: any) {
    throw new Error(error.message || 'Registration failed');
  }
};

export const logout = () => {
  // In a real application, you'd likely make an API call to invalidate the token
  // For this example, we just clear the local storage.
  localStorage.removeItem('user');
};