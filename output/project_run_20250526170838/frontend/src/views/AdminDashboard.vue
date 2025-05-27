<template>
  <div class="admin-dashboard">
    <h1>Admin Dashboard</h1>

    <section class="upload-section card">
      <h2>Upload Customer Data</h2>
      <p>Upload CSV files for various loan types to generate leads.</p>
      <div class="form-group">
        <label for="loanType">Select Loan Type:</label>
        <select id="loanType" v-model="selectedLoanType">
          <option value="">-- Please select --</option>
          <option value="Prospect">Prospect</option>
          <option value="TW Loyalty">TW Loyalty</option>
          <option value="Topup">Topup</option>
          <option value="Employee loans">Employee loans</option>
        </select>
      </div>
      <div class="form-group">
        <label for="fileUpload">Choose CSV File:</label>
        <input type="file" id="fileUpload" @change="handleFileUpload" accept=".csv" />
      </div>
      <button @click="uploadFile" :disabled="!selectedFile || !selectedLoanType || uploading">
        {{ uploading ? 'Uploading...' : 'Upload Data' }}
      </button>

      <div v-if="uploadMessage" :class="['message', uploadStatus]">
        {{ uploadMessage }}
      </div>
      <div v-if="uploadLogId" class="upload-log-id">
        Upload Log ID: <strong>{{ uploadLogId }}</strong>
      </div>
    </section>

    <section class="download-section card">
      <h2>Download Reports & Data Files</h2>
      <p>Access various system-generated reports and data exports.</p>
      <div class="download-buttons">
        <button @click="downloadFile('/campaigns/moengage-export', 'moengage_campaign_data.csv')">
          Download Moengage Format File (CSV)
        </button>
        <button @click="downloadFile('/data/duplicates', 'duplicate_customer_data.csv')">
          Download Duplicate Data File (CSV)
        </button>
        <button @click="downloadFile('/data/unique', 'unique_customer_data.csv')">
          Download Unique Data File (CSV)
        </button>
        <button @click="downloadFile('/data/errors', 'error_log.xlsx')">
          Download Error File (Excel)
        </button>
      </div>
      <div v-if="downloadMessage" :class="['message', downloadStatus]">
        {{ downloadMessage }}
      </div>
    </section>

    <section class="reports-section card">
      <h2>Reports & Views</h2>
      <p>Navigate to detailed reports and customer views.</p>
      <div class="report-links">
        <!-- These routes would need to be defined in your Vue Router configuration -->
        <router-link to="/daily-reports" class="button">View Daily Data Tally Reports</router-link>
        <router-link to="/customer-view" class="button">View Customer Level Details</router-link>
      </div>
    </section>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'AdminDashboard',
  data() {
    return {
      selectedFile: null,
      selectedLoanType: '',
      uploading: false,
      uploadMessage: '',
      uploadStatus: '', // 'success' or 'error'
      uploadLogId: null,
      downloadMessage: '',
      downloadStatus: '', // 'success' or 'error'
    };
  },
  methods: {
    handleFileUpload(event) {
      this.selectedFile = event.target.files[0];
      this.uploadMessage = ''; // Clear previous messages
      this.uploadStatus = '';
      this.uploadLogId = null;
    },
    async uploadFile() {
      if (!this.selectedFile || !this.selectedLoanType) {
        this.uploadMessage = 'Please select a file and a loan type.';
        this.uploadStatus = 'error';
        return;
      }

      this.uploading = true;
      this.uploadMessage = 'Uploading...';
      this.uploadStatus = '';
      this.uploadLogId = null;

      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64Content = e.target.result.split(',')[1]; // Get base64 part
        const payload = {
          file_content: base64Content,
          file_name: this.selectedFile.name,
          loan_type: this.selectedLoanType,
        };

        try {
          const response = await axios.post('/admin/customer-data/upload', payload, {
            headers: {
              'Content-Type': 'application/json',
            },
          });
          this.uploadMessage = `Upload successful! Processed ${response.data.success_count} records, ${response.data.error_count} errors.`;
          this.uploadStatus = 'success';
          this.uploadLogId = response.data.log_id;
          // Optionally clear the file input
          this.selectedFile = null;
          document.getElementById('fileUpload').value = '';
        } catch (error) {
          console.error('Error uploading file:', error);
          this.uploadMessage = `Upload failed: ${error.response?.data?.message || error.message}`;
          this.uploadStatus = 'error';
          this.uploadLogId = null;
        } finally {
          this.uploading = false;
        }
      };
      reader.readAsDataURL(this.selectedFile);
    },
    async downloadFile(endpoint, filename) {
      this.downloadMessage = `Downloading ${filename}...`;
      this.downloadStatus = '';
      try {
        const response = await axios.get(endpoint, {
          responseType: 'blob', // Important for file downloads
        });

        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        this.downloadMessage = `${filename} downloaded successfully!`;
        this.downloadStatus = 'success';
      } catch (error) {
        console.error(`Error downloading ${filename}:`, error);
        this.downloadMessage = `Failed to download ${filename}: ${error.response?.data?.message || error.message}`;
        this.downloadStatus = 'error';
      }
    },
  },
};
</script>

<style scoped>
.admin-dashboard {
  padding: 20px;
  max-width: 900px;
  margin: 20px auto;
  font-family: Arial, sans-serif;
  background-color: #f4f7f6;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  color: #2c3e50;
  text-align: center;
  margin-bottom: 30px;
}

h2 {
  color: #34495e;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 20px;
}

.card {
  background-color: #ffffff;
  border-radius: 8px;
  padding: 25px;
  margin-bottom: 30px;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.08);
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #555;
}

.form-group input[type="file"],
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box; /* Include padding and border in the element's total width and height */
}

button {
  background-color: #42b983;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s ease;
  margin-right: 10px;
  margin-bottom: 10px;
}

button:hover:not(:disabled) {
  background-color: #369f75;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
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

.upload-log-id {
  margin-top: 10px;
  font-size: 0.9em;
  color: #666;
}

.download-buttons button {
  display: block; /* Make buttons stack vertically */
  width: 100%; /* Full width */
  margin-bottom: 10px; /* Space between buttons */
}

.download-buttons button:last-child {
  margin-bottom: 0;
}

.report-links .button {
  display: inline-block;
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  text-decoration: none;
  margin-right: 10px;
  margin-bottom: 10px;
  transition: background-color 0.3s ease;
}

.report-links .button:hover {
  background-color: #0056b3;
}
</style>