import React, { createContext, useContext, useState, useCallback } from 'react';

export interface FilterState {
  searchQuery: string;
  selectedDate: string; // YYYY-MM-DD
  selectedMonth: string; // MM
  selectedYear: string; // YYYY
}

interface FilterContextType {
  filters: FilterState;
  updateSearchQuery: (query: string) => void;
  updateSelectedDate: (date: string) => void;
  updateSelectedMonth: (month: string) => void;
  updateSelectedYear: (year: string) => void;
  resetFilters: () => void;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

const initialFilterState: FilterState = {
  searchQuery: '',
  selectedDate: '',
  selectedMonth: '',
  selectedYear: String(new Date().getFullYear()), // Default to current year
};

export const FilterProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [filters, setFilters] = useState<FilterState>(initialFilterState);

  const updateSearchQuery = useCallback((query: string) => {
    setFilters(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const updateSelectedDate = useCallback((date: string) => {
    setFilters(prev => ({ ...prev, selectedDate: date }));
  }, []);

  const updateSelectedMonth = useCallback((month: string) => {
    setFilters(prev => ({ ...prev, selectedMonth: month }));
  }, []);

  const updateSelectedYear = useCallback((year: string) => {
    setFilters(prev => ({ ...prev, selectedYear: year }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(initialFilterState);
  }, []);

  const value = {
    filters,
    updateSearchQuery,
    updateSelectedDate,
    updateSelectedMonth,
    updateSelectedYear,
    resetFilters,
  };

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
};

export const useFilters = () => {
  const context = useContext(FilterContext);
  if (context === undefined) {
    throw new Error('useFilters must be used within a FilterProvider');
  }
  return context;
};