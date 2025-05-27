<template>
  <div class="daily-reports-container">
    <h1>Daily Data Tally Reports</h1>

    <div v-if="loading" class="loading-message">
      <p>Loading daily reports...</p>
    </div>

    <div v-else-if="error" class="error-message">
      <p>Error: {{ error }}</p>
      <p>Please try again later.</p>
    </div>

    <div v-else-if="reports.length === 0" class="no-data-message">
      <p>No daily reports available.</p>
    </div>

    <div v-else class="reports-table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Report Date</th>
            <th>Total Ingested</th>
            <th>Unique Records</th>
            <th>Duplicate Records</th>
            <th>Error Records</th>
            <th>Moengage Exported</th>
            <th>Successful Uploads</th>
            <th>Failed Uploads</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="report in reports" :key="report.report_date">
            <td>{{ report.report_date }}</td>
            <td>{{ report.total_records_ingested }}</td>
            <td>{{ report.unique_records }}</td>
            <td>{{ report.duplicate_records }}</td>
            <td>{{ report.error_records }}</td>
            <td>{{ report.moengage_exported_records }}</td>
            <td>{{ report.successful_uploads }}</td>
            <td>{{ report.failed_uploads }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DailyReports',
  data() {
    return {
      reports: [],
      loading: true,
      error: null,
    };
  },
  created() {
    this.fetchDailyReports();
  },
  methods: {
    async fetchDailyReports() {
      this.loading = true;
      this.error = null;
      try {
        // Assuming the backend Flask API is running on http://localhost:5000
        // and has an endpoint for daily reports.
        // This endpoint is inferred based on FR39 and common reporting needs.
        const response = await axios.get('http://localhost:5000/api/reports/daily-tally');
        this.reports = response.data;
      } catch (err) {
        console.error('Failed to fetch daily reports:', err);
        this.error = 'Could not retrieve daily reports. Please check the server connection.';
        if (err.response) {
          this.error += ` Server responded with: ${err.response.status} - ${err.response.data.message || err.response.statusText}`;
        } else if (err.request) {
          this.error += ' No response received from server.';
        }
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.daily-reports-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #333;
}

h1 {
  color: #2c3e50;
  text-align: center;
  margin-bottom: 30px;
}

.loading-message, .error-message, .no-data-message {
  text-align: center;
  padding: 20px;
  border-radius: 8px;
  margin-top: 20px;
}

.loading-message {
  background-color: #e0f7fa;
  color: #00796b;
}

.error-message {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #ef9a9a;
}

.no-data-message {
  background-color: #fff3e0;
  color: #e65100;
}

.reports-table-wrapper {
  overflow-x: auto;
  margin-top: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  background-color: #ffffff;
  border-radius: 8px;
  overflow: hidden; /* Ensures border-radius applies to table corners */
}

th, td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background-color: #f2f2f2;
  color: #555;
  font-weight: bold;
  text-transform: uppercase;
  font-size: 0.9em;
}

tbody tr:nth-child(even) {
  background-color: #f9f9f9;
}

tbody tr:hover {
  background-color: #f0f0f0;
  cursor: pointer;
}

td {
  font-size: 0.95em;
  color: #444;
}
</style>