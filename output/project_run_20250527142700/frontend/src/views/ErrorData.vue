<template>
  <div class="error-data-view">
    <h1>Download Error Data</h1>
    <p>This section allows you to download a file containing details of data validation errors from ingestion processes.</p>

    <button @click="downloadErrorFile" :disabled="isLoading">
      <span v-if="isLoading">Downloading...</span>
      <span v-else>Download Error File (Excel)</span>
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
  name: 'ErrorData',
  data() {
    return {
      backendUrl: 'http://localhost:5000', // Adjust if your Flask backend runs on a different port/host
      isLoading: false,
      message: '',
      error: '',
    };
  },
  methods: {
    async downloadErrorFile() {
      this.isLoading = true;
      this.message = '';
      this.error = '';

      try {
        const response = await axios.get(`${this.backendUrl}/exports/data-errors`, {
          responseType: 'blob', // Important for downloading binary files like Excel
        });

        // Create a Blob from the response data with the correct MIME type for Excel
        const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

        // Create a temporary URL for the Blob
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = 'data_errors.xlsx'; // Suggested filename for the downloaded file

        // Append to the body and programmatically click the link to trigger download
        document.body.appendChild(link);
        link.click();

        // Clean up: remove the link and revoke the object URL
        document.body.removeChild(link);
        window.URL.revokeObjectURL(link.href);

        this.message = 'Error data file downloaded successfully!';
      } catch (err) {
        console.error('Error downloading data errors file:', err);
        if (err.response) {
          // If the server responded with an error, try to parse it as JSON
          // This is necessary because responseType: 'blob' will make err.response.data a Blob even for JSON errors
          try {
            const errorBlob = new Blob([err.response.data], { type: 'application/json' });
            const reader = new FileReader();
            reader.onload = () => {
              try {
                const errorData = JSON.parse(reader.result);
                this.error = errorData.message || `Server error: ${err.response.status} - Failed to download file.`;
              } catch (parseError) {
                this.error = `Failed to download error data file. Server responded with status ${err.response.status}.`;
              }
            };
            reader.readAsText(errorBlob);
          } catch (blobReadError) {
            this.error = 'Failed to download error data file. An unexpected error occurred.';
          }
        } else {
          this.error = 'Network error or server is unreachable. Please check your connection.';
        }
      } finally {
        this.isLoading = false;
      }
    },
  },
};
</script>

<style scoped>
.error-data-view {
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
  color: #333;
  margin-bottom: 15px;
  font-size: 2em;
}

p {
  color: #666;
  margin-bottom: 30px;
  line-height: 1.6;
}

button {
  background-color: #007bff;
  color: white;
  padding: 12px 25px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1.1em;
  transition: background-color 0.3s ease;
  min-width: 200px; /* Ensure button has a consistent width */
}

button:hover:not(:disabled) {
  background-color: #0056b3;
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
  font-size: 1em;
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