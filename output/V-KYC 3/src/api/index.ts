// Define common API types
export interface ApiResponse<T> {
  data?: T;
  message: string;
  success: boolean;
  statusCode?: number;
  error?: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user';
}

export interface AuthResponseData {
  token: string;
  user: User;
}

// Basic API client setup
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

interface RequestOptions extends RequestInit {
  token?: string;
}

async function apiFetch<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  const { headers, token, ...restOptions } = options;

  const config: RequestInit = {
    ...restOptions,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Something went wrong', error: 'Unknown error' }));
      return {
        success: false,
        message: errorData.message || `HTTP error! Status: ${response.status}`,
        statusCode: response.status,
        error: errorData.error || response.statusText,
      };
    }

    const data: T = await response.json();
    return {
      success: true,
      data,
      message: 'Request successful',
      statusCode: response.status,
    };
  } catch (error) {
    console.error('API call failed:', error);
    return {
      success: false,
      message: 'Network error or server unreachable',
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

// Specific API services
export const authService = {
  login: async (credentials: { username: string; password: string }): Promise<ApiResponse<AuthResponseData>> => {
    return apiFetch<AuthResponseData>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  },

  getProfile: async (token: string): Promise<ApiResponse<User>> => {
    return apiFetch<User>('/auth/profile', {
      method: 'GET',
      token,
    });
  },
};

export const userService = {
  getDashboardData: async (token: string): Promise<ApiResponse<{ stats: string; recentActivities: string[] }>> => {
    // Simulate a real API call
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          success: true,
          message: 'Dashboard data fetched successfully',
          data: {
            stats: 'Total Users: 1200, Active Sessions: 850',
            recentActivities: [
              'User John Doe logged in.',
              'Report generated for Q1.',
              'System update applied.',
            ],
          },
        });
      }, 500);
    });
    // In a real app:
    // return apiFetch<{ stats: string; recentActivities: string[] }>('/dashboard', {
    //   method: 'GET',
    //   token,
    // });
  },
};