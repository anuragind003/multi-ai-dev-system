<template>
  <div class="customer-profile-view">
    <h1>Customer Profile</h1>

    <div v-if="loading" class="loading-message">
      Loading customer profile...
    </div>

    <div v-else-if="error" class="error-message">
      Error: {{ error }}
    </div>

    <div v-else-if="customerProfile">
      <div class="profile-section">
        <h2>Customer Details</h2>
        <p><strong>Customer ID:</strong> {{ customerProfile.customer_id }}</p>
        <p><strong>Mobile Number:</strong> {{ customerProfile.mobile_number }}</p>
        <p><strong>PAN Number:</strong> {{ customerProfile.pan_number }}</p>
        <p><strong>Segment:</strong> {{ customerProfile.segment }}</p>
        <p><strong>DND Flag:</strong> {{ customerProfile.dnd_flag ? 'Yes' : 'No' }}</p>
      </div>

      <div class="profile-section">
        <h2>Current Offers</h2>
        <div v-if="customerProfile.current_offers && customerProfile.current_offers.length > 0">
          <div v-for="offer in customerProfile.current_offers" :key="offer.offer_id" class="offer-card">
            <h3>Offer ID: {{ offer.offer_id }}</h3>
            <p><strong>Type:</strong> {{ offer.offer_type }}</p>
            <p><strong>Status:</strong> {{ offer.offer_status }}</p>
            <p><strong>Propensity:</strong> {{ offer.propensity }}</p>
            <p><strong>Start Date:</strong> {{ offer.start_date }}</p>
            <p><strong>End Date:</strong> {{ offer.end_date }}</p>
          </div>
        </div>
        <p v-else>No current offers found for this customer.</p>
      </div>

      <div class="profile-section">
        <h2>Journey Stages / Events</h2>
        <div v-if="customerProfile.journey_stages && customerProfile.journey_stages.length > 0">
          <div v-for="(event, index) in customerProfile.journey_stages" :key="index" class="event-card">
            <p><strong>Event Type:</strong> {{ event.event_type }}</p>
            <p><strong>Source:</strong> {{ event.source }}</p>
            <p><strong>Timestamp:</strong> {{ new Date(event.event_timestamp).toLocaleString() }}</p>
            <!-- event_details can be displayed here if its structure is known and relevant -->
          </div>
        </div>
        <p v-else>No journey stages or events found for this customer.</p>
      </div>
    </div>

    <div v-else class="no-profile-message">
      Please provide a customer ID in the URL (e.g., /customer-profile/your-customer-id).
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'CustomerProfileView',
  data() {
    return {
      customerProfile: null,
      loading: false,
      error: null,
    };
  },
  created() {
    // Fetch data when the component is created
    this.fetchCustomerProfile();
  },
  watch: {
    // Watch for changes in route parameters, specifically the 'id'
    // This allows the component to re-fetch data if the customer ID in the URL changes
    '$route.params.id': 'fetchCustomerProfile'
  },
  methods: {
    async fetchCustomerProfile() {
      const customerId = this.$route.params.id;

      if (!customerId) {
        this.customerProfile = null;
        this.error = 'No customer ID provided in the URL.';
        return;
      }

      this.loading = true;
      this.error = null;
      this.customerProfile = null; // Clear previous data before fetching new

      try {
        // Assuming your Flask backend is running on http://localhost:5000
        // In a production environment, you would configure a base URL for axios
        // or use a proxy to avoid CORS issues and manage environment-specific URLs.
        const response = await axios.get(`http://localhost:5000/api/customers/${customerId}`);
        this.customerProfile = response.data;
      } catch (err) {
        console.error('Failed to fetch customer profile:', err);
        if (err.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx (e.g., 404 Not Found, 500 Internal Server Error)
          this.error = err.response.data.message || `Server error: ${err.response.status} - ${err.response.statusText}`;
        } else if (err.request) {
          // The request was made but no response was received
          this.error = 'No response from server. Please check if the backend is running and accessible.';
        } else {
          // Something happened in setting up the request that triggered an Error
          this.error = 'An unexpected error occurred while making the request.';
        }
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.customer-profile-view {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f4f7f6;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

h1 {
  color: #2c3e50;
  text-align: center;
  margin-bottom: 30px;
  font-size: 2.2em;
  font-weight: 600;
}

h2 {
  color: #34495e;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 10px;
  margin-top: 30px;
  margin-bottom: 20px;
  font-size: 1.6em;
}

h3 {
  color: #4a698c;
  margin-top: 15px;
  margin-bottom: 10px;
  font-size: 1.2em;
}

.profile-section {
  background-color: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 25px;
  margin-bottom: 25px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.profile-section p {
  margin-bottom: 8px;
  line-height: 1.6;
  color: #555;
}

.profile-section p strong {
  color: #333;
}

.offer-card, .event-card {
  background-color: #fdfdfd;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 18px;
  margin-bottom: 15px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}

.offer-card p, .event-card p {
  margin: 5px 0;
  font-size: 0.95em;
}

.loading-message, .error-message, .no-profile-message {
  text-align: center;
  padding: 25px;
  font-size: 1.2em;
  border-radius: 8px;
  margin-top: 30px;
}

.loading-message {
  color: #2196f3;
  background-color: #e3f2fd;
  border: 1px solid #bbdefb;
}

.error-message {
  color: #d32f2f;
  background-color: #ffebee;
  border: 1px solid #ef9a9a;
}

.no-profile-message {
  color: #f57c00;
  background-color: #fff3e0;
  border: 1px solid #ffcc80;
}
</style>