import React, { createContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User, AuthContextType } from '@/types';
import { loginUser, logoutUser, getUserProfile } from '@services/api'; // Assuming these are in api.ts

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface GlobalProviderProps {
  children: ReactNode;
}

export const GlobalProvider: React.FC<GlobalProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadUser = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('authToken');
      if (token) {
        // In a real app, you'd validate the token with the backend
        // and fetch user details. For this example, we simulate it.
        const profile = await getUserProfile(); // Simulate API call
        setUser(profile);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
    } catch (err) {
      console.error('Failed to load user:', err);
      setError('Failed to load user session.');
      setUser(null);
      setIsAuthenticated(false);
      localStorage.removeItem('authToken'); // Clear invalid token
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (credentials: { username: string; password: string }) => {
    setIsLoading(true);
    setError(null);
    try {
      const { token, user: userData } = await loginUser(credentials.username, credentials.password);
      localStorage.setItem('authToken', token);
      setUser(userData);
      setIsAuthenticated(true);
      return true;
    } catch (err: any) {
      console.error('Login failed:', err);
      setError(err.message || 'Login failed. Please check your credentials.');
      setIsAuthenticated(false);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await logoutUser(); // Simulate API call to invalidate token
      localStorage.removeItem('authToken');
      setUser(null);
      setIsAuthenticated(false);
    } catch (err: any) {
      console.error('Logout failed:', err);
      setError(err.message || 'Logout failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const value = {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    setError, // Allow components to clear/set errors
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;