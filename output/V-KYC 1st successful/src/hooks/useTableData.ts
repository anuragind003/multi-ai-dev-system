// src/hooks/useTableData.ts
import { useState, useEffect, useCallback } from 'react';
import { fetchTableData } from '../services/api';
import { TableRecord, UseTableDataOptions, UseTableDataResult } from '../types';

/**
 * Custom hook for managing paginated, searchable table data.
 * Includes loading, error states, and debouncing for search input.
 */
export const useTableData = (options?: UseTableDataOptions): UseTableDataResult<TableRecord> => {
  const { initialPage = 1, initialPageSize = 10, debounceTime = 300 } = options || {};

  const [data, setData] = useState<TableRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [pageSize, setPageSize] = useState<number>(initialPageSize);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState<string>(searchTerm);

  // Debounce effect for search term
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, debounceTime);

    return () => {
      clearTimeout(handler);
    };
  }, [searchTerm, debounceTime]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTableData(currentPage, pageSize, debouncedSearchTerm);
      setData(response.data);
      setTotalRecords(response.totalRecords);
      setTotalPages(response.totalPages);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
      setData([]); // Clear data on error
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, debouncedSearchTerm]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const goToPage = useCallback((page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  }, [totalPages]);

  const handlePageSizeChange = useCallback((size: number) => {
    setPageSize(size);
    setCurrentPage(1); // Reset to first page when page size changes
  }, []);

  const refreshData = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    currentPage,
    pageSize,
    totalPages,
    totalRecords,
    searchTerm,
    setSearchTerm,
    goToPage,
    setPageSize: handlePageSizeChange,
    refreshData,
  };
};