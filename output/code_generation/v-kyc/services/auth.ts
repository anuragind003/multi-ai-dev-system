import { User } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

// Token storage keys
const TOKEN_KEY = 'vkyc_token';
const USER_KEY = 'vkyc_user';

// Helper to handle API responses
const handleResponse = async (response: Response) => {
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }
    return response.json();
};

// Token management
export const getToken = (): string | null => {
    return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token);
};

export const removeToken = (): void => {
    localStorage.removeItem(TOKEN_KEY);
};

export const getUser = (): User | null => {
    const userStr = localStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
};

export const setUser = (user: User): void => {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const removeUser = (): void => {
    localStorage.removeItem(USER_KEY);
};

// Check if token is expired
export const isTokenExpired = (): boolean => {
    const token = getToken();
    if (!token) return true;

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.exp * 1000 < Date.now();
    } catch (error) {
        return true;
    }
};

// Login function
export const login = async (username: string, password: string): Promise<{ user: User; token: string }> => {
    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        const data = await handleResponse(response);
        
        // Store token and user data
        setToken(data.token);
        setUser(data.user);
        
        return data;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
};

// Logout function
export const logout = (): void => {
    removeToken();
    removeUser();
};

// Verify token with backend
export const verifyToken = async (): Promise<boolean> => {
    const token = getToken();
    if (!token || isTokenExpired()) {
        logout();
        return false;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/verify-token`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });

        if (response.ok) {
            return true;
        } else {
            logout();
            return false;
        }
    } catch (error) {
        console.error('Token verification error:', error);
        logout();
        return false;
    }
};

// Get authorization header for API requests
export const getAuthHeader = (): { Authorization: string } | {} => {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
};

// Auto-refresh token (if needed)
export const refreshToken = async (): Promise<boolean> => {
    // For now, we'll just verify the current token
    // In a more complex setup, you might want to implement token refresh
    return await verifyToken();
}; 