import { useAuthContext, useFilterContext } from '../context/AppContext';

/**
 * Custom hook for authentication state and actions.
 * @returns {AuthContextType} Authentication context values.
 */
export const useAuth = useAuthContext;

/**
 * Custom hook for filter state and actions.
 * @returns {FilterContextType} Filter context values.
 */
export const useFilters = useFilterContext;