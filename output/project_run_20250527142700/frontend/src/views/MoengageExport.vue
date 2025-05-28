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
  name: 'MoengageExport',
  data() {
    return {
      loading: false,
      successMessage: '',
      error: '',
    };
  },
  methods: {
    async downloadMoengageFile() {
      this.loading = true;
      this.successMessage = '';
      this.error = '';

      try {
        // Make a GET request to the backend API endpoint
        // The responseType 'blob' is crucial for downloading files
        const response = await axios.get('/exports/moengage-campaign-file', {
          responseType: 'blob', // Important for file downloads
        });

        // Check if the response indicates an error (e.g., no data found)
        // If the backend sends JSON for errors, we need to handle it.
        // Axios with responseType: 'blob' will still give a blob for JSON,
        // so we check content type.
        if (response.headers['content-type'] && response.headers['content-type'].includes('application/json')) {
          // If it's JSON, it's likely an error message from the backend
          const reader = new FileReader();
          reader.onload = () => {
            const errorData = JSON.parse(reader.result);
            this.error = errorData.message || 'An unexpected error occurred while generating the file.';
          };
          reader.readAsText(response.data);
        } else {
          // Create a Blob from the response data
          const blob = new Blob([response.data], { type: 'text/csv' });

          // Create a temporary URL for the blob
          const url = window.URL.createObjectURL(blob);

          // Create a temporary anchor tag
          const link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', 'moengage_campaign_export.csv'); // Set the desired filename

          // Append to body, click, and remove
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);

          // Revoke the object URL to free up memory
          window.URL.revokeObjectURL(url);

          this.successMessage = 'Moengage campaign file downloaded successfully!';
        }
      } catch (err) {
        console.error('Error downloading Moengage file:', err);
        if (err.response) {
          // If the server responded with a status code outside the 2xx range
          // and it's not a blob, try to parse it as JSON for error messages
          if (err.response.data instanceof Blob && err.response.headers['content-type'].includes('application/json')) {
            const reader = new FileReader();
            reader.onload = () => {
              try {
                const errorData = JSON.parse(reader.result);
                this.error = errorData.message || `Server error: ${err.response.status}`;
              } catch (e) {
                this.error = `Failed to parse error response. Status: ${err.response.status}`;
              }
            };
            reader.readAsText(err.response.data);
          } else {
            this.error = err.response.data.message || `Server error: ${err.response.status}`;
          }
        } else if (err.request) {
          // The request was made but no response was received
          this.error = 'No response from server. Please check your network connection.';
        } else {
          // Something happened in setting up the request that triggered an Error
          this.error = 'An unexpected error occurred: ' + err.message;
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
  max-width: 800px;
  margin: 50px auto;
  padding: 30px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  background-color: #fff;
  text-align: center;
}

h1 {
  color: #333;
  margin-bottom: 20px;
  font-size: 2em;
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
  font-size: 1.1em;
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
  padding: 10px 15px;
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