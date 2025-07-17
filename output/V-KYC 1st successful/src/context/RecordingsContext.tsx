import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { RecordingsContextType, Recording, FilterParams } from '../types';
import { getRecordings } from '../services/apiClient';
import { useAuth } from './AuthContext'; // To react to auth changes

const RecordingsContext = createContext<RecordingsContextType | undefined>(undefined);

export const RecordingsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [filterParams, setFilterParams] = useState<FilterParams>({ page: 1, limit: 10 });
  const [totalRecordings, setTotalRecordings] = useState<number>(0);

  const fetchRecordings = useCallback(async (paramsOverride?: FilterParams) => {
    if (!isAuthenticated) {
      setRecordings([]);
      setTotalRecordings(0);
      return;
    }

    setLoading(true);
    setError(null);
    const currentParams = { ...filterParams, ...paramsOverride };
    setFilterParams(currentParams); // Update context state with new params

    try {
      const response = await getRecordings(currentParams);
      setRecordings(response.data);
      setTotalRecordings(response.total);
    } catch (err) {
      console.error('Failed to fetch recordings:', err);
      setError('Failed to load recordings. Please try again.');
      setRecordings([]);
      setTotalRecordings(0);
    } finally {
      setLoading(false);
    }
  }, [filterParams, isAuthenticated]);

  // Initial fetch and re-fetch on filterParams change
  useEffect(() => {
    if (isAuthenticated) {
      fetchRecordings();
    }
  }, [isAuthenticated, filterParams.search, filterParams.category, filterParams.minDuration,
      filterParams.maxDuration, filterParams.startDate, filterParams.endDate,
      filterParams.tags, filterParams.page, filterParams.limit, fetchRecordings]); // Re-run when filterParams change

  const value = {
    recordings,
    loading,
    error,
    filterParams,
    setFilterParams,
    fetchRecordings,
    totalRecordings,
  };

  return <RecordingsContext.Provider value={value}>{children}</RecordingsContext.Provider>;
};

export const useRecordings = (): RecordingsContextType => {
  const context = useContext(RecordingsContext);
  if (context === undefined) {
    throw new Error('useRecordings must be used within a RecordingsProvider');
  }
  return context;
};