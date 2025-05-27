<template>
  <div class="customer-profile-container">
    <h1>Customer Profile</h1>

    <div v-if="loading" class="loading-message">
      Loading customer data...
    </div>

    <div v-else-if="error" class="error-message">
      Error: {{ error }}
    </div>

    <div v-else-if="customer">
      <section class="customer-details card">
        <h2>Customer Details</h2>
        <div class="detail-grid">
          <p><strong>Customer ID:</strong> {{ customer.customer_id }}</p>
          <p><strong>Mobile Number:</strong> {{ customer.mobile_number }}</p>
          <p><strong>PAN Number:</strong> {{ customer.pan_number || 'N/A' }}</p>
          <p><strong>Segment:</strong> {{ customer.segment || 'N/A' }}</p>
          <p><strong>DND Flag:</strong> <span :class="{'dnd-true': customer.dnd_flag, 'dnd-false': !customer.dnd_flag}">{{ customer.dnd_flag ? 'Yes' : 'No' }}</span></p>
        </div>
      </section>

      <section class="current-offers card">
        <h2>Current Offers</h2>
        <div v-if="customer.current_offers && customer.current_offers.length > 0">
          <div v-for="offer in customer.current_offers" :key="offer.offer_id" class="offer-item">
            <p><strong>Offer ID:</strong> {{ offer.offer_id }}</p>
            <p><strong>Type:</strong> {{ offer.offer_type }}</p>
            <p><strong>Status:</strong> <span :class="['offer-status', offer.offer_status.toLowerCase()]">{{ offer.offer_status }}</span></p>
            <p><strong>Propensity:</strong> {{ offer.propensity || 'N/A' }}</p>
            <p><strong>Start Date:</strong> {{ offer.start_date }}</p>
            <p><strong>End Date:</strong> {{ offer.end_date }}</p>
          </div>
        </div>
        <p v-else>No current offers found for this customer.</p>
      </section>

      <section class="journey-stages card">
        <h2>Journey Stages</h2>
        <div v-if="customer.journey_stages && customer.journey_stages.length > 0">
          <div v-for="(stage, index) in customer.journey_stages" :key="index" class="stage-item">
            <p><strong>Event Type:</strong> {{ stage.event_type }}</p>
            <p><strong>Source:</strong> {{ stage.source }}</p>
            <p><strong>Timestamp:</strong> {{ new Date(stage.event_timestamp).toLocaleString() }}</p>
            <p v-if="stage.event_details"><strong>Details:</strong> {{ JSON.stringify(stage.event_details) }}</p>
          </div>
        </div>
        <p v-else>No journey stages found for this customer.</p>
      </section>
    </div>
    <div v-else class="no-data-message">
      No customer data available. Please ensure a valid Customer ID is provided.
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'CustomerProfile',
  data() {
    return {
      customer: null,
      loading: true,
      error: null,
    };
  },
  created() {
    this.fetchCustomerProfile();
  },
  methods: {
    async fetchCustomerProfile() {
      const customerId = this.$route.params.id;
      if (!customerId) {
        this.error = 'Customer ID is missing in the URL.';
        this.loading = false;
        return;
      }

      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get(`/api/customers/${customerId}`);
        this.customer = response.data;
      } catch (err) {
        console.error('Failed to fetch customer profile:', err);
        if (err.response) {
          this.error = `Could not load customer profile: ${err.response.status} - ${err.response.data.message || 'Server error'}`;
        } else if (err.request) {
          this.error = 'No response from server. Please check your network connection.';
        } else {
          this.error = `Error setting up request: ${err.message}`;
        }
        this.customer = null; // Clear any previous data
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.customer-profile-container {
  max-width: 900px;
  margin: 40px auto;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 2.2em;
}

h2 {
  color: #0056b3;
  border-bottom: 2px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 20px;
  font-size: 1.6em;
}

.card {
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 25px;
  margin-bottom: 25px;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
}

.loading-message, .error-message, .no-data-message {
  text-align: center;
  padding: 20px;
  font-size: 1.1em;
  color: #555;
}

.error-message {
  color: #d9534f;
  background-color: #f2dede;
  border: 1px solid #ebccd1;
  border-radius: 4px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.detail-grid p {
  margin: 0;
  padding: 5px 0;
  font-size: 1.05em;
}

.detail-grid strong {
  color: #333;
}

.dnd-true {
  color: #d9534f;
  font-weight: bold;
}

.dnd-false {
  color: #5cb85c;
  font-weight: bold;
}

.offer-item, .stage-item {
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 15px;
  background-color: #fdfdfd;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.offer-item p, .stage-item p {
  margin: 5px 0;
}

.offer-status {
  font-weight: bold;
  padding: 3px 8px;
  border-radius: 4px;
  display: inline-block;
  font-size: 0.9em;
}

.offer-status.active {
  background-color: #d4edda;
  color: #155724;
}

.offer-status.inactive {
  background-color: #fff3cd;
  color: #856404;
}

.offer-status.expired {
  background-color: #f8d7da;
  color: #721c24;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .customer-profile-container {
    margin: 20px;
    padding: 15px;
  }

  h1 {
    font-size: 1.8em;
  }

  h2 {
    font-size: 1.4em;
  }

  .card {
    padding: 20px;
  }
}

@media (max-width: 480px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>