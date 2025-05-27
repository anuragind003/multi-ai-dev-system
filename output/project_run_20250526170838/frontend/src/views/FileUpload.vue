<template>
  <div class="file-upload-container">
    <h2>Upload Customer Data</h2>

    <form @submit.prevent="uploadFile" class="upload-form">
      <div class="form-group">
        <label for="loanType">Select Loan Type:</label>
        <select id="loanType" v-model="loanType" required>
          <option value="" disabled>Please select a loan type</option>
          <option v-for="type in loanTypes" :key="type" :value="type">{{ type }}</option>
        </select>
      </div>

      <div class="form-group">
        <label for="fileInput">Choose File (CSV):</label>
        <input type="file" id="fileInput" @change="handleFileChange" accept=".csv" required ref="fileInput">
      </div>

      <button type="submit" :disabled="loading || !selectedFile || !loanType">
        <span v-if="loading">Uploading...</span>
        <span v-else>Upload File</span>
      </button>
    </form>

    <div v-if="message" :class="['message', { 'error': isError, 'success': !isError }]">
      {{ message }}
    </div>

    <div v-if="uploadLog" class="upload-log">
      <h3>Upload Summary:</h3>
      <p><strong>Log ID:</strong> {{ uploadLog.log_id }}</p>
      <p><strong>Successful Records:</strong> {{ uploadLog.success_count }}</p>
      <p><strong>Error Records:</strong> {{ uploadLog.error_count }}</p>
      <p v-if="uploadLog.error_count > 0">
        Please download the <router-link to="/data-downloads?type=errors">Error Excel file</router-link> for details.
      </p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'FileUpload',
  data() {
    return {
      selectedFile: null,
      loanType: '',
      loanTypes: ['Prospect', 'TW Loyalty', 'Topup', 'Employee'],
      loading: false,
      message: '',
      isError: false,
      uploadLog: null,
    };
  },
  methods: {
    handleFileChange(event) {
      this.selectedFile = event.target.files[0];
      this.message = ''; // Clear previous messages
      this.isError = false;
      this.uploadLog = null;
    },
    async uploadFile() {
      if (!this.selectedFile || !this.loanType) {
        this.message = 'Please select a file and a loan type.';
        this.isError = true;
        return;
      }

      this.loading = true;
      this.message = '';
      this.isError = false;
      this.uploadLog = null;

      const formData = new FormData();
      formData.append('file', this.selectedFile);
      formData.append('loan_type', this.loanType);

      try {
        const response = await axios.post('/admin/customer-data/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        this.message = 'File uploaded successfully!';
        this.isError = false;
        this.uploadLog = response.data;

        // Clear the file input after successful upload
        this.selectedFile = null;
        if (this.$refs.fileInput) {
          this.$refs.fileInput.value = '';
        }
        this.loanType = ''; // Optionally reset loan type
      } catch (error) {
        console.error('Upload failed:', error);
        this.isError = true;
        if (error.response && error.response.data && error.response.data.message) {
          this.message = `Upload failed: ${error.response.data.message}`;
        } else {
          this.message = 'An unexpected error occurred during upload.';
        }
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.file-upload-container {
  max-width: 600px;
  margin: 50px auto;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background-color: #ffffff;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 1.8em;
}

.upload-form .form-group {
  margin-bottom: 20px;
}

.upload-form label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #555;
}

.upload-form select,
.upload-form input[type="file"] {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  box-sizing: border-box; /* Ensures padding doesn't increase width */
  font-size: 1em;
  background-color: #f9f9f9;
}

.upload-form select {
  appearance: none; /* Remove default arrow */
  background-image: url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23007bff%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-6.5%200-12.3%203.2-16.1%208.1-3.8%204.9-4.9%2011-3.1%2016.9l132.8%20140.7c3.8%204%209.4%206.3%2015.1%206.3s11.3-2.3%2015.1-6.3L290.2%2094.3c1.8-5.9.7-12-3.1-16.9z%22%2F%3E%3C%2Fsvg%3E');
  background-repeat: no-repeat;
  background-position: right 10px top 50%;
  background-size: 12px;
}

.upload-form button {
  width: 100%;
  padding: 15px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 1.1em;
  cursor: pointer;
  transition: background-color 0.3s ease;
  margin-top: 20px;
}

.upload-form button:hover:not(:disabled) {
  background-color: #0056b3;
}

.upload-form button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.message {
  margin-top: 25px;
  padding: 15px;
  border-radius: 5px;
  font-weight: bold;
  text-align: center;
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

.upload-log {
  margin-top: 30px;
  padding: 20px;
  background-color: #e9f7ef;
  border: 1px solid #c3e6cb;
  border-radius: 8px;
}

.upload-log h3 {
  color: #28a745;
  margin-bottom: 15px;
  font-size: 1.3em;
}

.upload-log p {
  margin-bottom: 8px;
  color: #333;
}

.upload-log strong {
  color: #0056b3;
}

.upload-log a {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
}

.upload-log a:hover {
  text-decoration: underline;
}
</style>