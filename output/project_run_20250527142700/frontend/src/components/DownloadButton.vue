<template>
  <div>
    <BaseButton
      :variant="variant"
      :size="size"
      :data-testid="dataTestid"
      :loading="isLoading"
      @click="handleDownload"
    >
      {{ label }}
    </BaseButton>
    <div v-if="message" :class="['message', messageType]">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';
import BaseButton from './BaseButton.vue'; // Assuming BaseButton is in the same directory or correctly aliased

const props = defineProps({
  /**
   * The text displayed on the button.
   */
  label: {
    type: String,
    required: true,
  },
  /**
   * The API endpoint to call for the file download.
   * E.g., '/api/exports/moengage-campaign-file'
   */
  endpoint: {
    type: String,
    required: true,
  },
  /**
   * The suggested filename for the downloaded file.
   * This will be used if the Content-Disposition header doesn't provide one.
   */
  filename: {
    type: String,
    required: true,
  },
  /**
   * Visual variant of the button (e.g., 'primary', 'secondary').
   * Passed to BaseButton.
   */
  variant: {
    type: String,
    default: 'primary',
  },
  /**
   * Size of the button (e.g., 'small', 'medium', 'large').
   * Passed to BaseButton.
   */
  size: {
    type: String,
    default: 'medium',
  },
  /**
   * A data-testid attribute for E2E testing.
   */
  dataTestid: {
    type: String,
    default: '',
  },
});

const isLoading = ref(false);
const message = ref('');
const messageType = ref(''); // 'success' or 'error'

/**
 * Handles the file download process.
 * Makes an API call, creates a Blob from the response, and triggers a download.
 */
const handleDownload = async () => {
  isLoading.value = true;
  message.value = '';
  messageType.value = '';

  try {
    const response = await axios.get(props.endpoint, {
      responseType: 'blob', // Crucial for downloading binary data
    });

    // Attempt to extract filename from Content-Disposition header
    const contentDisposition = response.headers['content-disposition'];
    let actualFilename = props.filename;
    if (contentDisposition) {
      // Regex to find filename in Content-Disposition, handling UTF-8 and quoted filenames
      const filenameMatch = contentDisposition.match(/filename\*?=['"]?(?:UTF-8''|[^; ]+)?([^; ]+)/);
      if (filenameMatch && filenameMatch[1]) {
        try {
          // Decode URI component if it's URL-encoded, and remove surrounding quotes
          actualFilename = decodeURIComponent(filenameMatch[1].replace(/^"|"$/g, ''));
        } catch (e) {
          console.warn('Could not decode filename from Content-Disposition, using provided filename.', e);
          actualFilename = filenameMatch[1].replace(/^"|"$/g, '');
        }
      }
    }

    // Create a Blob from the response data
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);

    // Create a temporary anchor element to trigger the download
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', actualFilename); // Set the download filename
    document.body.appendChild(link);
    link.click(); // Programmatically click the link to start download
    document.body.removeChild(link); // Clean up the temporary link
    window.URL.revokeObjectURL(url); // Release the object URL

    message.value = `${props.label} downloaded successfully!`;
    messageType.value = 'success';
  } catch (error) {
    console.error('Download error:', error);
    message.value = `Failed to download ${props.label}. Please try again.`;
    messageType.value = 'error';

    // If the error response is a Blob (e.g., JSON error from backend), try to parse it
    if (error.response && error.response.data instanceof Blob) {
      const reader = new FileReader();
      reader.onload = function() {
        try {
          const errorData = JSON.parse(reader.result);
          if (errorData.message) {
            message.value = `Failed to download ${props.label}: ${errorData.message}`;
          }
        } catch (e) {
          // Not a JSON error, or parsing failed, keep generic message
          console.warn('Could not parse error response as JSON:', e);
        }
      };
      reader.readAsText(error.response.data);
    } else if (error.response && error.response.data && typeof error.response.data === 'object') {
        // Handle direct JSON error responses
        if (error.response.data.message) {
            message.value = `Failed to download ${props.label}: ${error.response.data.message}`;
        }
    }
  } finally {
    isLoading.value = false;
    // Clear the message after 5 seconds
    setTimeout(() => {
      message.value = '';
      messageType.value = '';
    }, 5000);
  }
};
</script>

<style scoped>
/* Styles for the feedback message */
.message {
  margin-top: 10px;
  padding: 8px 15px;
  border-radius: 5px;
  font-size: 0.9em;
  text-align: center;
  word-break: break-word; /* Ensure long messages wrap */
}

.message.success {
  background-color: #e6ffe6;
  color: #008000;
  border: 1px solid #008000;
}

.message.error {
  background-color: #ffe6e6;
  color: #cc0000;
  border: 1px solid #cc0000;
}
</style>