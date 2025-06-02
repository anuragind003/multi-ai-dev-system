<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios'; // Assuming axios is installed and configured in your project

const router = useRouter();

/**
 * Computed property to determine if the user is authenticated.
 * It checks for the presence of an 'authToken' in localStorage.
 *
 * Note: localStorage itself is not reactive. This computed property will
 * re-evaluate when its dependencies change (e.g., if `localStorage.getItem`
 * was wrapped in a reactive ref, or if the component re-renders due to route changes).
 * For a truly reactive global authentication state that updates across all components
 * and browser tabs, a dedicated state management library (like Pinia or Vuex)
 * is highly recommended. For this component, it will correctly reflect the state
 * upon initial load and after a logout action initiated from this component.
 */
const isAuthenticated = computed(() => {
  return !!localStorage.getItem('authToken');
});

/**
 * Handles the user logout process.
 * 1. Attempts to make an API call to the backend logout endpoint to invalidate the session/token.
 * 2. Clears the authentication token from localStorage regardless of the API call success/failure
 *    to ensure the client-side state reflects a logged-out user.
 * 3. Redirects the user to the login page.
 */
const handleLogout = async () => {
  try {
    const authToken = localStorage.getItem('authToken');
    if (authToken) {
      // Send the token to the backend for invalidation, if applicable.
      // The backend might use this to revoke the token or clear session data.
      await axios.post('/api/logout', {}, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });
    }

    // Clear the authentication token from localStorage.
    // This is crucial for client-side logout, even if the backend call fails.
    localStorage.removeItem('authToken');

    // Redirect the user to the login page after logout.
    router.push('/login');
  } catch (error) {
    console.error('Logout failed:', error);
    // In case of an API error during logout, still ensure client-side token is cleared.
    localStorage.removeItem('authToken');
    router.push('/login'); // Still redirect to login page.
    // Optionally, provide user feedback about the logout attempt failure.
    alert('Logout failed. Please try again or clear your browser data if issues persist.');
  }
};
</script>

<template>
  <nav class="navbar">
    <div class="navbar-brand">
      <!-- Application branding/logo, links to home page -->
      <router-link to="/" class="navbar-item">
        Task Tracker
      </router-link>
    </div>

    <div class="navbar-menu">
      <div class="navbar-start">
        <!-- Navigation link for tasks, visible only when authenticated -->
        <router-link v-if="isAuthenticated" to="/tasks" class="navbar-item">
          Tasks
        </router-link>
      </div>

      <div class="navbar-end">
        <!-- Navigation links for Login and Register, visible only when not authenticated -->
        <template v-if="!isAuthenticated">
          <router-link to="/login" class="navbar-item">
            Login
          </router-link>
          <router-link to="/register" class="navbar-item">
            Register
          </router-link>
        </template>

        <!-- Logout button, visible only when authenticated -->
        <button v-if="isAuthenticated" @click="handleLogout" class="navbar-item logout-button">
          Logout
        </button>
      </div>
    </div>
  </nav>
</template>

<style scoped>
/* Basic styling for the Navbar component */
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #333; /* Dark background for the navbar */
  padding: 1rem 2rem;
  color: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Subtle shadow for depth */
}

.navbar-brand .navbar-item {
  font-size: 1.5rem;
  font-weight: bold;
  color: white;
  text-decoration: none; /* Remove underline from links */
}

.navbar-menu {
  display: flex;
  flex-grow: 1; /* Allows the menu to take available space */
  justify-content: space-between;
  align-items: center;
}

.navbar-start,
.navbar-end {
  display: flex;
  align-items: center;
}

.navbar-item {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  transition: background-color 0.3s ease; /* Smooth transition for hover effects */
  border-radius: 4px; /* Slightly rounded corners for items */
}

.navbar-item:hover {
  background-color: #555; /* Darker background on hover */
}

/* Styling for the logout button to differentiate it */
.logout-button {
  background-color: #dc3545; /* Red color for logout button */
  color: white;
  border: none;
  cursor: pointer;
  padding: 0.5rem 1rem;
  margin-left: 1rem; /* Space from other navigation items */
  transition: background-color 0.3s ease;
  border-radius: 4px;
}

.logout-button:hover {
  background-color: #c82333; /* Darker red on hover */
}

/* Styling for the active router link, provided by Vue Router */
.navbar-item.router-link-active {
  background-color: #007bff; /* Blue background for the active link */
}

/* Responsive adjustments for smaller screens */
@media (max-width: 768px) {
  .navbar {
    flex-direction: column; /* Stack items vertically */
    align-items: flex-start;
    padding: 1rem;
  }

  .navbar-menu {
    flex-direction: column;
    width: 100%; /* Full width for menu on small screens */
    margin-top: 1rem;
  }

  .navbar-start,
  .navbar-end {
    flex-direction: column;
    width: 100%;
    align-items: flex-start;
  }

  .navbar-item,
  .logout-button {
    width: 100%; /* Full width for individual items */
    text-align: left;
    margin: 0.25rem 0; /* Vertical spacing between items */
  }
}
</style>