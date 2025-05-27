<template>
  <div class="admin-dashboard">
    <h1>Admin Dashboard</h1>

    <section class="upload-section card">
      <h2>Upload Customer Data</h2>
      <p>Upload CSV files for various loan types to generate leads in the system.</p>
      <div class="form-group">
        <label for="loanType">Select Loan Type:</label>
        <select id="loanType" v-model="selectedLoanType">
          <option value="">--Please choose a loan type--</option>
          <option value="Prospect">Prospect</option>
          <option value="TW Loyalty">TW Loyalty</option>
          <option value="Topup">Topup</option>
          <option value="Employee loans">Employee loans</option>
        </select>
      </div>
      <div class="form-group">
        <label for="customerFile">Choose CSV File:</label>
        <input type="file" id="customerFile" @change="handleFileUpload" accept=".csv" />
      </div>
      <button @click="uploadCustomerData" :disabled="!selectedFile || !selectedLoanType || uploading">
        {{ uploading ? 'Uploading...' : 'Upload Data' }}
      </button>
      <div v-if="uploadMessage" :class="['message', uploadStatus]">
        {{ uploadMessage }}
      </div>
    </section>

    <section class="download-section card">
      <h2>Download Reports & Files</h2>
      <p>Download various system-generated files for analysis and campaigns.</p>
      <div class="download-buttons">
        <button @click="downloadFile('/campaigns/moengage-export', 'moengage_campaign_data.csv', 'csv')" :disabled="downloading.moengage">
          {{ downloading.moengage ? 'Generating...' : 'Download Moengage File' }}
        </button>
        <button @click="downloadFile('/data/duplicates', 'duplicate_customer_data.csv', 'csv')" :disabled="downloading.duplicates">
          {{ downloading.duplicates ? 'Generating...' : 'Download Duplicate Data' }}
        </button>
        <button @click="downloadFile('/data/unique', 'unique_customer_data.csv', 'csv')" :disabled="downloading.unique">
          {{ downloading.unique ? 'Generating...' : 'Download Unique Data' }}
        </button>
        <button @click="downloadFile('/data/errors', 'error_log.xlsx', 'xlsx')" :disabled="downloading.errors">
          {{ downloading.errors ? 'Generating...' : 'Download Error File' }}
        </button>
      </div>
      <div v-if="downloadMessage" :class="['message', downloadStatus]">
        {{ downloadMessage }}
      </div>
    </section>

    <section class="reporting-section card">
      <h2>Reporting & Views</h2>
      <p>Access various reports and customer views.</p>
      <div class="report-links">
        <!-- These links would navigate to other Vue components for detailed reports -->
        <router-link to="/admin/daily-reports" class="button-link">View Daily Data Tally Reports</router-link>
        <router-link to="/admin/customer-view" class="button-link">View Customer Level Journey</router-link>
      </div>
    </section>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'AdminDashboardView',
  data() {
    return {
      selectedFile: null,
      selectedLoanType: '',
      uploading: false,
      uploadMessage: '',
      uploadStatus: '', // 'success' or 'error'
      downloading: {
        moengage: false,
        duplicates: false,
        unique: false,
        errors: false,
      },
      downloadMessage: '',
      downloadStatus: '', // 'success' or 'error'
      backendUrl: 'http://localhost:5000', // Base URL for your Flask backend
    };
  },
  methods: {
    handleFileUpload(event) {
      this.selectedFile = event.target.files[0];
      this.uploadMessage = ''; // Clear previous messages
      this.uploadStatus = '';
    },
    async uploadCustomerData() {
      if (!this.selectedFile || !this.selectedLoanType) {
        this.uploadMessage = 'Please select a file and a loan type.';
        this.uploadStatus = 'error';
        return;
      }

      this.uploading = true;
      this.uploadMessage = 'Uploading... Please wait.';
      this.uploadStatus = '';

      const reader = new FileReader();
      reader.onload = async (e) => {
        // The result is a Data URL (e.g., "data:text/csv;base64,...")
        // We need to extract only the base64 part
        const fileContent = e.target.result.split(',')[1];
        const fileName = this.selectedFile.name;

        try {
          const response = await axios.post(`${this.backendUrl}/admin/customer-data/upload`, {
            file_content: fileContent,
            file_name: fileName,
            loan_type: this.selectedLoanType,
          });

          if (response.data.status === 'success') {
            this.uploadMessage = `Upload successful! Log ID: ${response.data.log_id}, Success: ${response.data.success_count}, Errors: ${response.data.error_count}.`;
            this.uploadStatus = 'success';
          } else {
            // This path might be hit if backend returns 'status: error' but with 200 OK
            this.uploadMessage = `Upload failed: ${response.data.message || 'Unknown error.'}`;
            this.uploadStatus = 'error';
          }
        } catch (error) {
          console.error('Error uploading file:', error);
          this.uploadMessage = `Upload failed: ${error.response?.data?.message || error.message}.`;
          this.uploadStatus = 'error';
        } finally {
          this.uploading = false;
          // Clear file input after upload attempt
          document.getElementById('customerFile').value = '';
          this.selectedFile = null;
        }
      };
      reader.onerror = (error) => {
        this.uploading = false;
        this.uploadMessage = `Error reading file: ${error.message}`;
        this.uploadStatus = 'error';
      };
      reader.readAsDataURL(this.selectedFile); // Read file as Data URL (base64)
    },

    async downloadFile(endpoint, filename, fileType) {
      let downloadKey = '';
      if (endpoint.includes('moengage')) downloadKey = 'moengage';
      else if (endpoint.includes('duplicates')) downloadKey = 'duplicates';
      else if (endpoint.includes('unique')) downloadKey = 'unique';
      else if (endpoint.includes('errors')) downloadKey = 'errors';

      this.downloading[downloadKey] = true;
      this.downloadMessage = `Generating ${filename}...`;
      this.downloadStatus = '';

      try {
        const response = await axios.get(`${this.backendUrl}${endpoint}`, {
          responseType: 'blob', // Important for file downloads
        });

        // Create a Blob from the response data
        const blob = new Blob([response.data], { type: response.headers['content-type'] });
        const url = window.URL.createObjectURL(blob);

        // Create a temporary link element and trigger the download
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url); // Clean up the URL object

        this.downloadMessage = `${filename} downloaded successfully!`;
        this.downloadStatus = 'success';
      } catch (error) {
        console.error(`Error downloading ${filename}:`, error);
        this.downloadMessage = `Failed to download ${filename}: ${error.response?.data?.message || error.message}.`;
        this.downloadStatus = 'error';
      } finally {
        this.downloading[downloadKey] = false;
      }
    },
  },
};
</script>

<style scoped>
.admin-dashboard {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
  font-family: Arial, sans-serif;
}

h1 {
  color: #333;
  text-align: center;
  margin-bottom: 30px;
}

.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 25px;
  margin-bottom: 30px;
}

.card h2 {
  color: #0056b3;
  margin-top: 0;
  margin-bottom: 15px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.card p {
  color: #555;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #333;
}

.form-group input[type="file"],
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box; /* Ensures padding doesn't increase width */
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
  margin-right: 10px; /* For multiple buttons */
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.download-buttons button {
  margin-bottom: 10px;
}

.message {
  margin-top: 20px;
  padding: 10px;
  border-radius: 4px;
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

.report-links {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}

.button-link {
  display: inline-block;
  background-color: #6c757d;
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  text-decoration: none;
  font-size: 16px;
  transition: background-color 0.3s ease;
}

.button-link:hover {
  background-color: #5a6268;
}
</style>