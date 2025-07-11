import React, { createContext, useState, useContext, useCallback, useEffect } from 'react';
import { api } from '@/services/api';

// --- Auth Context ---
interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  createdAt: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  authError: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthContextProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Initial loading for auth check

  useEffect(() => {
    // Simulate checking for a token in localStorage on app load
    const storedToken = localStorage.getItem('authToken');
    const storedUser = localStorage.getItem('authUser');
    if (storedToken && storedUser) {
      try {
        const parsedUser: User = JSON.parse(storedUser);
        setUser(parsedUser);
        setIsAuthenticated(true);
      } catch (e) {
        console.error("Failed to parse stored user data:", e);
        localStorage.removeItem('authToken');
        localStorage.removeItem('authUser');
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const response = await api.login(username, password);
      const { token, user: userData } = response.data;
      localStorage.setItem('authToken', token);
      localStorage.setItem('authUser', JSON.stringify(userData));
      setUser(userData);
      setIsAuthenticated(true);
      setAuthError(null);
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'Login failed. Please check your credentials.';
      setAuthError(errorMessage);
      setUser(null);
      setIsAuthenticated(false);
      localStorage.removeItem('authToken');
      localStorage.removeItem('authUser');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    setUser(null);
    setIsAuthenticated(false);
    setAuthError(null);
  }, []);

  const contextValue = React.useMemo(() => ({
    user,
    isAuthenticated,
    authError,
    isLoading,
    login,
    logout,
  }), [user, isAuthenticated, authError, isLoading, login, logout]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthContextProvider');
  }
  return context;
};

// --- Recordings Context ---
interface Recording {
  id: string;
  title: string;
  description: string;
  duration: number; // in seconds
  date: string; // ISO string
  tags: string[];
}

interface RecordingsContextType {
  recordings: Recording[];
  isLoading: boolean;
  error: string | null;
  fetchRecordings: () => Promise<void>;
  addRecording: (newRecording: Omit<Recording, 'id'>) => Promise<void>;
  updateRecording: (id: string, updatedRecording: Partial<Omit<Recording, 'id'>>) => Promise<void>;
  deleteRecording: (id: string) => Promise<void>;
}

const RecordingsContext = createContext<RecordingsContextType | undefined>(undefined);

export const RecordingsContextProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecordings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getRecordings();
      setRecordings(response.data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to fetch recordings.');
      console.error('Error fetching recordings:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const addRecording = useCallback(async (newRecording: Omit<Recording, 'id'>) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.createRecording(newRecording);
      setRecordings(prev => [...prev, response.data]);
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to add recording.');
      console.error('Error adding recording:', err);
      throw err; // Re-throw to allow form to catch
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateRecording = useCallback(async (id: string, updatedRecording: Partial<Omit<Recording, 'id'>>) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.updateRecording(id, updatedRecording);
      setRecordings(prev => prev.map(rec => (rec.id === id ? response.data : rec)));
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to update recording.');
      console.error('Error updating recording:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteRecording = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.deleteRecording(id);
      setRecordings(prev => prev.filter(rec => rec.id !== id));
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to delete recording.');
      console.error('Error deleting recording:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const contextValue = React.useMemo(() => ({
    recordings,
    isLoading,
    error,
    fetchRecordings,
    addRecording,
    updateRecording,
    deleteRecording,
  }), [recordings, isLoading, error, fetchRecordings, addRecording, updateRecording, deleteRecording]);

  return (
    <RecordingsContext.Provider value={contextValue}>
      {children}
    </RecordingsContext.Provider>
  );
};

export const useRecordings = () => {
  const context = useContext(RecordingsContext);
  if (context === undefined) {
    throw new Error('useRecordings must be used within a RecordingsContextProvider');
  }
  return context;
};