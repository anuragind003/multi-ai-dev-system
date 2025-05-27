<template>
  <div class="file-upload-card">
    <h2>Upload Customer Data</h2>
    <p>Upload customer details for Prospect, TW Loyalty, Topup, and Employee loans.</p>

    <div class="form-group">
      <label for="loanType">Select Loan Type:</label>
      <select id="loanType" v-model="selectedLoanType">
        <option value="" disabled>Please select a loan type</option>
        <option v-for="type in loanTypes" :key="type" :value="type">{{ type }}</option>
      </select>
    </div>

    <div class="form-group">
      <label for="fileInput">Choose CSV File:</label>
      <input type="file" id="fileInput" @change="handleFileChange" accept=".csv" />
    </div>

    <button @click="uploadFile" :disabled="!selectedFile || !selectedLoanType || uploading">
      {{ uploading ? 'Uploading...' : 'Upload' }}
    </button>

    <div v-if="uploading" class="status-message loading">
      <p>Processing file...</p>
    </div>

    <div v-if="uploadStatus === 'success'" class="status-message success">
      <p>File uploaded successfully!</p>
      <p>Log ID: {{ uploadResult.log_id }}</p>
      <p>Records Processed: {{ uploadResult.success_count }}</p>
      <p>Errors: {{ uploadResult.error_count }}</p>
      <button v-if="uploadResult.error_count > 0 && uploadResult.log_id" @click="downloadErrorFile" class="download-button">
        Download Error File
      </button>
    </div>

    <div v-if="uploadStatus === 'error'" class="status-message error">
      <p>Upload failed: {{ errorMessage }}</p>
      <p v-if="uploadResult.error_count > 0">Please download the error file for details.</p>
      <button v-if="uploadResult.log_id" @click="downloadErrorFile" class="download-button">
        Download Error File
      </button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'; // Assuming axios is installed and configured in your project

export default {
  name: 'FileUploadCard',
  data() {
    return {
      selectedFile: null,
      selectedLoanType: '',
      loanTypes: ['Prospect', 'TW Loyalty', 'Topup', 'Employee loans'],
      uploading: false,
      uploadStatus: null, // 'success', 'error', null
      errorMessage: '',
      uploadResult: {
        log_id: null,
        success_count: 0,
        error_count: 0,
      },
    };
  },
  methods: {
    handleFileChange(event) {
      this.selectedFile = event.target.files[0];
      // Reset status messages and results on new file selection
      this.uploadStatus = null;
      this.errorMessage = '';
      this.uploadResult = { log_id: null, success_count: 0, error_count: 0 };
    },
    async uploadFile() {
      if (!this.selectedFile || !this.selectedLoanType) {
        this.errorMessage = 'Please select a file and a loan type.';
        this.uploadStatus = 'error';
        return;
      }

      this.uploading = true;
      this.uploadStatus = null; // Clear previous status
      this.errorMessage = ''; // Clear previous error message

      const formData = new FormData();
      // The backend Flask endpoint expects 'file' for the actual file content,
      // 'file_name' and 'loan_type' as additional form fields.
      formData.append('file', this.selectedFile);
      formData.append('file_name', this.selectedFile.name);
      formData.append('loan_type', this.selectedLoanType);

      try {
        const response = await axios.post('/admin/customer-data/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data', // Important for file uploads
          },
        });

        // Assuming backend response structure as per system design
        if (response.data.status === 'success') {
          this.uploadStatus = 'success';
          this.uploadResult = {
            log_id: response.data.log_id,
            success_count: response.data.success_count,
            error_count: response.data.error_count,
          };
        } else {
          // Handle cases where backend returns a non-2xx status or 'status: "failed"'
          this.uploadStatus = 'error';
          this.errorMessage = response.data.message || 'Unknown error occurred during upload.';
          this.uploadResult = {
            log_id: response.data.log_id || null,
            success_count: response.data.success_count || 0,
            error_count: response.data.error_count || 0,
          };
        }
      } catch (error) {
        this.uploadStatus = 'error';
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx (e.g., 400, 500)
          this.errorMessage = error.response.data.message || `Server error: ${error.response.status}`;
          this.uploadResult = {
            log_id: error.response.data.log_id || null,
            success_count: error.response.data.success_count || 0,
            error_count: error.response.data.error_count || 0,
          };
        } else if (error.request) {
          // The request was made but no response was received (e.g., network error)
          this.errorMessage = 'No response from server. Please check your network connection.';
        } else {
          // Something happened in setting up the request that triggered an Error
          this.errorMessage = `Error: ${error.message}`;
        }
        console.error('Upload error:', error);
      } finally {
        this.uploading = false;
      }
    },
    async downloadErrorFile() {
      // FR38: The Admin Portal shall generate an error file with an 'Error Desc' column upon upload failure.
      // FR34: The system shall provide a screen for users to download an Error Excel file.
      // Assuming a specific endpoint for downloading an error file by its log_id.
      // The system design mentions `/data/errors` for generic error file download.
      // For a specific upload's error file, a more specific endpoint like `/data/errors/{log_id}` is assumed.
      if (!this.uploadResult.log_id) {
        alert('No log ID available to download the error file.');
        return;
      }

      try {
        const response = await axios.get(`/data/errors/${this.uploadResult.log_id}`, {
          responseType: 'blob', // Important for downloading binary data like Excel files
        });

        // Create a URL for the blob and trigger download
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        // Assuming the error file is an Excel file (.xlsx) as per FR34
        link.setAttribute('download', `error_log_${this.uploadResult.log_id}.xlsx`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url); // Clean up the URL object
      } catch (error) {
        console.error('Error downloading error file:', error);
        alert('Failed to download error file. Please try again.');
      }
    },
  },
};
</script>

<style scoped>
.file-upload-card {
  background-color: #f9f9f9;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  margin: 20px auto;
  max-width: 600px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  font-family: Arial, sans-serif;
}

h2 {
  color: #333;
  margin-bottom: 15px;
  text-align: center;
}

p {
  color: #666;
  margin-bottom: 20px;
  text-align: center;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #555;
}

input[type="file"],
select {
  width: calc(100% - 22px); /* Account for padding and border */
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 16px;
  box-sizing: border-box; /* Ensures padding and border are included in the element's total width */
  background-color: #fff;
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
  width: 100%;
  box-sizing: border-box;
  margin-top: 10px;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

.status-message {
  margin-top: 20px;
  padding: 15px;
  border-radius: 4px;
  font-weight: bold;
  text-align: left;
}

.status-message p {
  margin: 5px 0;
  text-align: left; /* Override center alignment for general p */
}

.status-message.loading {
  background-color: #e0f7fa;
  color: #007bff;
  border: 1px solid #007bff;
}

.status-message.success {
  background-color: #d4edda;
  color: #28a745;
  border: 1px solid #28a745;
}

.status-message.error {
  background-color: #f8d7da;
  color: #dc3545;
  border: 1px solid #dc3545;
}

.download-button {
  background-color: #6c757d;
  margin-top: 10px;
  width: auto; /* Allow button to size based on content */
  padding: 8px 15px;
  font-size: 14px;
}

.download-button:hover:not(:disabled) {
  background-color: #5a6268;
}
</style>