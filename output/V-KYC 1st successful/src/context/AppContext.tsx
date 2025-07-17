import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { AuthContextType, UploadContextType, User, UploadStatus, UploadResultItem, AuthStatus } from '../types';
import { loginUser, uploadFile, getUploadResults } from '../services/api';
import { handleApiError } from '../utils/helpers';

interface AppContextCombined extends AuthContextType, UploadContextType {}

const AppContext = createContext<AppContextCombined | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Auth State
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authStatus, setAuthStatus] = useState<AuthStatus>('idle');

  // Upload State
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadResults, setUploadResults] = useState<UploadResultItem[]>([]);
  const [currentUploadError, setCurrentUploadError] = useState<string | null>(null);
  const [isFetchingResults, setIsFetchingResults] = useState<boolean>(false);
  const [fetchResultsError, setFetchResultsError] = useState<string | null>(null);

  // --- Auth Actions ---
  const login = async (username: string, password: string) => {
    setAuthStatus('loading');
    try {
      const response = await loginUser(username, password);
      const { token, user: userData } = response.data;
      localStorage.setItem('authToken', token);
      setUser(userData);
      setIsAuthenticated(true);
      setAuthStatus('authenticated');
    } catch (error) {
      const errorMessage = handleApiError(error);
      setCurrentUploadError(errorMessage); // Reusing for login errors
      setAuthStatus('unauthenticated');
      throw new Error(errorMessage); // Re-throw to be caught by login form
    } finally {
      setCurrentUploadError(null); // Clear after attempt
    }
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setUser(null);
    setIsAuthenticated(false);
    setAuthStatus('unauthenticated');
    clearUploadState(); // Clear upload state on logout
  };

  // Initial auth check
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (token) {
      // In a real app, you'd validate this token with the backend
      // For this example, we'll assume a token means authenticated
      // and fetch user details if necessary.
      // For simplicity, we'll just set authenticated if token exists.
      setIsAuthenticated(true);
      setAuthStatus('authenticated');
      // Optionally, fetch user profile here if token is valid
      // setUser({ id: '1', username: 'demo', email: 'demo@example.com', role: 'user' });
    } else {
      setAuthStatus('unauthenticated');
    }
  }, []);

  // --- Upload Actions ---
  const initiateUpload = async (file: File) => {
    setUploadStatus('uploading');
    setUploadProgress(0);
    setCurrentUploadError(null);
    try {
      // Simulate progress
      let progress = 0;
      const interval = setInterval(() => {
        progress += 10;
        if (progress <= 90) setUploadProgress(progress);
        else clearInterval(interval);
      }, 200);

      const response = await uploadFile(file, (event) => {
        if (event.lengthComputable) {
          const percentCompleted = Math.round((event.loaded * 100) / event.total);
          setUploadProgress(percentCompleted);
        }
      });
      clearInterval(interval); // Clear interval if not already
      setUploadProgress(100);
      setUploadStatus('processing'); // File uploaded, now server is processing

      // Assuming the response contains the initial upload result or a job ID
      // For simplicity, we'll immediately fetch results after a short delay
      setTimeout(async () => {
        await fetchUploadResults(); // Fetch updated results after processing
        setUploadStatus('completed');
      }, 2000); // Simulate server processing time

    } catch (error) {
      const errorMessage = handleApiError(error);
      setCurrentUploadError(errorMessage);
      setUploadStatus('failed');
      setUploadProgress(0);
    }
  };

  const fetchUploadResults = async () => {
    setIsFetchingResults(true);
    setFetchResultsError(null);
    try {
      const results = await getUploadResults();
      setUploadResults(results.data);
    } catch (error) {
      const errorMessage = handleApiError(error);
      setFetchResultsError(errorMessage);
    } finally {
      setIsFetchingResults(false);
    }
  };

  const clearUploadState = () => {
    setUploadStatus('idle');
    setUploadProgress(0);
    setUploadResults([]);
    setCurrentUploadError(null);
    setIsFetchingResults(false);
    setFetchResultsError(null);
  };

  const contextValue: AppContextCombined = {
    user,
    isAuthenticated,
    authStatus,
    login,
    logout,
    uploadStatus,
    uploadProgress,
    uploadResults,
    currentUploadError,
    isFetchingResults,
    fetchResultsError,
    initiateUpload,
    fetchUploadResults,
    clearUploadState,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};