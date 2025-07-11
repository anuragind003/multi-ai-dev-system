import { useContext } from 'react';
import DataContext from '@context/DataContext';
import { DataContextType } from '@types';

/**
 * Custom hook to access data context.
 * Throws an error if used outside of DataContextProvider.
 */
export const useData = (): DataContextType => {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataContextProvider');
  }
  return context;
};