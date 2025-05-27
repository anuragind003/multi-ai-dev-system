<template>
  <div class="file-upload-input">
    <h2>Upload Customer Data</h2>
    <p>Please select a file (CSV) and the corresponding loan type to upload customer details.</p>

    <div class="form-group">
      <label for="file-input">Select File:</label>
      <input
        type="file"
        id="file-input"
        ref="fileInput"
        @change="handleFileChange"
        accept=".csv"
        class="file-input"
      />
      <span v-if="selectedFile">{{ selectedFile.name }}</span>
      <span v-else class="no-file-selected">No file selected</span>
    </div>

    <div class="form-group">
      <label for="loan-type-select">Loan Type:</label>
      <select id="loan-type-select" v-model="loanType" class="loan-type-select">
        <option value="" disabled>Select a loan type</option>
        <option v-for="type in loanTypeOptions" :key="type" :value="type">
          {{ type }}
        </option>
      </select>
    </div>

    <button @click="uploadFile" :disabled="!selectedFile || !loanType || uploading" class="upload-button">
      <span v-if="uploading">Uploading...</span>
      <span v-else>Upload Data</span>
    </button>

    <div v-if="uploading" class="upload-status">
      <div class="spinner"></div>
      <p>Processing your file...</p>
    </div>

    <div v-if="uploadSuccess" class="alert success">
      <p><strong>Upload Successful!</strong></p>
      <p>Log ID: {{ logId }}</p>
      <p>Records Processed: {{ successCount + errorCount }}</p>
      <p>Successful Records: {{ successCount }}</p>
      <p>Error Records: {{ errorCount }}</p>
      <p v-if="errorCount > 0">Please check the <router-link to="/data/errors">Error Data Download</router-link> section for details.</p>
    </div>

    <div v-if="uploadError" class="alert error">
      <p><strong>Upload Failed:</strong></p>
      <p>{{ uploadError }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'FileUploadInput',
  data() {
    return {
      selectedFile: null,
      loanType: '',
      loanTypeOptions: ['Prospect', 'TW Loyalty', 'Topup', 'Employee loans'],
      uploading: false,
      uploadSuccess: false,
      uploadError: '',
      logId: null,
      successCount: 0,
      errorCount: 0,
    };
  },
  methods: {
    handleFileChange(event) {
      this.selectedFile = event.target.files[0];
      // Reset messages on new file selection
      this.uploadSuccess = false;
      this.uploadError = '';
      this.logId = null;
      this.successCount = 0;
      this.errorCount = 0;
    },
    async uploadFile() {
      if (!this.selectedFile) {
        this.uploadError = 'Please select a file to upload.';
        return;
      }
      if (!this.loanType) {
        this.uploadError = 'Please select a loan type.';
        return;
      }

      this.uploading = true;
      this.uploadSuccess = false;
      this.uploadError = '';

      const formData = new FormData();
      formData.append('file', this.selectedFile);
      formData.append('loan_type', this.loanType);

      try {
        const response = await axios.post('/admin/customer-data/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        if (response.data.status === 'success') {
          this.uploadSuccess = true;
          this.logId = response.data.log_id;
          this.successCount = response.data.success_count;
          this.errorCount = response.data.error_count;
          // Optionally clear the file input after successful upload
          this.$refs.fileInput.value = '';
          this.selectedFile = null;
          this.loanType = ''; // Reset loan type as well
        } else {
          // This case might be for a 'partial success' or specific backend logic
          // For now, assuming 'status: success' means overall success.
          // If backend sends 'status: failed' with details, it would fall into catch block.
          this.uploadError = response.data.message || 'An unknown error occurred during upload.';
        }
      } catch (error) {
        console.error('File upload failed:', error);
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          this.uploadError = error.response.data.message || `Server Error: ${error.response.status}`;
        } else if (error.request) {
          // The request was made but no response was received
          this.uploadError = 'No response from server. Please check your network connection.';
        } else {
          // Something happened in setting up the request that triggered an Error
          this.uploadError = error.message || 'An unexpected error occurred.';
        }
      } finally {
        this.uploading = false;
      }
    },
  },
};
</script>

<style scoped>
.file-upload-input {
  max-width: 600px;
  margin: 40px auto;
  padding: 30px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  background-color: #ffffff;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #333;
}

h2 {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 25px;
  font-size: 1.8em;
}

p {
  text-align: center;
  margin-bottom: 20px;
  color: #555;
  line-height: 1.6;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #444;
}

.file-input {
  display: block;
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  box-sizing: border-box; /* Ensures padding doesn't increase width */
  background-color: #f9f9f9;
  cursor: pointer;
}

.file-input::-webkit-file-upload-button {
  visibility: hidden;
}
.file-input::before {
  content: 'Choose File';
  display: inline-block;
  background: #007bff;
  color: white;
  border: 1px solid #007bff;
  border-radius: 4px;
  padding: 8px 12px;
  outline: none;
  white-space: nowrap;
  -webkit-user-select: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 10pt;
  margin-right: 10px;
}
.file-input:hover::before {
  background: #0056b3;
  border-color: #0056b3;
}
.file-input:active::before {
  background: #004085;
  border-color: #004085;
}

.no-file-selected {
  font-style: italic;
  color: #888;
  margin-left: 10px;
}

.loan-type-select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  background-color: #f9f9f9;
  font-size: 1em;
  appearance: none; /* Remove default arrow */
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23007bff%22%20d%3D%22M287%2C197.9L159.3%2C69.2c-3.7-3.7-9.8-3.7-13.5%2C0L5.4%2C197.9c-3.7%2C3.7-3.7%2C9.8%2C0%2C13.5l13.5%2C13.5c3.7%2C3.7%2C9.8%2C3.7%2C13.5%2C0l110.7-110.7l110.7%2C110.7c3.7%2C3.7%2C9.8%2C3.7%2C13.5%2C0l13.5-13.5C290.7%2C207.7%2C290.7%2C201.6%2C287%2C197.9z%22%2F%3E%3C%2Fsvg%3E');
  background-repeat: no-repeat;
  background-position: right 10px top 50%;
  background-size: 12px auto;
}

.upload-button {
  display: block;
  width: 100%;
  padding: 12px 20px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 1.1em;
  cursor: pointer;
  transition: background-color 0.3s ease;
  margin-top: 25px;
}

.upload-button:hover:not(:disabled) {
  background-color: #218838;
}

.upload-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.upload-status {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 20px;
  color: #007bff;
  font-weight: bold;
}

.spinner {
  border: 4px solid rgba(0, 123, 255, 0.1);
  border-top: 4px solid #007bff;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
  margin-right: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.alert {
  padding: 15px;
  border-radius: 5px;
  margin-top: 20px;
  font-size: 0.95em;
  line-height: 1.5;
}

.alert.success {
  background-color: #d4edda;
  color: #155724;
  border-color: #c3e6cb;
}

.alert.error {
  background-color: #f8d7da;
  color: #721c24;
  border-color: #f5c6cb;
}

.alert p {
  text-align: left;
  margin-bottom: 5px;
}

.alert p:last-child {
  margin-bottom: 0;
}

.alert a {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
}

.alert a:hover {
  text-decoration: underline;
}
</style>