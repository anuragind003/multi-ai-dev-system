import { createStore } from 'vuex';
import axios from 'axios';

// Base URL for the backend API
const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5000/api';

export default createStore({
  state: {
    isLoading: false,
    error: null,
    customerProfile: null,
    uploadStatus: null,
    // Potentially add state for reports if they become more complex than direct downloads
  },
  mutations: {
    SET_LOADING(state, status) {
      state.isLoading = status;
    },
    SET_ERROR(state, message) {
      state.error = message;
    },
    CLEAR_ERROR(state) {
      state.error = null;
    },
    SET_CUSTOMER_PROFILE(state, profile) {
      state.customerProfile = profile;
    },
    SET_UPLOAD_STATUS(state, status) {
      state.uploadStatus = status;
    },
    CLEAR_UPLOAD_STATUS(state) {
      state.uploadStatus = null;
    }
  },
  actions: {
    /**
     * Uploads customer details file (Prospect, TW Loyalty, Topup, Employee loans) via Admin Portal.
     * @param {Object} context - Vuex context object.
     * @param {Object} payload - Contains file and loan type.
     * @param {File} payload.file - The file to upload.
     * @param {string} payload.loanType - The type of loan (e.g., 'Prospect', 'TW Loyalty').
     */
    async uploadCustomerData({ commit }, payload) {
      commit('SET_LOADING', true);
      commit('CLEAR_ERROR');
      commit('CLEAR_UPLOAD_STATUS');
      try {
        const formData = new FormData();
        formData.append('file', payload.file);
        formData.append('loan_type', payload.loanType);

        const response = await axios.post(`${API_BASE_URL}/admin/customer-data/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        commit('SET_UPLOAD_STATUS', response.data);
        return response.data;
      } catch (err) {
        const errorMessage = err.response?.data?.message || err.message || 'Failed to upload customer data.';
        commit('SET_ERROR', errorMessage);
        throw err; // Re-throw to allow component to handle
      } finally {
        commit('SET_LOADING', false);
      }
    },

    /**
     * Fetches a single customer's profile view with associated offers and journey stages.
     * @param {Object} context - Vuex context object.
     * @param {string} customerId - The ID of the customer to fetch.
     */
    async fetchCustomerProfile({ commit }, customerId) {
      commit('SET_LOADING', true);
      commit('CLEAR_ERROR');
      try {
        const response = await axios.get(`${API_BASE_URL}/customers/${customerId}`);
        commit('SET_CUSTOMER_PROFILE', response.data);
        return response.data;
      } catch (err) {
        const errorMessage = err.response?.data?.message || err.message || `Failed to fetch customer profile for ID: ${customerId}.`;
        commit('SET_ERROR', errorMessage);
        throw err;
      } finally {
        commit('SET_LOADING', false);
      }
    },

    /**
     * Generates and allows download of the Moengage format CSV file for campaigns.
     * @param {Object} context - Vuex context object.
     */
    async downloadMoengageFile({ commit }) {
      commit('SET_LOADING', true);
      commit('CLEAR_ERROR');
      try {
        const response = await axios.get(`${API_BASE_URL}/campaigns/moengage-export`, {
          responseType: 'blob' // Important for downloading files
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'moengage_campaign_data.csv'); // Or get filename from headers if available
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        const errorMessage = err.response?.data?.message || err.message || 'Failed to download Moengage file.';
        commit('SET_ERROR', errorMessage);
        throw err;
      } finally {
        commit('SET_LOADING', false);
      }
    },

    /**
     * Allows download of a file containing identified duplicate customer records.
     * @param {Object} context - Vuex context object.
     */
    async downloadDuplicateDataFile({ commit }) {
      commit('SET_LOADING', true);
      commit('CLEAR_ERROR');
      try {
        const response = await axios.get(`${API_BASE_URL}/data/duplicates`, {
          responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'duplicate_customer_data.csv');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        const errorMessage = err.response?.data?.message || err.message || 'Failed to download duplicate data file.';
        commit('SET_ERROR', errorMessage);
        throw err;
      } finally {
        commit('SET_LOADING', false);
      }
    },

    /**
     * Allows download of a file containing unique customer records after deduplication.
     * @param {Object} context - Vuex context object.
     */
    async downloadUniqueDataFile({ commit }) {
      commit('SET_LOADING', true);
      commit('CLEAR_ERROR');
      try {
        const response = await axios.get(`${API_BASE_URL}/data/unique`, {
          responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'unique_customer_data.csv');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        const errorMessage = err.response?.data?.message || err.message || 'Failed to download unique data file.';
        commit('SET_ERROR', errorMessage);
        throw err;
      } finally {
        commit('SET_LOADING', false);
      }
    },

    /**
     * Allows download of an Excel file detailing errors from data ingestion processes.
     * @param {Object} context - Vuex context object.
     */
    async downloadErrorFile({ commit }) {
      commit('SET_LOADING', true);
      commit('CLEAR_ERROR');
      try {
        const response = await axios.get(`${API_BASE_URL}/data/errors`, {
          responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'data_errors.xlsx'); // Assuming Excel file
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        const errorMessage = err.response?.data?.message || err.message || 'Failed to download error file.';
        commit('SET_ERROR', errorMessage);
        throw err;
      } finally {
        commit('SET_LOADING', false);
      }
    },

    // Action to clear error messages
    clearErrorMessage({ commit }) {
      commit('CLEAR_ERROR');
    },

    // Action to clear upload status messages
    clearUploadStatus({ commit }) {
      commit('CLEAR_UPLOAD_STATUS');
    }
  },
  getters: {
    isLoading: state => state.isLoading,
    error: state => state.error,
    customerProfile: state => state.customerProfile,
    uploadStatus: state => state.uploadStatus,
  }
});