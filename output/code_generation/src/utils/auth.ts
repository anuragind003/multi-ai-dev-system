import Cookies from 'js-cookie';

// For production, JWTs should ideally be stored in HttpOnly cookies set by the server.
// This prevents client-side JavaScript from accessing them, mitigating XSS attacks.
// For demonstration purposes, we'll use js-cookie to simulate cookie handling.
// If HttpOnly cookies are not feasible, localStorage is an alternative, but less secure.

const TOKEN_KEY = 'jwt_token';
const USER_KEY = 'user_data';

/**
 * Sets the JWT token and user data.
 * In a real application, the token would be set by the server as an HttpOnly cookie.
 * Here, we use js-cookie for client-side cookie management for demonstration.
 * If using localStorage, replace Cookies.set/get/remove with localStorage.setItem/getItem/removeItem.
 * @param token The JWT token.
 * @param user The user data object.
 */
export const setAuthData = (token: string, user: any): void => {
  // Store token in a cookie (or localStorage)
  Cookies.set(TOKEN_KEY, token, { expires: 7, secure: import.meta.env.PROD, sameSite: 'Lax' }); // Expires in 7 days, secure in production
  // Store user data in localStorage (or sessionStorage)
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

/**
 * Retrieves the JWT token.
 * @returns The JWT token string or null if not found.
 */
export const getAuthToken = (): string | null => {
  return Cookies.get(TOKEN_KEY) || null;
};

/**
 * Retrieves the stored user data.
 * @returns The user data object or null if not found.
 */
export const getAuthUser = (): any | null => {
  const userData = localStorage.getItem(USER_KEY);
  return userData ? JSON.parse(userData) : null;
};

/**
 * Removes the JWT token and user data.
 */
export const removeAuthData = (): void => {
  Cookies.remove(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

/**
 * Removes only the JWT token.
 */
export const removeAuthToken = (): void => {
  Cookies.remove(TOKEN_KEY);
};