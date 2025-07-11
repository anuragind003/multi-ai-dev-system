import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  AuthContextType,
  AuthState,
  AppAlert,
  AppContextType,
  User,
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  generateUniqueId,
} from '@/types';
import { authService } from '@/services/api';
import { Alert } from '@/components/ui'; // Assuming Alert is exported from ui/index.ts

// --- Auth Context ---
const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    isLoading: true,
    error: null,
  });

  const checkAuth = useCallback(async () => {
    setAuthState((prev) => ({ ...prev, isLoading: true, error: null }));
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

    if (!accessToken || !refreshToken) {
      setAuthState({ isAuthenticated: false, user: null, isLoading: false, error: null });
      return;
    }

    try {
      const response = await authService.checkAuthStatus();
      setAuthState({
        isAuthenticated: true,
        user: response.data,
        isLoading: false,
        error: null,
      });
    } catch (err: any) {
      console.error('Auth check failed:', err);
      localStorage.clear(); // Clear invalid tokens
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false,
        error: err.response?.data?.message || 'Authentication failed',
      });
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (username: string, password: string) => {
    setAuthState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await authService.login(username, password);
      const { accessToken, refreshToken, user } = response.data;
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      setAuthState({ isAuthenticated: true, user, isLoading: false, error: null });
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'Login failed. Please check your credentials.';
      setAuthState({ isAuthenticated: false, user: null, isLoading: false, error: errorMessage });
      throw new Error(errorMessage); // Re-throw to be caught by form
    }
  };

  const logout = useCallback(async () => {
    setAuthState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      await authService.logout(); // Optional: Invalidate token on server
    } catch (err) {
      console.error('Logout failed on server:', err);
      // Still proceed with client-side logout
    } finally {
      localStorage.clear();
      setAuthState({ isAuthenticated: false, user: null, isLoading: false, error: null });
    }
  }, []);

  const authValue = {
    ...authState,
    login,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={authValue}>{children}</AuthContext.Provider>;
};

// --- App Context (for global state like alerts, general loading) ---
const AppContext = createContext<AppContextType | undefined>(undefined);

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [alerts, setAlerts] = useState<AppAlert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const alertTimeoutRefs = useRef<{ [key: string]: NodeJS.Timeout }>({});

  const addAlert = useCallback((message: string, type: AppAlert['type'], duration: number = 5000) => {
    const id = generateUniqueId();
    const newAlert: AppAlert = { id, message, type, duration };
    setAlerts((prev) => [...prev, newAlert]);

    if (duration > 0) {
      alertTimeoutRefs.current[id] = setTimeout(() => {
        removeAlert(id);
      }, duration);
    }
  }, []);

  const removeAlert = useCallback((id: string) => {
    setAlerts((prev) => prev.filter((alert) => alert.id !== id));
    if (alertTimeoutRefs.current[id]) {
      clearTimeout(alertTimeoutRefs.current[id]);
      delete alertTimeoutRefs.current[id];
    }
  }, []);

  useEffect(() => {
    return () => {
      // Clear all timeouts on unmount
      Object.values(alertTimeoutRefs.current).forEach(clearTimeout);
    };
  }, []);

  const setLoading = useCallback((loading: boolean) => {
    setIsLoading(loading);
  }, []);

  const appValue = {
    alerts,
    addAlert,
    removeAlert,
    isLoading,
    setLoading,
  };

  return (
    <AppContext.Provider value={appValue}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2">
        {alerts.map((alert) => (
          <Alert key={alert.id} message={alert.message} type={alert.type} onClose={() => removeAlert(alert.id)} />
        ))}
      </div>
    </AppContext.Provider>
  );
};

// --- Combined App Providers ---
export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <AuthProvider>
      <AppProvider>{children}</AppProvider>
    </AuthProvider>
  );
};