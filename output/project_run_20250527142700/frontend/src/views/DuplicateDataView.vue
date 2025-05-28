<template>
  <div class="duplicate-data-view">
    <h1>Duplicate Customer Data</h1>
    <p>Download a file containing customer data identified as duplicates by the CDP system.</p>

    <button @click="downloadDuplicateData" :disabled="loading">
      <span v-if="loading">Downloading...</span>
      <span v-else>Download Duplicate Data File</span>
    </button>

    <div v-if="message" class="message success">
      {{ message }}
    </div>
    <div v-if="error" class="message error">
      {{ error }}
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DuplicateDataView',
  data() {
    return {
      loading: false,
      message: '',
      error: '',
    };
  },
  methods: {
    async downloadDuplicateData() {
      this.loading = true;
      this.message = '';
      this.error = '';

      try {
        // Make a GET request to the backend API endpoint for duplicate data export
        const response = await axios.get('/api/exports/duplicate-customers', {
          responseType: 'blob', // Important for downloading files
        });

        // Create a blob from the response data
        const blob = new Blob([response.data], { type: 'text/csv' });

        // Create a link element
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);

        // Extract filename from Content-Disposition header if available, otherwise use a default
        const contentDisposition = response.headers['content-disposition'];
        let filename = 'duplicate_customers.csv';
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1];
          }
        }

        link.setAttribute('download', filename); // Set the download attribute with the filename
        document.body.appendChild(link); // Append to the body
        link.click(); // Programmatically click the link to trigger the download
        document.body.removeChild(link); // Clean up the DOM

        this.message = `File "${filename}" downloaded successfully!`;
      } catch (err) {
        console.error('Error downloading duplicate data:', err);
        if (err.response && err.response.data) {
          // Try to read error message from blob if it's an error response
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const errorData = JSON.parse(reader.result);
              this.error = errorData.message || 'An unknown error occurred during download.';
            } catch (e) {
              this.error = 'Failed to download file. Please try again. (Could not parse error response)';
            }
          };
          reader.readAsText(err.response.data);
        } else {
          this.error = 'Failed to connect to the server or an unexpected error occurred.';
        }
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.duplicate-data-view {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  font-family: Arial, sans-serif;
}

h1 {
  color: #333;
  margin-bottom: 15px;
}

p {
  color: #555;
  margin-bottom: 25px;
}

button {
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s ease;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.message {
  margin-top: 20px;
  padding: 10px;
  border-radius: 5px;
  font-weight: bold;
}

.message.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
</style>