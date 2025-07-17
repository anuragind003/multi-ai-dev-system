import { User, Recording } from '../types';
import { getAuthHeader, logout } from './auth';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

// Helper to handle API responses
const handleResponse = async (response: Response) => {
    if (!response.ok) {
        if (response.status === 401) {
            // Token expired or invalid
            logout();
            throw new Error('Session expired. Please login again.');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }
    return response.json();
};

// Helper to make authenticated API requests
const makeAuthenticatedRequest = async (url: string, options: RequestInit = {}) => {
    const authHeader = getAuthHeader();
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...authHeader,
            ...options.headers,
        },
    });
    return handleResponse(response);
};

/**
 * Authenticates a user against the backend API.
 */
export const loginUser = async (username: string, password: string): Promise<User | null> => {
    console.log(`Attempting login for user: ${username}`);
    
    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        if (response.ok) {
            const user = await response.json();
            console.log('Login successful:', user);
            return user;
        } else {
            console.log('Login failed: Invalid credentials');
            return null;
        }
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
};

interface SearchParams {
    lanId?: string;
    date?: string;
    month?: string;
    lanIds?: string[];
}

/**
 * Searches for recordings in the backend database based on various criteria.
 */
export const searchRecordings = async (params: any): Promise<Recording[]> => {
    console.log("Searching with params:", params);

    try {
        let url: string;
        let options: RequestInit = {
            method: 'GET',
        };

        if (params.lanIds && params.lanIds.length > 0) {
            // Bulk search using POST
            url = `${API_BASE_URL}/recordings/search/bulk`;
            options.method = 'POST';
            options.body = JSON.stringify({ lanIds: params.lanIds });
        } else {
            // Single search using GET
            const searchParams = new URLSearchParams();
            if (params.lanId) searchParams.append('lanId', params.lanId);
            if (params.date) searchParams.append('date', params.date);
            if (params.month) searchParams.append('month', params.month);
            if (params.startDate) searchParams.append('startDate', params.startDate);
            if (params.endDate) searchParams.append('endDate', params.endDate);
            if (params.status) searchParams.append('status', params.status);
            if (params.fileSize) searchParams.append('fileSize', params.fileSize);
            
            url = `${API_BASE_URL}/recordings/search?${searchParams.toString()}`;
        }

        const results = await makeAuthenticatedRequest(url, options);
        console.log(`Found ${results.length} results.`);
        return results;
    } catch (error) {
        console.error('Search error:', error);
        throw error;
    }
};

/**
 * Fetches the 10 most recent recordings from the backend database.
 */
export const getRecentRecordings = async (): Promise<Recording[]> => {
    console.log("Fetching recent recordings");
    
    try {
        const recent = await makeAuthenticatedRequest(`${API_BASE_URL}/recordings/recent`);
        return recent;
    } catch (error) {
        console.error('Error fetching recent recordings:', error);
        throw error;
    }
};

/**
 * Downloads a single recording from the NFS server via SFTP.
 */
export const downloadSingleRecording = async (lanId: string): Promise<void> => {
    console.log(`Initiating download for single LAN ID: ${lanId}`);
    
    try {
        const authHeader = getAuthHeader();
        const response = await fetch(`${API_BASE_URL}/recordings/download/${lanId}`, {
            method: 'GET',
            headers: {
                ...authHeader,
            },
        });

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                throw new Error('Session expired. Please login again.');
            }
            throw new Error(`Download failed: ${response.statusText}`);
        }

        // Create a blob from the response and trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `${lanId}_recording.mp4`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Download error:', error);
        throw error;
    }
};

/**
 * Downloads multiple recordings as a ZIP file from the NFS server via SFTP.
 */
export const downloadBulkRecordings = async (lanIds: string[]): Promise<void> => {
    console.log(`Initiating bulk download for ${lanIds.length} IDs.`);
    
    try {
        const authHeader = getAuthHeader();
        const response = await fetch(`${API_BASE_URL}/recordings/download-bulk`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeader,
            },
            body: JSON.stringify({ lanIds }),
        });

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                throw new Error('Session expired. Please login again.');
            }
            throw new Error(`Bulk download failed: ${response.statusText}`);
        }

        // Create a blob from the response and trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `VKYC_Recordings_${new Date().toISOString().split('T')[0]}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Bulk download error:', error);
        throw error;
    }
};

/**
 * Verifies the current token with the backend.
 */
export const verifyToken = async (): Promise<boolean> => {
    try {
        const authHeader = getAuthHeader();
        const response = await fetch(`${API_BASE_URL}/verify-token`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...authHeader,
            },
        });
        return response.ok;
    } catch (error) {
        console.error('Token verification error:', error);
        return false;
    }
};
