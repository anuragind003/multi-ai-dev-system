<template>
  <div class="data-table-container">
    <h2 v-if="title" class="table-title">{{ title }}</h2>

    <div v-if="loading" class="loading-indicator">Loading data...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!items || items.length === 0" class="no-data-message">No data available.</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th v-for="header in headers" :key="header.value">{{ header.text }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, index) in items" :key="index">
          <td v-for="header in headers" :key="header.value">
            {{ item[header.value] }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  name: 'DataTable',
  props: {
    /**
     * Array of header objects. Each object should have 'text' (display name)
     * and 'value' (key in the item object).
     * Example: [{ text: 'Customer ID', value: 'customer_id' }, { text: 'Mobile', value: 'mobile_number' }]
     */
    headers: {
      type: Array,
      required: true,
      validator: (value) => value.every(header => typeof header === 'object' && 'text' in header && 'value' in header)
    },
    /**
     * Array of data objects, where each object represents a row.
     * Keys in the objects should match the 'value' properties in the headers.
     */
    items: {
      type: Array,
      required: true
    },
    /**
     * Optional title for the table.
     */
    title: {
      type: String,
      default: ''
    },
    /**
     * Boolean to indicate if data is currently being loaded.
     */
    loading: {
      type: Boolean,
      default: false
    },
    /**
     * String to display an error message if data fetching fails.
     */
    error: {
      type: String,
      default: ''
    }
  }
};
</script>

<style scoped>
.data-table-container {
  width: 100%;
  overflow-x: auto; /* Allows horizontal scrolling for wide tables */
  margin-top: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  background-color: #fff;
}

.table-title {
  padding: 15px;
  margin: 0;
  font-size: 1.5em;
  color: #333;
  border-bottom: 1px solid #e0e0e0;
  background-color: #f9f9f9;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 0.9em;
}

.data-table th,
.data-table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.data-table th {
  background-color: #f2f2f2;
  color: #555;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table tbody tr:hover {
  background-color: #f5f5f5;
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.loading-indicator,
.error-message,
.no-data-message {
  padding: 20px;
  text-align: center;
  color: #777;
  font-style: italic;
}

.error-message {
  color: #d9534f; /* A common red for error messages */
  font-weight: bold;
}
</style>