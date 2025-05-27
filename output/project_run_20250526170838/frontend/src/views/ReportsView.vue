<template>
  <div class="reports-view">
    <h1>Reports & Data Downloads</h1>

    <p>Select a report type to download the corresponding data file.</p>

    <div class="report-actions">
      <button @click="downloadMoengageFile" :disabled="loading.moengage">
        <span v-if="loading.moengage">Downloading...</span>
        <span v-else>Download Moengage Format File (CSV)</span>
      </button>
      <p v-if="message.moengage" :class="message.moengage.type">{{ message.moengage.text }}</p>

      <button @click="downloadDuplicateDataFile" :disabled="loading.duplicates">
        <span v-if="loading.duplicates">Downloading...</span>
        <span v-else>Download Duplicate Data File (CSV)</span>
      </button>
      <p v-if="message.duplicates" :class="message.duplicates.type">{{ message.duplicates.text }}</p>

      <button @click="downloadUniqueDataFile" :disabled="loading.unique">
        <span v-if="loading.unique">Downloading...</span>
        <span v-else>Download Unique Data File (CSV)</span>
      </button>
      <p v-if="message.unique" :class="message.unique.type">{{ message.unique.text }}</p>

      <button @click="downloadErrorFile" :disabled="loading.errors">
        <span v-if="loading.errors">Downloading...</span>
        <span v-else>Download Error File (Excel)</span>
      </button>
      <p v-if="message.errors" :class="message.errors.type">{{ message.errors.text }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ReportsView',
  data() {
    return {
      loading: {
        moengage: false,
        duplicates: false,
        unique: false,
        errors: false,
      },
      message: {
        moengage: null,
        duplicates: null,
        unique: null,
        errors: null,
      },
      // Use environment variable for API base URL, fallback for development
      apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
    };
  },
  methods: {
    /**
     * Generic method to handle file downloads from the backend.
     * @param {string} endpoint - The API endpoint to call (e.g., '/campaigns/moengage-export').
     * @param {string} fileName - The base name for the downloaded file (e.g., 'moengage_report').
     * @param {string} loadingKey - The key in the `loading` data object to manage loading state.
     * @param {string} messageKey - The key in the `message` data object to display feedback.
     * @param {string} fileExtension - The file extension (e.g., 'csv', 'xlsx').
     */
    async downloadFile(endpoint, fileName, loadingKey, messageKey, fileExtension) {
      this.loading[loadingKey] = true;
      this.message[messageKey] = null; // Clear previous message

      try {
        const response = await axios.get(`${this.apiBaseUrl}${endpoint}`, {
          responseType: 'blob', // Crucial for downloading binary data like files
        });

        // Create a Blob from the response data
        const blob = new Blob([response.data], { type: response.headers['content-type'] });
        const url = window.URL.createObjectURL(blob);

        // Create a temporary link element to trigger the download
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${fileName}.${fileExtension}`); // Set the download file name
        document.body.appendChild(link);
        link.click(); // Programmatically click the link to start download

        // Clean up the temporary link and URL object
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        this.message[messageKey] = { type: 'success', text: `${fileName} downloaded successfully!` };
      } catch (error) {
        console.error(`Error downloading ${fileName}:`, error);
        let errorMessage = `Failed to download ${fileName}. Please try again.`;

        // Attempt to parse error message from blob if the response was an error JSON
        if (error.response && error.response.data instanceof Blob) {
          const reader = new FileReader();
          reader.onload = async (e) => {
            try {
              const errorJson = JSON.parse(e.target.result);
              errorMessage = errorJson.message || errorMessage;
            } catch (parseError) {
              // If parsing fails, stick to generic message
              console.error("Could not parse error response as JSON:", parseError);
            } finally {
              this.message[messageKey] = { type: 'error', text: errorMessage };
            }
          };
          reader.readAsText(error.response.data);
        } else if (error.response && error.response.data && typeof error.response.data === 'object') {
          // For non-blob errors (e.g., network errors, or if backend sends JSON directly)
          errorMessage = error.response.data.message || errorMessage;
          this.message[messageKey] = { type: 'error', text: errorMessage };
        } else {
          this.message[messageKey] = { type: 'error', text: errorMessage };
        }
      } finally {
        this.loading[loadingKey] = false;
        // Clear the message after a few seconds for better UX
        setTimeout(() => {
          this.message[messageKey] = null;
        }, 5000);
      }
    },

    downloadMoengageFile() {
      this.downloadFile('/campaigns/moengage-export', 'moengage_format_file', 'moengage', 'moengage', 'csv');
    },
    downloadDuplicateDataFile() {
      this.downloadFile('/data/duplicates', 'duplicate_customer_data', 'duplicates', 'duplicates', 'csv');
    },
    downloadUniqueDataFile() {
      this.downloadFile('/data/unique', 'unique_customer_data', 'unique', 'unique', 'csv');
    },
    downloadErrorFile() {
      // Assuming the error file is an Excel file, typically .xlsx
      this.downloadFile('/data/errors', 'error_log', 'errors', 'errors', 'xlsx');
    },
  },
};
</script>

<style scoped>
.reports-view {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

h1 {
  color: #2c3e50;
  text-align: center;
  margin-bottom: 30px;
  font-size: 2.2em;
  font-weight: 600;
}

p {
  text-align: center;
  color: #555;
  margin-bottom: 25px;
  font-size: 1.1em;
}

.report-actions {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

button {
  background-color: #007bff;
  color: white;
  padding: 14px 25px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1.1em;
  font-weight: 500;
  transition: background-color 0.3s ease, transform 0.2s ease;
  width: 100%;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
  transform: translateY(-2px);
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
  box-shadow: none;
}

.message {
  margin-top: 5px;
  padding: 10px 15px;
  border-radius: 5px;
  font-size: 0.95em;
  text-align: center;
  font-weight: 500;
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