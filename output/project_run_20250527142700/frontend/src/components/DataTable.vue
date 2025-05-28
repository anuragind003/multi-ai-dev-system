<template>
  <div class="data-table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="header in headers" :key="header.value">{{ header.text }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="items.length === 0">
          <td :colspan="headers.length" class="no-data">No data available.</td>
        </tr>
        <tr v-for="(item, index) in items" :key="index">
          <td v-for="header in headers" :key="header.value">
            {{ getItemValue(item, header.value) }}
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
     * Array of header objects. Each object should have:
     * - text: The display text for the column header (e.g., 'Customer Name')
     * - value: The key in the item object that corresponds to this column's data (e.g., 'customer_name')
     * Example: [{ text: 'ID', value: 'id' }, { text: 'Name', value: 'name' }]
     */
    headers: {
      type: Array,
      required: true,
      default: () => [],
      validator: (value) => value.every(header => typeof header.text === 'string' && typeof header.value === 'string')
    },
    /**
     * Array of data objects to display in the table rows.
     * Each object's keys should match the 'value' properties in the headers.
     * Example: [{ id: 1, name: 'Alice' }, { id: 2, name: 'Bob' }]
     */
    items: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  methods: {
    /**
     * Retrieves the value for a given key from an item object.
     * This method can be extended to handle nested properties if needed.
     * @param {Object} item - The data object for the current row.
     * @param {string} key - The key (property name) to retrieve from the item.
     * @returns {*} The value associated with the key, or undefined if not found.
     */
    getItemValue(item, key) {
      // Basic implementation: direct property access.
      // For nested properties (e.g., 'customer.name'), this would need to be more complex:
      // return key.split('.').reduce((o, i) => (o ? o[i] : undefined), item);
      return item[key];
    }
  }
};
</script>

<style scoped>
.data-table-container {
  width: 100%;
  overflow-x: auto; /* Allows table to scroll horizontally if content is too wide */
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  background-color: #fff;
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
  background-color: #f8f8f8;
  color: #333;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table tbody tr:hover {
  background-color: #f5f5f5;
  transition: background-color 0.2s ease;
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.data-table .no-data {
  text-align: center;
  padding: 20px;
  color: #777;
  font-style: italic;
}
</style>