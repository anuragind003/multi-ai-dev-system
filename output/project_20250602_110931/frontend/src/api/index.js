import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        console.error('API Request Interceptor Error:', error.message, error.config);
        return Promise.reject(error);
    }
);

api.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        console.error('API Response Interceptor Error:', error.response?.data || error.message || error, error.config);

        if (error.response) {
            const { status, data } = error.response;

            switch (status) {
                case 400:
                    console.error('Bad Request:', data.message || 'Invalid request data provided.');
                    break;
                case 401:
                    console.warn('Unauthorized: Please log in again.');
                    // Example: localStorage.removeItem('access_token');
                    // Example: window.location.href = '/login';
                    break;
                case 403:
                    console.warn('Forbidden: You do not have permission to perform this action.');
                    break;
                case 404:
                    console.warn('Not Found: The requested resource could not be found.');
                    break;
                case 500:
                    console.error('Internal Server Error: Something went wrong on the server. Please try again later.');
                    break;
                default:
                    console.error(`API Error ${status}:`, data.message || 'An unexpected API error occurred.');
            }
        } else if (error.request) {
            console.error('Network Error: No response received from server. Please check your connection or server status.', error.code);
        } else {
            console.error('Client-side Request Error:', error.message);
        }

        return Promise.reject(error);
    }
);

export default api;