import { createStore } from 'vuex';
import axios from 'axios';

// Define the base URL for the API.
// It tries to use an environment variable (e.g., set in .env.development or .env.production)
// and falls back to a default localhost address if not defined.
const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5000';

export default createStore({
  // State: Holds the reactive data for the application.
  state: {
    isLoadingMoengageFile: false,
    isLoadingDuplicateFile: false,
    isLoadingUniqueFile: false,
    isLoadingErrorFile: false,
    error: null, // To store any error messages from API calls
  },

  // Mutations: Synchronous functions that modify the state.
  mutations: {
    SET_LOADING_MOENGAGE_FILE(state, status) {
      state.isLoadingMoengageFile = status;
    },
    SET_LOADING_DUPLICATE_FILE(state, status) {
      state.isLoadingDuplicateFile = status;
    },
    SET_LOADING_UNIQUE_FILE(state, status) {
      state.isLoadingUniqueFile = status;
    },
    SET_LOADING_ERROR_FILE(state, status) {
      state.isLoadingErrorFile = status;
    },
    SET_ERROR(state, message) {
      state.error = message;
    },
    CLEAR_ERROR(state) {
      state.error = null;
    },
  },

  // Actions: Asynchronous functions that can commit mutations.
  actions: {
    /**
     * Generic action to handle file downloads from the backend.
     * It manages loading states, error handling, and initiates the file download in the browser.
     * @param {object} context - Vuex context object (contains commit, dispatch, state, getters).
     * @param {object} payload - Object containing download parameters.
     * @param {string} payload.endpoint - The API endpoint to call (e.g., '/exports/moengage-campaign-file').
     * @param {string} payload.filename - The base name for the downloaded file (e.g., 'moengage_data').
     * @param {string} payload.mutationType - The mutation to commit for setting the loading state.
     * @param {string} [payload.fileType='csv'] - The file extension (e.g., 'csv', 'xlsx').
     */
    async downloadFile({ commit }, { endpoint, filename, mutationType, fileType = 'csv' }) {
      commit('CLEAR_ERROR'); // Clear previous errors
      commit(mutationType, true); // Set loading state to true

      try {
        const response = await axios.get(`${API_BASE_URL}${endpoint}`, {
          responseType: 'blob', // Crucial for downloading binary data (files)
        });

        const contentType = response.headers['content-type'];

        // Check if the response is JSON (indicating an error from the backend) or a file blob.
        if (contentType && contentType.includes('application/json')) {
          // If it's JSON, it's likely an error message from the server.
          // Read the blob as text to parse the JSON.
          const reader = new FileReader();
          reader.onload = (e) => {
            try {
              const errorData = JSON.parse(e.target.result);
              commit('SET_ERROR', errorData.message || 'An unknown error occurred during download.');
            } catch (parseError) {
              commit('SET_ERROR', 'Failed to parse error response from server.');
            }
          };
          reader.readAsText(response.data);
        } else {
          // It's a file, proceed with the download.
          const url = window.URL.createObjectURL(new Blob([response.data]));
          const link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', `${filename}.${fileType}`); // Set the download filename
          document.body.appendChild(link);
          link.click(); // Programmatically click the link to trigger download
          document.body.removeChild(link); // Clean up the temporary link
          window.URL.revokeObjectURL(url); // Release the object URL
        }
      } catch (error) {
        console.error(`Error downloading ${filename}:`, error);
        if (error.response && error.response.data) {
          // If the error response also contains a blob, try to read it as text for an error message.
          const reader = new FileReader();
          reader.onload = (e) => {
            try {
              const errorData = JSON.parse(e.target.result);
              commit('SET_ERROR', errorData.message || `Failed to download ${filename}.`);
            } catch (parseError) {
              commit('SET_ERROR', `Failed to download ${filename}. Server error.`);
            }
          };
          reader.readAsText(error.response.data);
        } else {
          // Handle network errors or other non-response errors.
          commit('SET_ERROR', `Network error or server unreachable: ${error.message}`);
        }
      } finally {
        commit(mutationType, false); // Always set loading state to false after attempt
      }
    },

    // Specific actions for each file type, dispatching to the generic downloadFile action.
    async downloadMoengageFile({ dispatch }) {
      await dispatch('downloadFile', {
        endpoint: '/exports/moengage-campaign-file',
        filename: `moengage_campaign_data_${new Date().toISOString().slice(0, 10)}`, // e.g., moengage_campaign_data_2023-10-27
        mutationType: 'SET_LOADING_MOENGAGE_FILE',
        fileType: 'csv',
      });
    },

    async downloadDuplicateFile({ dispatch }) {
      await dispatch('downloadFile', {
        endpoint: '/exports/duplicate-customers',
        filename: `duplicate_customer_data_${new Date().toISOString().slice(0, 10)}`,
        mutationType: 'SET_LOADING_DUPLICATE_FILE',
        fileType: 'csv',
      });
    },

    async downloadUniqueFile({ dispatch }) {
      await dispatch('downloadFile', {
        endpoint: '/exports/unique-customers',
        filename: `unique_customer_data_${new Date().toISOString().slice(0, 10)}`,
        mutationType: 'SET_LOADING_UNIQUE_FILE',
        fileType: 'csv',
      });
    },

    async downloadErrorFile({ dispatch }) {
      await dispatch('downloadFile', {
        endpoint: '/exports/data-errors',
        filename: `data_errors_${new Date().toISOString().slice(0, 10)}`,
        mutationType: 'SET_LOADING_ERROR_FILE',
        fileType: 'xlsx', // As per FR33, this is an Excel file
      });
    },
  },

  // Getters: Functions to retrieve state data, potentially computed.
  getters: {
    isLoadingMoengageFile: (state) => state.isLoadingMoengageFile,
    isLoadingDuplicateFile: (state) => state.isLoadingDuplicateFile,
    isLoadingUniqueFile: (state) => state.isLoadingUniqueFile,
    isLoadingErrorFile: (state) => state.isLoadingErrorFile,
    getError: (state) => state.error,
  },
});