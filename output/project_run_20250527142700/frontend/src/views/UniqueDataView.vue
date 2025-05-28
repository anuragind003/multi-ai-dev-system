<template>
  <div class="unique-data-view">
    <h1>Download Unique Customer Data</h1>
    <p>Click the button below to download the file containing unique customer profiles after deduplication.</p>

    <button @click="downloadUniqueData" :disabled="loading">
      <span v-if="loading">Downloading...</span>
      <span v-else>Download Unique Data File</span>
    </button>

    <div v-if="message" :class="['status-message', messageType]">
      {{ message }}
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'UniqueDataView',
  data() {
    return {
      loading: false,
      message: '',
      messageType: '' // 'success' or 'error'
    };
  },
  methods: {
    async downloadUniqueData() {
      this.loading = true;
      this.message = '';
      this.messageType = '';

      try {
        // Make a GET request to the backend API for unique customers
        const response = await axios({
          url: `${process.env.VUE_APP_API_BASE_URL}/exports/unique-customers`,
          method: 'GET',
          responseType: 'blob', // Important: responseType must be 'blob' for file downloads
        });

        // Create a Blob from the response data
        const blob = new Blob([response.data], { type: 'text/csv' });

        // Create a link element
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = `unique_customer_data_${new Date().toISOString().slice(0, 10)}.csv`; // Dynamic filename

        // Append to the document body and click it
        document.body.appendChild(link);
        link.click();

        // Clean up: remove the link and revoke the URL
        document.body.removeChild(link);
        window.URL.revokeObjectURL(link.href);

        this.message = 'Unique data file downloaded successfully!';
        this.messageType = 'success';

      } catch (error) {
        console.error('Error downloading unique data:', error);
        this.message = 'Failed to download unique data file. Please try again.';
        this.messageType = 'error';

        // Attempt to read error message from blob if available
        if (error.response && error.response.data instanceof Blob) {
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const errorData = JSON.parse(reader.result);
              this.message = errorData.message || this.message;
            } catch (e) {
              // Not a JSON error, use generic message
            }
          };
          reader.readAsText(error.response.data);
        }
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
.unique-data-view {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h1 {
  color: #333;
  margin-bottom: 20px;
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
  font-size: 16px;
  transition: background-color 0.3s ease;
}

button:hover:not(:disabled) {
  background-color: #45a049;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.status-message {
  margin-top: 20px;
  padding: 10px;
  border-radius: 5px;
  font-weight: bold;
}

.status-message.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-message.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
</style>