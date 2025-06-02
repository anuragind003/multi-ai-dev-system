const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';

/**
 * Handles common API response parsing and error handling.
 * @param {Response} response - The fetch API response object.
 * @returns {Promise<any>} - A promise that resolves with the JSON data or rejects with an error.
 */
async function handleApiResponse(response) {
    if (response.ok) {
        const contentType = response.headers.get('content-type');
        // Check if the response has content and is JSON before trying to parse.
        // Also, explicitly check for 204 No Content, as it should not have a body.
        if (contentType && contentType.includes('application/json') && response.status !== 204) {
            return response.json();
        }
        // If no JSON content, 204 No Content, or other successful status without expected JSON, return an empty object.
        return {};
    } else {
        let errorData = {};
        try {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                errorData = await response.json();
            } else {
                // Fallback to text if not JSON, or if content-type is missing.
                // Provide a default message if response.text() is empty.
                errorData = { message: await response.text() || `Server error: ${response.status}` };
            }
        } catch (e) {
            // Catch errors that occur during the parsing of the error response body (e.g., malformed JSON).
            errorData = { message: `Failed to parse error response from server (Status: ${response.status})`, originalError: e.message };
        }
        const errorMessage = errorData.message || `API Error: ${response.status} ${response.statusText}`;
        const error = new Error(errorMessage);
        error.status = response.status;
        error.data = errorData; // Attach full error data for more detailed handling if needed.
        throw error;
    }
}

// Common headers for API requests, promoting consistency.
const commonHeaders = {
    'Content-Type': 'application/json',
};

/**
 * Registers a new user with the provided email and password.
 * @param {string} email - The user's email address.
 * @param {string} password - The user's password.
 * @returns {Promise<object>} - A promise that resolves with the registration success message or rejects with an error.
 */
export async function register(email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: commonHeaders,
            body: JSON.stringify({ email, password }),
        });
        return await handleApiResponse(response);
    } catch (error) {
        console.error('Registration failed:', error);
        throw error; // Re-throw to be caught by the calling component.
    }
}

/**
 * Logs in a user with the provided email and password.
 * On successful login, stores the authentication token in localStorage.
 * @param {string} email - The user's email address.
 * @param {string} password - The user's password.
 * @returns {Promise<object>} - A promise that resolves with user data and token, or rejects with an error.
 */
export async function login(email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: commonHeaders,
            body: JSON.stringify({ email, password }),
        });

        const data = await handleApiResponse(response);

        // Assuming the backend returns a token upon successful login.
        if (data.access_token) {
            localStorage.setItem('authToken', data.access_token);
            // Optionally store user info if returned by the backend, e.g.:
            // localStorage.setItem('userEmail', data.user.email);
        }
        return data;
    } catch (error) {
        console.error('Login failed:', error);
        throw error;
    }
}

/**
 * Logs out the current user.
 * Clears the authentication token from localStorage.
 * @returns {Promise<object>} - A promise that resolves with a success message or rejects with an error.
 */
export async function logout() {
    try {
        const token = localStorage.getItem('authToken');
        if (token) {
            // Optionally, send a request to the backend to invalidate the token/session.
            // This depends on whether the backend supports token invalidation on logout.
            // For JWTs, often client-side deletion is sufficient, but for session-based
            // authentication, a backend call is crucial.
            const response = await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: {
                    ...commonHeaders, // Include common headers
                    'Authorization': `Bearer ${token}` // Send token for backend validation/invalidation
                },
            });
            // Process response. handleApiResponse will throw if the backend call fails,
            // which will be caught by the outer try-catch block.
            await handleApiResponse(response);
        }

        // Always clear client-side token regardless of backend logout success or failure.
        localStorage.removeItem('authToken');
        // Optionally remove other user-related data, e.g.:
        // localStorage.removeItem('userEmail');

        return { message: 'Logged out successfully' };
    } catch (error) {
        // This catch block will handle errors from the fetch call itself (e.g., network issues)
        // or errors thrown by handleApiResponse if the backend logout failed.
        console.error('Logout failed (client-side token cleared anyway):', error);
        // Ensure token is cleared even if an error occurred during the API call.
        localStorage.removeItem('authToken');
        // Optionally remove other user-related data, e.g.:
        // localStorage.removeItem('userEmail');
        throw error; // Re-throw to inform the UI about the backend logout failure.
    }
}

/**
 * Retrieves the authentication token from localStorage.
 * @returns {string | null} - The authentication token or null if not found.
 */
export function getAuthToken() {
    return localStorage.getItem('authToken');
}

/**
 * Checks if the user is currently authenticated by checking for an auth token.
 * Note: This only checks for the presence of a token, not its validity or expiration.
 * For full validation, a backend endpoint (e.g., /auth/verify-token) would be needed.
 * @returns {boolean} - True if an auth token exists, false otherwise.
 */
export function isAuthenticated() {
    return !!getAuthToken();
}