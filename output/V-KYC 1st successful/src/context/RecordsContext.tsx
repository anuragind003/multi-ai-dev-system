import React, { createContext, useContext, useState, useCallback } from 'react';
import { RecordsContextType, Record } from '@types';
import { fetchRecords as apiFetchRecords, downloadRecord as apiDownloadRecord } from '@api/apiService';
import { toast } from 'react-toastify';

const RecordsContext = createContext<RecordsContextType | undefined>(undefined);

export const RecordsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [records, setRecords] = useState<Record[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetchRecords();
      if (response.success && response.data) {
        setRecords(response.data);
      } else {
        setError(response.message || 'Failed to fetch records.');
        toast.error(response.message || 'Failed to fetch records.');
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred while fetching records.');
      // Toast is already handled by apiService interceptor
    } finally {
      setLoading(false);
    }
  }, []);

  const downloadRecord = useCallback(async (recordId: string, fileName: string) => {
    setLoading(true); // Can be a separate download-specific loading state if needed
    setError(null);
    try {
      await apiDownloadRecord(recordId);
      // Success toast is handled within apiDownloadRecord
    } catch (err: any) {
      setError(err.message || `Failed to download ${fileName}.`);
      // Toast is already handled by apiService interceptor
    } finally {
      setLoading(false);
    }
  }, []);

  const contextValue = {
    records,
    loading,
    error,
    fetchRecords,
    downloadRecord,
  };

  return (
    <RecordsContext.Provider value={contextValue}>
      {children}
    </RecordsContext.Provider>
  );
};

export const useRecords = () => {
  const context = useContext(RecordsContext);
  if (context === undefined) {
    throw new Error('useRecords must be used within a RecordsProvider');
  }
  return context;
};