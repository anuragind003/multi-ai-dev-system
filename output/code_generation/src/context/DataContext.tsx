import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { TableDataItem } from '../types';
import { fetchTableData } from '../services/api';

interface DataContextType {
  data: TableDataItem[];
  loading: boolean;
  error: string | null;
  currentPage: number;
  totalPages: number;
  totalRecords: number;
  itemsPerPage: number;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  goToPage: (page: number) => void;
  refreshData: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

// Custom hook for debouncing a value
const useDebounce = <T,>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [data, setData] = useState<TableDataItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [searchTerm, setSearchTermState] = useState<string>('');

  const itemsPerPage = 10;
  const debouncedSearchTerm = useDebounce(searchTerm, 500); // Debounce search input

  const totalPages = useMemo(() => Math.ceil(totalRecords / itemsPerPage), [totalRecords, itemsPerPage]);

  const fetchData = useCallback(async (page: number, search: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTableData(page, itemsPerPage, search);
      setData(response.data);
      setTotalRecords(response.totalRecords);
      setCurrentPage(page);
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError('Failed to load data. Please try again.');
      setData([]);
      setTotalRecords(0);
    } finally {
      setLoading(false);
    }
  }, [itemsPerPage]);

  useEffect(() => {
    // Reset page to 1 when search term changes
    setCurrentPage(1);
    fetchData(1, debouncedSearchTerm);
  }, [debouncedSearchTerm, fetchData]);

  const goToPage = useCallback((page: number) => {
    if (page >= 1 && page <= totalPages) {
      fetchData(page, debouncedSearchTerm);
    }
  }, [totalPages, debouncedSearchTerm, fetchData]);

  const refreshData = useCallback(() => {
    fetchData(currentPage, debouncedSearchTerm);
  }, [currentPage, debouncedSearchTerm, fetchData]);

  const setSearchTerm = useCallback((term: string) => {
    setSearchTermState(term);
  }, []);

  const contextValue = useMemo(() => ({
    data,
    loading,
    error,
    currentPage,
    totalPages,
    totalRecords,
    itemsPerPage,
    searchTerm,
    setSearchTerm,
    goToPage,
    refreshData,
  }), [data, loading, error, currentPage, totalPages, totalRecords, itemsPerPage, searchTerm, setSearchTerm, goToPage, refreshData]);

  return (
    <DataContext.Provider value={contextValue}>
      {children}
    </DataContext.Provider>
  );
};

export const useData = () => {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
};