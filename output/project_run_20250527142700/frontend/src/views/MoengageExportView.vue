<template>
  <div class="moengage-export-view">
    <h1>Moengage Campaign File Export</h1>
    <p>
      Click the button below to generate and download the Moengage-formatted CSV file
      containing eligible customer data for your campaigns. DND (Do Not Disturb) customers
      will be automatically excluded from this export.
    </p>

    <button @click="downloadMoengageFile" :disabled="loading">
      <span v-if="loading">Generating file...</span>
      <span v-else>Download Moengage Export</span>
    </button>

    <div v-if="successMessage" class="message success">
      {{ successMessage }}
    </div>

    <div v-if="error" class="message error">
      Error: {{ error }}
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'MoengageExportView',
  data() {
    return {
      loading: false,
      error: null,
      successMessage: null,
    };
  },
  methods: {
    async downloadMoengageFile() {
      this.loading = true;
      this.error = null;
      this.successMessage = null;

      try {
        // Make a GET request to the backend API endpoint
        // The backend is expected to return a CSV file as a blob
        const response = await axios.get('/api/exports/moengage-campaign-file', {
          responseType: 'blob', // Important: specify responseType as 'blob' for file downloads
        });

        // Create a blob from the response data
        const blob = new Blob([response.data], { type: 'text/csv' });

        // Create a temporary URL for the blob
        const url = window.URL.createObjectURL(blob);

        // Create a temporary anchor element
        const link = document.createElement('a');
        link.href = url;

        // Set the download attribute with a desired filename
        const date = new Date();
        const filename = `moengage_campaign_export_${date.getFullYear()}${(date.getMonth() + 1).toString().padStart(2, '0')}${date.getDate().toString().padStart(2, '0')}_${date.getHours().toString().padStart(2, '0')}${date.getMinutes().toString().padStart(2, '0')}${date.getSeconds().toString().padStart(2, '0')}.csv`;
        link.setAttribute('download', filename);

        // Append the link to the body, click it, and then remove it
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Revoke the object URL to free up memory
        window.URL.revokeObjectURL(url);

        this.successMessage = `File "${filename}" downloaded successfully!`;

      } catch (err) {
        console.error('Error downloading Moengage file:', err);
        if (err.response && err.response.data) {
          // Try to parse error message from blob if available
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const errorData = JSON.parse(reader.result);
              this.error = errorData.message || 'An unknown error occurred during download.';
            } catch (e) {
              this.error = 'Failed to download file. Please try again later.';
            }
          };
          reader.readAsText(err.response.data);
        } else {
          this.error = 'Network error or server is unreachable. Please try again.';
        }
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.moengage-export-view {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  font-family: Arial, sans-serif;
  text-align: center;
}

h1 {
  color: #333;
  margin-bottom: 20px;
}

p {
  color: #555;
  line-height: 1.6;
  margin-bottom: 30px;
}

button {
  background-color: #007bff;
  color: white;
  padding: 12px 25px;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
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