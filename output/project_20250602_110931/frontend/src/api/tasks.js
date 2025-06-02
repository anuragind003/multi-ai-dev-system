import axios from 'axios';

// Base URL for the backend API.
// It attempts to use an environment variable (common in React apps)
// and falls back to a default localhost URL for development.
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';

/**
 * Retrieves the authentication token from local storage.
 * This token is expected to be set upon successful user login.
 * @returns {string | null} The authentication token if found, otherwise null.
 */
const getAuthToken = () => {
  return localStorage.getItem('authToken'); // Assuming the token is stored under 'authToken'
};

/**
 * Configures an Axios instance with common headers and an interceptor
 * to automatically include the authorization token in requests.
 */
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the Bearer token in the Authorization header
// for every outgoing request, if a token exists.
axiosInstance.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // Do something with request error (e.g., log it)
    return Promise.reject(error);
  }
);

/**
 * Centralized error handling for API calls.
 * Logs the detailed error and throws a new Error with a user-friendly message.
 * @param {Error} error - The error object from the Axios catch block.
 * @param {string} defaultMessage - A default message to use if no specific error message is available from the API.
 * @param {string | null} [taskId=null] - Optional task ID for more specific error messages.
 * @throws {Error} A new Error object with a refined message.
 */
const handleApiError = (error, defaultMessage, taskId = null) => {
  const context = taskId ? ` with ID ${taskId}` : '';
  const apiErrorMessage = error.response?.data?.message;
  const errorMessageToThrow = apiErrorMessage || error.message || `${defaultMessage}${context}.`;

  console.error(`${defaultMessage}${context}:`, error.response?.data || error.message || error);
  throw new Error(errorMessageToThrow);
};

/**
 * Fetches all tasks for the authenticated user.
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of task objects.
 * @throws {Error} If the API call fails (e.g., network error, unauthorized, server error).
 */
export const getTasks = async () => {
  try {
    const response = await axiosInstance.get('/tasks');
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to fetch tasks');
  }
};

/**
 * Fetches a single task by its ID.
 * @param {string} taskId - The unique identifier of the task to fetch.
 * @returns {Promise<Object>} A promise that resolves to a single task object.
 * @throws {Error} If the API call fails or the task is not found.
 */
export const getTaskById = async (taskId) => {
  try {
    const response = await axiosInstance.get(`/tasks/${taskId}`);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to fetch task', taskId);
  }
};

/**
 * Creates a new task.
 * @param {Object} taskData - The data for the new task.
 *   Expected properties: `title` (string), `description` (string, optional), `due_date` (string, optional, ISO format).
 * @returns {Promise<Object>} A promise that resolves to the newly created task object.
 * @throws {Error} If the API call fails (e.g., validation errors, unauthorized).
 */
export const createTask = async (taskData) => {
  try {
    const response = await axiosInstance.post('/tasks', taskData);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to create task');
  }
};

/**
 * Updates an existing task.
 * @param {string} taskId - The ID of the task to update.
 * @param {Object} taskData - The updated data for the task.
 *   Can include `title`, `description`, `due_date`, `is_complete`.
 * @returns {Promise<Object>} A promise that resolves to the updated task object.
 * @throws {Error} If the API call fails.
 */
export const updateTask = async (taskId, taskData) => {
  try {
    const response = await axiosInstance.put(`/tasks/${taskId}`, taskData);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to update task', taskId);
  }
};

/**
 * Deletes a task by its ID.
 * @param {string} taskId - The ID of the task to delete.
 * @returns {Promise<Object>} A promise that resolves to a confirmation object
 *   (e.g., `{ message: 'Task deleted successfully' }`).
 * @throws {Error} If the API call fails.
 */
export const deleteTask = async (taskId) => {
  try {
    const response = await axiosInstance.delete(`/tasks/${taskId}`);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to delete task', taskId);
  }
};

/**
 * Marks a task as complete or incomplete.
 * This function specifically updates the `is_complete` status of a task.
 * It uses a PUT request to the task's endpoint, sending only the `is_complete` field.
 * @param {string} taskId - The ID of the task to update.
 * @param {boolean} isComplete - True to mark as complete, false to mark as incomplete.
 * @returns {Promise<Object>} A promise that resolves to the updated task object.
 * @throws {Error} If the API call fails.
 */
export const markTaskComplete = async (taskId, isComplete) => {
  try {
    // Send a PUT request with only the `is_complete` field.
    // The backend is expected to handle partial updates or merge this field.
    const response = await axiosInstance.put(`/tasks/${taskId}`, { is_complete: isComplete });
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to update task completion status', taskId);
  }
};