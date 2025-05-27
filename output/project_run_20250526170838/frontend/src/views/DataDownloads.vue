<template>
  <div class="data-downloads-container">
    <h1>Data Downloads</h1>

    <div class="download-section">
      <h2>Moengage Campaign File</h2>
      <p>Download the customer data formatted for Moengage campaigns (CSV).</p>
      <button @click="downloadMoengageFile" :disabled="loadingMoengage">
        <span v-if="loadingMoengage">Downloading...</span>
        <span v-else>Download Moengage File</span>
      </button>
      <p v-if="messageMoengage" :class="messageMoengage.type">{{ messageMoengage.text }}</p>
    </div>

    <div class="download-section">
      <h2>Duplicate Data File</h2>
      <p>Download a file containing records identified as duplicates (CSV).</p>
      <button @click="downloadDuplicateData" :disabled="loadingDuplicates">
        <span v-if="loadingDuplicates">Downloading...</span>
        <span v-else>Download Duplicate Data</span>
      </button>
      <p v-if="messageDuplicates" :class="messageDuplicates.type">{{ messageDuplicates.text }}</p>
    </div>

    <div class="download-section">
      <h2>Unique Data File</h2>
      <p>Download a file containing unique customer records after deduplication (CSV).</p>
      <button @click="downloadUniqueData" :disabled="loadingUnique">
        <span v-if="loadingUnique">Downloading...</span>
        <span v-else>Download Unique Data</span>
      </button>
      <p v-if="messageUnique" :class="messageUnique.type">{{ messageUnique.text }}</p>
    </div>

    <div class="download-section">
      <h2>Error Log File</h2>
      <p>Download an Excel file detailing errors from recent data ingestion processes (XLSX).</p>
      <button @click="downloadErrorFile" :disabled="loadingErrors">
        <span v-if="loadingErrors">Downloading...</span>
        <span v-else>Download Error Log</span>
      </button>
      <p v-if="messageErrors" :class="messageErrors.type">{{ messageErrors.text }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DataDownloads',
  data() {
    return {
      loadingMoengage: false,
      messageMoengage: null,
      loadingDuplicates: false,
      messageDuplicates: null,
      loadingUnique: false,
      messageUnique: null,
      loadingErrors: false,
      messageErrors: null,
      apiBaseUrl: process.env.VUE_APP_API_BASE_URL || '/api', // Fallback to /api if env var not set
    };
  },
  methods: {
    async downloadFile(url, defaultFilename, messageKey, fileType = 'csv') {
      this[messageKey] = null; // Clear previous messages
      this[`loading${messageKey.replace('message', '')}`] = true; // Set loading state

      try {
        const response = await axios.get(`${this.apiBaseUrl}${url}`, {
          responseType: 'blob', // Important for file downloads
        });

        const contentDisposition = response.headers['content-disposition'];
        let filename = defaultFilename;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1];
          }
        }

        const blob = new Blob([response.data], { type: response.headers['content-type'] });
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(link.href);

        this[messageKey] = { type: 'success', text: `Successfully downloaded ${filename}` };
      } catch (error) {
        console.error(`Error downloading ${defaultFilename}:`, error);
        let errorMessage = `Failed to download ${defaultFilename}. Please try again.`;
        if (error.response && error.response.data) {
          try {
            // Attempt to read error message from blob response
            const errorBlob = new Blob([error.response.data], { type: 'application/json' });
            const reader = new FileReader();
            reader.onload = () => {
              try {
                const errorJson = JSON.parse(reader.result);
                errorMessage = errorJson.message || errorMessage;
              } catch (parseError) {
                // If parsing fails, use generic message
              }
              this[messageKey] = { type: 'error', text: errorMessage };
            };
            reader.readAsText(errorBlob);
          } catch (e) {
            this[messageKey] = { type: 'error', text: errorMessage };
          }
        } else {
          this[messageKey] = { type: 'error', text: errorMessage };
        }
      } finally {
        this[`loading${messageKey.replace('message', '')}`] = false; // Reset loading state
      }
    },

    downloadMoengageFile() {
      this.downloadFile('/campaigns/moengage-export', 'moengage_campaign_data.csv', 'messageMoengage', 'csv');
    },
    downloadDuplicateData() {
      this.downloadFile('/data/duplicates', 'duplicate_customer_data.csv', 'messageDuplicates', 'csv');
    },
    downloadUniqueData() {
      this.downloadFile('/data/unique', 'unique_customer_data.csv', 'messageUnique', 'csv');
    },
    downloadErrorFile() {
      this.downloadFile('/data/errors', 'error_log.xlsx', 'messageErrors', 'xlsx');
    },
  },
};
</script>

<style scoped>
.data-downloads-container {
  max-width: 800px;
  margin: 40px auto;
  padding: 30px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h1 {
  color: #333;
  text-align: center;
  margin-bottom: 30px;
  font-size: 2.2em;
}

.download-section {
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 25px;
  margin-bottom: 25px;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
}

.download-section h2 {
  color: #0056b3;
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.6em;
}

.download-section p {
  color: #555;
  line-height: 1.6;
  margin-bottom: 20px;
}

button {
  background-color: #007bff;
  color: white;
  padding: 12px 25px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.3s ease, transform 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 180px;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
  transform: translateY(-1px);
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.success {
  color: #28a745;
  margin-top: 15px;
  font-weight: bold;
}

.error {
  color: #dc3545;
  margin-top: 15px;
  font-weight: bold;
}
</style>