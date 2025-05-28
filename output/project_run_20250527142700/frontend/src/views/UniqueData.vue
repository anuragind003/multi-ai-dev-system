<template>
  <div class="unique-data-container">
    <h1>Download Unique Customer Data</h1>
    <p>Click the button below to download the file containing unique customer profiles after deduplication.</p>

    <button @click="downloadUniqueData" :disabled="isLoading">
      <span v-if="isLoading">Downloading...</span>
      <span v-else>Download Unique Data File</span>
    </button>

    <div v-if="isLoading" class="message loading">
      Preparing your file. This may take a moment...
    </div>

    <div v-if="downloadSuccess" class="message success">
      File downloaded successfully!
    </div>

    <div v-if="errorMessage" class="message error">
      Error: {{ errorMessage }}
    </div>
  </div>
</template>

<script>
import axios from 'axios';

// Define the base URL for the backend API.
// Using import.meta.env for Vite-based projects, fallback to localhost for development.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export default {
  name: 'UniqueData',
  data() {
    return {
      isLoading: false,
      downloadSuccess: false,
      errorMessage: '',
    };
  },
  methods: {
    /**
     * Initiates the download of the unique customer data file from the backend.
     * This method makes an API call to the /exports/unique-customers endpoint,
     * handles the file download, and updates the UI state.
     */
    async downloadUniqueData() {
      this.isLoading = true;
      this.downloadSuccess = false;
      this.errorMessage = '';

      try {
        // Make a GET request to the unique-customers export endpoint
        // responseType: 'blob' is crucial for handling binary data like CSV files
        const response = await axios.get(`${API_BASE_URL}/exports/unique-customers`, {
          responseType: 'blob',
        });

        // Create a Blob from the response data with the correct MIME type for CSV
        const blob = new Blob([response.data], { type: 'text/csv' });

        // Create a temporary URL for the Blob
        const url = window.URL.createObjectURL(blob);

        // Create a temporary anchor (<a>) element to trigger the download
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'unique_customer_data.csv'); // Set the desired filename

        // Append the link to the document body, click it, and then remove it
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Revoke the object URL to free up memory
        window.URL.revokeObjectURL(url);

        this.downloadSuccess = true;
      } catch (error) {
        console.error('Error downloading unique data file:', error);
        this.errorMessage = 'Failed to download unique data file. Please try again.';

        // Attempt to parse error message from blob response if available
        if (error.response && error.response.data instanceof Blob) {
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const errorJson = JSON.parse(reader.result);
              this.errorMessage = errorJson.message || this.errorMessage;
            } catch (e) {
              // If it's not a JSON error, keep the generic message
            }
          };
          reader.readAsText(error.response.data);
        } else if (error.response && error.response.data && typeof error.response.data === 'object') {
          // For non-blob errors (e.g., JSON error from backend)
          this.errorMessage = error.response.data.message || this.errorMessage;
        }
      } finally {
        this.isLoading = false;
      }
    },
  },
};
</script>

<style scoped>
.unique-data-container {
  max-width: 800px;
  margin: 50px auto;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background-color: #ffffff;
  text-align: center;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h1 {
  color: #2c3e50;
  margin-bottom: 20px;
  font-size: 2em;
}

p {
  color: #555;
  margin-bottom: 30px;
  line-height: 1.6;
}

button {
  background-color: #4CAF50; /* Green */
  color: white;
  padding: 12px 25px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1.1em;
  transition: background-color 0.3s ease, transform 0.2s ease;
  min-width: 200px;
}

button:hover:not(:disabled) {
  background-color: #45a049;
  transform: translateY(-2px);
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.message {
  margin-top: 25px;
  padding: 15px;
  border-radius: 5px;
  font-weight: bold;
}

.loading {
  background-color: #e0f7fa;
  color: #00796b;
  border: 1px solid #b2ebf2;
}

.success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.error {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #ef9a9a;
}
</style>