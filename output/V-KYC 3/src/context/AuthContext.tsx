import React, { createContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { User, AuthResponseData, authService, ApiResponse } from '@api/index';

// Define types for AuthContext
interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  loading: boolean;
  error: string | null;
}

// Create the AuthContext
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// AuthProvider component
interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Function to handle user login
  const login = useCallback((newToken: string, newUser: User) => {
    localStorage.setItem('authToken', newToken);
    localStorage.setItem('authUser', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
    setIsAuthenticated(true);
    setError(null);
  }, []);

  // Function to handle user logout
  const logout = useCallback(() => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    setError(null);
  }, []);

  // Effect to check for existing token on app load
  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    const storedUser = localStorage.getItem('authUser');

    if (storedToken && storedUser) {
      try {
        const parsedUser: User = JSON.parse(storedUser);
        // Validate token with backend if necessary, or just set state
        // For this example, we'll simulate validation by fetching profile
        const validateToken = async () => {
          setLoading(true);
          const response: ApiResponse<User> = await authService.getProfile(storedToken);
          if (response.success && response.data) {
            login(storedToken, response.data); // Re-login with validated data
          } else {
            console.error("Token validation failed:", response.message);
            logout(); // Clear invalid token
            setError(response.message || "Session expired or invalid.");
          }
          setLoading(false);
        };
        validateToken();
      } catch (e) {
        console.error("Failed to parse stored user or validate token:", e);
        logout();
        setLoading(false);
        setError("Failed to restore session.");
      }
    } else {
      setLoading(false);
    }
  }, [login, logout]); // Depend on login/logout to avoid stale closures

  const contextValue = {
    isAuthenticated,
    user,
    token,
    login,
    logout,
    loading,
    error,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};