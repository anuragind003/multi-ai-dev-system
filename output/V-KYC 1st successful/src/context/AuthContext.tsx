import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { login as apiLogin, logout as apiLogout, checkAuthStatus } from '../services/api';
import { User, AuthCredentials } from '../types'; // Assuming types are defined here

// Define types for the context state and actions
interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (credentials: AuthCredentials) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

// Create the context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// AuthProvider component
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Initial loading for auth check
  const [error, setError] = useState<string | null>(null);

  // Function to clear error messages
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Initial authentication check on component mount
  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      try {
        const userData = await checkAuthStatus(); // API call to verify token/session
        if (userData) {
          setIsAuthenticated(true);
          setUser(userData);
        } else {
          setIsAuthenticated(false);
          setUser(null);
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        setIsAuthenticated(false);
        setUser(null);
        // Do not set error here, as it's a silent check
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, []);

  // Login function
  const login = useCallback(async (credentials: AuthCredentials) => {
    setIsLoading(true);
    setError(null);
    try {
      const userData = await apiLogin(credentials);
      setIsAuthenticated(true);
      setUser(userData);
      // Store token/session info if necessary (e.g., localStorage, http-only cookie)
    } catch (err: any) {
      console.error('Login failed:', err);
      setIsAuthenticated(false);
      setUser(null);
      setError(err.message || 'Login failed. Please check your credentials.');
      throw err; // Re-throw to allow component to handle specific errors
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Logout function
  const logout = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await apiLogout();
      setIsAuthenticated(false);
      setUser(null);
      // Clear any stored token/session info
    } catch (err: any) {
      console.error('Logout failed:', err);
      setError(err.message || 'Logout failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const value = {
    isAuthenticated,
    user,
    isLoading,
    error,
    login,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use the AuthContext
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Define User and AuthCredentials types here or in a separate types file
// For simplicity, defining them here. In a larger app, move to src/types/index.ts
export interface User {
  id: string;
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  role: 'admin' | 'user';
}

export interface AuthCredentials {
  username?: string;
  email?: string;
  password: string;
}