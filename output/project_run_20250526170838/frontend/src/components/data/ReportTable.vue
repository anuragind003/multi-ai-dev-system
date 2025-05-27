<template>
  <div class="report-table-container">
    <h2>{{ reportTitle }}</h2>

    <div v-if="loading" class="loading-indicator">
      Loading report data...
    </div>

    <div v-else-if="error" class="error-message">
      Error: {{ error }}
    </div>

    <div v-else-if="reportData.length === 0" class="no-data-message">
      No data available for this report.
    </div>

    <div v-else class="table-wrapper">
      <table class="report-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key">
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in reportData" :key="rowIndex">
            <td v-for="column in columns" :key="column.key">
              {{ getCellValue(row, column.key) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import axios from 'axios'; // Assuming axios is installed and configured in your project

export default {
  name: 'ReportTable',
  props: {
    /**
     * Defines the type of report to display.
     * Valid values are 'daily-tally' for FR39 or 'customer-journey' for FR40.
     */
    reportType: {
      type: String,
      required: true,
      validator: (value) => ['daily-tally', 'customer-journey'].includes(value)
    }
  },
  data() {
    return {
      reportData: [],
      columns: [],
      loading: false,
      error: null
    };
  },
  computed: {
    /**
     * Returns a user-friendly title based on the reportType prop.
     */
    reportTitle() {
      switch (this.reportType) {
        case 'daily-tally':
          return 'Daily Data Tally Report';
        case 'customer-journey':
          return 'Customer Journey Stages Report';
        default:
          return 'Report'; // Fallback, though validator should prevent this
      }
    },
    /**
     * Constructs the API URL based on the reportType.
     * Assumes backend endpoints for these reports.
     */
    apiUrl() {
      // Use environment variable for API base URL for flexibility (e.g., .env.development, .env.production)
      const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5000';
      switch (this.reportType) {
        case 'daily-tally':
          // Hypothetical endpoint for daily data tally report (FR39)
          return `${API_BASE_URL}/api/reports/daily-tally`;
        case 'customer-journey':
          // Hypothetical endpoint for customer-level view with stages report (FR40)
          return `${API_BASE_URL}/api/reports/customer-journey`;
        default:
          return ''; // Should not be reached due to prop validator
      }
    }
  },
  watch: {
    /**
     * Watches for changes in the reportType prop and re-fetches data.
     * `immediate: true` ensures data is fetched on initial component load.
     */
    reportType: {
      immediate: true,
      handler() {
        this.fetchReportData();
      }
    }
  },
  methods: {
    /**
     * Fetches report data from the backend API.
     * Handles loading states, errors, and dynamically sets table columns.
     */
    async fetchReportData() {
      this.loading = true;
      this.error = null;
      this.reportData = [];
      this.columns = [];

      try {
        const response = await axios.get(this.apiUrl);
        this.reportData = response.data;

        if (this.reportData.length > 0) {
          // Dynamically generate columns from the keys of the first data row.
          // This provides flexibility for different report structures.
          this.columns = Object.keys(this.reportData[0]).map(key => ({
            key: key,
            label: this.formatColumnHeader(key) // Format key for display
          }));
        }
      } catch (err) {
        console.error(`Failed to fetch ${this.reportType} report data:`, err);
        // Provide a user-friendly error message
        this.error = err.response?.data?.message || err.message || 'An unknown error occurred while fetching data.';
      } finally {
        this.loading = false;
      }
    },
    /**
     * Formats a data key (e.g., 'customer_id', 'totalCustomers') into a readable table header.
     * Converts snake_case or camelCase to Title Case.
     * @param {string} key - The original key from the data object.
     * @returns {string} The formatted label.
     */
    formatColumnHeader(key) {
      return key
        .replace(/_/g, ' ') // Replace underscores with spaces
        .replace(/([A-Z])/g, ' $1') // Add space before capital letters (for camelCase)
        .trim() // Remove leading/trailing spaces
        .split(' ') // Split into words
        .map(word => word.charAt(0).toUpperCase() + word.slice(1)) // Capitalize first letter of each word
        .join(' '); // Join words back with spaces
    },
    /**
     * Safely retrieves a cell value from a row object.
     * Can be extended to handle nested properties if needed in the future.
     * @param {Object} row - The data row object.
     * @param {string} key - The key of the column.
     * @returns {*} The value for the given key in the row.
     */
    getCellValue(row, key) {
      return row[key];
    }
  }
};
</script>

<style scoped>
/* Container for the entire report table component */
.report-table-container {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin: 20px auto; /* Center the container */
  max-width: 1200px; /* Limit width for better readability */
}

/* Report title styling */
h2 {
  color: #333;
  margin-bottom: 25px;
  text-align: center;
  font-size: 1.8em;
  font-weight: 600;
}

/* Styles for loading, error, and no data messages */
.loading-indicator,
.error-message,
.no-data-message {
  text-align: center;
  padding: 30px;
  font-size: 1.2em;
  color: #555;
  background-color: #eef;
  border-radius: 5px;
  margin-top: 20px;
}

.error-message {
  color: #d9534f; /* Red for errors */
  background-color: #fdd;
  border: 1px solid #d9534f;
  font-weight: bold;
}

.no-data-message {
  color: #777;
  background-color: #f0f0f0;
}

/* Wrapper for the table to enable horizontal scrolling on small screens */
.table-wrapper {
  overflow-x: auto;
  border: 1px solid #ddd;
  border-radius: 5px;
}

/* Main table styling */
.report-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 600px; /* Ensure table doesn't get too narrow */
}

/* Table header cells */
.report-table th {
  background-color: #007bff; /* Primary blue color */
  color: white;
  padding: 15px 20px;
  text-align: left;
  font-weight: bold;
  white-space: nowrap; /* Prevent header text from wrapping */
}

/* Table data cells */
.report-table td {
  border: 1px solid #eee; /* Lighter border for cells */
  padding: 12px 20px;
  text-align: left;
  color: #333;
  white-space: nowrap; /* Prevent cell content from wrapping */
}

/* Zebra striping for table rows */
.report-table tbody tr:nth-child(even) {
  background-color: #f8f8f8;
}

/* Hover effect for table rows */
.report-table tbody tr:hover {
  background-color: #eef;
  cursor: default;
}
</style>