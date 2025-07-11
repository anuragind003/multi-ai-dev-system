import React, { createContext, useState, useEffect, useCallback } from 'react';
import { User, AuthContextType, AppContextType } from '@/utils'; // Combined types

// Combined Context Type
interface CombinedContextType extends AuthContextType, AppContextType {}

const AuthAndAppContext = createContext<CombinedContextType | undefined>(undefined);

interface AuthAndAppProviderProps {
  children: React.ReactNode;
}

export const AuthAndAppProvider: React.FC<AuthAndAppProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [appLoading, setAppLoading] = useState<boolean>(false);
  const [appError, setAppError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // Auth related functions
  const login = useCallback((userData: User, token: string) => {
    localStorage.setItem('authToken', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
    setIsAuthenticated(true);
    setAppError(null); // Clear any previous auth errors
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
    setAppError(null);
  }, []);

  const checkAuth = useCallback(() => {
    const token = localStorage.getItem('authToken');
    const storedUser = localStorage.getItem('user');
    if (token && storedUser) {
      try {
        const userData: User = JSON.parse(storedUser);
        setUser(userData);
        setIsAuthenticated(true);
      } catch (e) {
        console.error("Failed to parse user data from localStorage", e);
        logout(); // Clear invalid data
      }
    } else {
      setIsAuthenticated(false);
    }
  }, [logout]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // App related functions
  const showLoading = useCallback(() => setAppLoading(true), []);
  const hideLoading = useCallback(() => setAppLoading(false), []);
  const showError = useCallback((message: string) => setAppError(message), []);
  const clearError = useCallback(() => setAppError(null), []);
  const showNotification = useCallback((message: string, duration = 3000) => {
    setNotification(message);
    const timer = setTimeout(() => setNotification(null), duration);
    return () => clearTimeout(timer);
  }, []);
  const clearNotification = useCallback(() => setNotification(null), []);

  const value = {
    user,
    isAuthenticated,
    login,
    logout,
    appLoading,
    showLoading,
    hideLoading,
    appError,
    showError,
    clearError,
    notification,
    showNotification,
    clearNotification,
  };

  return (
    <AuthAndAppContext.Provider value={value}>
      {children}
    </AuthAndAppContext.Provider>
  );
};