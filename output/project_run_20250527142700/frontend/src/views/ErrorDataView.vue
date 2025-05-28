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
  name: 'ErrorDataView',
  data() {
    return {
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
        // Make a GET request to the backend API endpoint for error data
        const response = await axios.get('/api/exports/data-errors', {
          responseType: 'blob', // Important: responseType must be 'blob' for file downloads
        });

        // Create a blob from the response data
        const blob = new Blob([response.data], { type: response.headers['content-type'] });

        // Create a link element
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);

        // Get filename from Content-Disposition header if available, otherwise use a default
        const contentDisposition = response.headers['content-disposition'];
        let filename = 'error_data.xlsx'; // Default filename
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1];
          }
        }

        link.setAttribute('download', filename); // Set the download attribute with the filename
        document.body.appendChild(link); // Append to the document body
        link.click(); // Programmatically click the link to trigger the download
        document.body.removeChild(link); // Clean up: remove the link element
        window.URL.revokeObjectURL(link.href); // Clean up: revoke the object URL

        this.message = `"${filename}" download initiated successfully.`;
      } catch (err) {
        console.error('Error downloading error file:', err);
        this.error = 'Failed to download error file. Please try again.';
        if (err.response && err.response.data) {
          // Attempt to read error message from blob if it's an API error
          try {
            const errorBlob = new Blob([err.response.data], { type: 'application/json' });
            const reader = new FileReader();
            reader.onload = () => {
              try {
                const errorData = JSON.parse(reader.result);
                this.error = errorData.message || this.error;
              } catch (parseError) {
                console.error('Failed to parse error response:', parseError);
              }
            };
            reader.readAsText(errorBlob);
          } catch (blobError) {
            console.error('Error processing error blob:', blobError);
          }
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
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h1 {
  color: #333;
  text-align: center;
  margin-bottom: 20px;
}

p {
  color: #555;
  text-align: center;
  margin-bottom: 30px;
}

button {
  display: block;
  width: fit-content;
  margin: 0 auto;
  padding: 12px 25px;
  font-size: 16px;
  color: #fff;
  background-color: #007bff;
  border: none;
  border-radius: 5px;
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
  text-align: center;
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