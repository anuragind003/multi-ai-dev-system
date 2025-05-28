<template>
  <div id="app">
    <header>
      <h1>LTFS Offer CDP - Data Export Portal</h1>
    </header>
    <main>
      <section class="export-section">
        <h2>Download Data Files</h2>
        <div class="button-group">
          <button @click="downloadFile('moengage-campaign-file')" :disabled="loading.moengage">
            {{ loading.moengage ? 'Generating...' : 'Download Moengage Campaign File' }}
          </button>
          <button @click="downloadFile('duplicate-customers')" :disabled="loading.duplicate">
            {{ loading.duplicate ? 'Generating...' : 'Download Duplicate Data File' }}
          </button>
          <button @click="downloadFile('unique-customers')" :disabled="loading.unique">
            {{ loading.unique ? 'Generating...' : 'Download Unique Data File' }}
          </button>
          <button @click="downloadFile('data-errors')" :disabled="loading.errors">
            {{ loading.errors ? 'Generating...' : 'Download Error Excel File' }}
          </button>
        </div>
        <p v-if="message" :class="['message', messageType]">{{ message }}</p>
      </section>
    </main>
    <footer>
      <p>&copy; {{ currentYear }} LTFS Offer CDP</p>
    </footer>
  </div>
</template>

<script>
import { ref } from 'vue';

export default {
  name: 'App',
  setup() {
    // Determine API base URL. Use environment variable for flexibility (e.g., .env.development, .env.production)
    // For Vite, environment variables are exposed via `import.meta.env`
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

    const loading = ref({
      moengage: false,
      duplicate: false,
      unique: false,
      errors: false,
    });
    const message = ref('');
    const messageType = ref(''); // Can be 'success' or 'error'

    const currentYear = new Date().getFullYear();

    const downloadFile = async (endpoint) => {
      // Map endpoint name to loading state key (e.g., 'moengage-campaign-file' -> 'moengage')
      const loadingKey = endpoint.replace(/-/g, '_');
      loading.value[loadingKey] = true;
      message.value = '';
      messageType.value = '';

      try {
        const response = await fetch(`${API_BASE_URL}/exports/${endpoint}`);

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! Status: ${response.status}, Message: ${errorText}`);
        }

        // Attempt to get filename from Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${endpoint}.csv`; // Default filename if header is missing or malformed
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename\*?=['"]?(?:UTF-8''|)([^"';\n]*)/i);
          if (filenameMatch && filenameMatch[1]) {
            try {
              filename = decodeURIComponent(filenameMatch[1]);
            } catch (e) {
              console.warn('Could not decode filename from Content-Disposition, using raw value.', e);
              filename = filenameMatch[1];
            }
          }
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename; // Set the downloaded file name
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url); // Clean up the URL object

        message.value = `File '${filename}' downloaded successfully!`;
        messageType.value = 'success';

      } catch (error) {
        console.error('Download failed:', error);
        message.value = `Failed to download file: ${error.message || 'An unknown error occurred.'}`;
        messageType.value = 'error';
      } finally {
        loading.value[loadingKey] = false;
      }
    };

    return {
      loading,
      message,
      messageType,
      currentYear,
      downloadFile,
    };
  },
};
</script>

<style>
/* Basic styling for the application */
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin: 60px auto; /* Center the app container */
  max-width: 900px; /* Limit width for better readability */
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  min-height: 600px; /* Minimum height for the app container */
}

header {
  background-color: #42b983;
  color: white;
  padding: 25px;
  border-radius: 8px 8px 0 0;
}

h1 {
  margin: 0;
  font-size: 2.2em;
}

main {
  flex-grow: 1;
  padding: 30px;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.export-section {
  width: 100%;
  max-width: 700px;
}

h2 {
  color: #34495e;
  margin-bottom: 30px;
  font-size: 1.8em;
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
}

button {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 15px 30px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1em;
  font-weight: bold;
  transition: background-color 0.3s ease, transform 0.2s ease;
  min-width: 280px; /* Ensure buttons have a consistent minimum width */
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

button:hover:not(:disabled) {
  background-color: #369f70;
  transform: translateY(-2px);
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
  box-shadow: none;
}

.message {
  margin-top: 30px;
  padding: 15px;
  border-radius: 8px;
  font-weight: bold;
  font-size: 1.1em;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.success {
  background-color: #e6ffe6;
  color: #008000;
  border: 1px solid #008000;
}

.error {
  background-color: #ffe6e6;
  color: #ff0000;
  border: 1px solid #ff0000;
}

footer {
  margin-top: auto; /* Pushes footer to the bottom */
  padding: 20px;
  background-color: #f0f0f0;
  color: #555;
  border-radius: 0 0 8px 8px;
  font-size: 0.9em;
}
</style>