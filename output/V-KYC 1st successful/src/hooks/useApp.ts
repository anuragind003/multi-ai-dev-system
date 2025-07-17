// src/hooks/useApp.ts
import { useGlobalContext } from '../context/GlobalContext';

/**
 * Custom hook to access the global application context.
 * Provides access to user authentication state, recordings data,
 * loading states, errors, and actions like login, logout, and fetching recordings.
 */
export const useApp = () => {
  return useGlobalContext();
};