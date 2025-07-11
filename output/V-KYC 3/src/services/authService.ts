import api from './api';

export interface User {
  id: string;
  username: string;
  email: string;
  roles: string[];
  // Add other user properties as needed
}

export interface LoginCredentials {
  username?: string;
  email?: string;
  password: string;
}

interface AuthResponse {
  token: string;
  user: User;
}

export const login = async (credentials: LoginCredentials): Promise<AuthResponse> => {
  const response = await api.post<AuthResponse>('/auth/login', credentials);
  return response.data;
};

export const logout = async (): Promise<void> => {
  // In a real application, you might send a request to invalidate the token on the server
  // For this example, we'll just simulate it.
  // await api.post('/auth/logout');
  console.log('Simulating backend logout...');
  return Promise.resolve();
};

export const getProfile = async (): Promise<User> => {
  const response = await api.get<User>('/auth/profile');
  return response.data;
};