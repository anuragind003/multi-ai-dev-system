const TOKEN_KEY = 'authToken';

/**
 * Stores the authentication token in localStorage.
 * @param token The token string to store.
 */
export const setAuthToken = (token: string): void => {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (error) {
    console.error('Error storing token in localStorage:', error);
    // Handle cases where localStorage might be unavailable (e.g., privacy mode)
  }
};

/**
 * Retrieves the authentication token from localStorage.
 * @returns The token string or null if not found.
 */
export const getAuthToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (error) {
    console.error('Error retrieving token from localStorage:', error);
    return null;
  }
};

/**
 * Removes the authentication token from localStorage.
 */
export const removeAuthToken = (): void => {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (error) {
    console.error('Error removing token from localStorage:', error);
  }
};