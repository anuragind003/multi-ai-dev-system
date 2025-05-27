<template>
  <div class="report-table-container">
    <h2>{{ reportTitle }}</h2>

    <div v-if="loading" class="loading-indicator">
      <div class="spinner"></div>
      Loading report data...
    </div>

    <div v-if="error" class="error-message">
      Error: {{ error }}
    </div>

    <div v-if="!loading && !error && headers.length > 0 && rows.length > 0" class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th v-for="header in headers" :key="header">{{ header }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in rows" :key="rowIndex">
            <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!loading && !error && (headers.length === 0 || rows.length === 0)" class="no-data-message">
      No data available for this report.
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ReportTable',
  props: {
    /**
     * Specifies the type of report to display.
     * Valid values: 'daily-tally', 'customer-view'.
     */
    reportType: {
      type: String,
      required: true,
      validator: (value) => ['daily-tally', 'customer-view'].includes(value)
    },
    /**
     * Optional: Date for daily reports (e.g., 'YYYY-MM-DD').
     * Required if reportType is 'daily-tally'.
     */
    reportDate: {
      type: String,
      default: ''
    },
    /**
     * Optional: Customer ID for customer-level view.
     * Required if reportType is 'customer-view'.
     */
    customerId: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      headers: [], // Array of column headers (strings)
      rows: [],    // Array of arrays, where each inner array is a row of data
      loading: false,
      error: null
    };
  },
  computed: {
    reportTitle() {
      switch (this.reportType) {
        case 'daily-tally':
          return `Daily Data Tally Report ${this.reportDate ? `for ${this.reportDate}` : ''}`;
        case 'customer-view':
          return `Customer Journey View ${this.customerId ? `for Customer ID: ${this.customerId}` : ''}`;
        default:
          return 'Report';
      }
    },
    apiUrl() {
      // Base URL for the Flask backend, defaulting to localhost:5000 if not set in .env
      const baseUrl = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5000';
      let endpoint = '';
      const params = new URLSearchParams();

      switch (this.reportType) {
        case 'daily-tally':
          // FR39: The system shall provide a front-end for daily reports for data tally.
          // Assuming a backend endpoint for daily tally reports.
          endpoint = '/api/reports/daily-tally';
          if (this.reportDate) {
            params.append('date', this.reportDate);
          }
          break;
        case 'customer-view':
          // FR40: The system shall provide a front-end for customer-level view with stages.
          // Assuming a backend endpoint that returns tabular data for customer stages.
          // The system design mentions /customers/{customer_id} for a single customer profile,
          // but for a 'report table', a dedicated endpoint returning tabular stage data is more suitable.
          endpoint = `/api/reports/customer-stages`;
          if (this.customerId) {
            params.append('customer_id', this.customerId);
          }
          break;
        default:
          return ''; // Should not be reached due to prop validator
      }
      return `${baseUrl}${endpoint}?${params.toString()}`;
    }
  },
  methods: {
    /**
     * Fetches report data from the backend API based on reportType and other props.
     */
    async fetchReportData() {
      this.loading = true;
      this.error = null;
      this.headers = [];
      this.rows = [];

      // Validate required props for specific report types
      if (this.reportType === 'daily-tally' && !this.reportDate) {
        this.error = 'Report Date is required for Daily Data Tally Report.';
        this.loading = false;
        return;
      }
      if (this.reportType === 'customer-view' && !this.customerId) {
        this.error = 'Customer ID is required for Customer Journey View.';
        this.loading = false;
        return;
      }

      if (!this.apiUrl) {
        this.error = 'Invalid report configuration.';
        this.loading = false;
        return;
      }

      try {
        const response = await axios.get(this.apiUrl);
        const data = response.data;

        // Expected data format from backend:
        // {
        //   "headers": ["Column Name 1", "Column Name 2", ...],
        //   "rows": [
        //     ["Value 1A", "Value 1B", ...],
        //     ["Value 2A", "Value 2B", ...]
        //   ]
        // }
        if (data && Array.isArray(data.headers) && Array.isArray(data.rows)) {
          this.headers = data.headers;
          this.rows = data.rows;
        } else {
          this.error = 'Invalid data format received from the server. Expected "headers" and "rows" arrays.';
        }
      } catch (err) {
        console.error('Failed to fetch report data:', err);
        // Display a user-friendly error message
        this.error = err.response?.data?.message || err.message || 'An unknown error occurred while fetching report data.';
      } finally {
        this.loading = false;
      }
    }
  },
  watch: {
    // Watch for changes in props and re-fetch data
    reportType: 'fetchReportData',
    reportDate: 'fetchReportData',
    customerId: 'fetchReportData'
  },
  mounted() {
    // Fetch data when the component is first mounted
    this.fetchReportData();
  }
};
</script>

<style scoped>
.report-table-container {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h2 {
  color: #333;
  margin-bottom: 25px;
  text-align: center;
  font-size: 1.8em;
  font-weight: 600;
}

.loading-indicator, .error-message, .no-data-message {
  text-align: center;
  padding: 30px;
  font-size: 1.1em;
  color: #555;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.loading-indicator {
  color: #007bff;
}

.spinner {
  border: 4px solid rgba(0, 123, 255, 0.1);
  border-top: 4px solid #007bff;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #dc3545;
  font-weight: bold;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 5px;
}

.no-data-message {
  color: #6c757d;
  background-color: #e9ecef;
  border: 1px solid #dee2e6;
  border-radius: 5px;
}

.table-wrapper {
  overflow-x: auto; /* Allows horizontal scrolling for wide tables */
  max-width: 100%;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  background-color: #fff;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  overflow: hidden; /* Ensures rounded corners apply to table content */
}

th, td {
  border: 1px solid #e0e0e0;
  padding: 14px 18px;
  text-align: left;
  vertical-align: middle;
}

th {
  background-color: #007bff;
  color: white;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.95em;
  position: sticky;
  top: 0; /* Makes headers sticky if table is scrollable */
  z-index: 1;
}

tbody tr:nth-child(even) {
  background-color: #f8f9fa;
}

tbody tr:hover {
  background-color: #e2f0ff;
  transition: background-color 0.2s ease;
}

td {
  color: #495057;
  font-size: 0.9em;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .report-table-container {
    padding: 15px;
  }

  h2 {
    font-size: 1.5em;
    margin-bottom: 20px;
  }

  th, td {
    padding: 10px 12px;
    font-size: 0.8em;
  }
}

@media (max-width: 480px) {
  .report-table-container {
    padding: 10px;
  }

  h2 {
    font-size: 1.3em;
    margin-bottom: 15px;
  }

  th, td {
    padding: 8px 10px;
    font-size: 0.75em;
  }
}
</style>