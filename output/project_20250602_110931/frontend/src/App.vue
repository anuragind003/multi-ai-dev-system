<template>
  <div id="app">
    <header class="app-header">
      <nav>
        <router-link to="/" class="app-title">Simple Task Tracker</router-link>
        <div class="nav-links">
          <template v-if="isAuthenticated">
            <router-link to="/tasks">My Tasks</router-link>
            <button @click="logout" class="logout-button">Logout</button>
          </template>
          <template v-else>
            <router-link to="/login">Login</router-link>
            <router-link to="/register">Register</router-link>
          </template>
        </div>
      </nav>
    </header>
    <main class="app-main">
      <!-- Vue Router will render the component corresponding to the current route here -->
      <router-view />
    </main>
    <footer class="app-footer">
      <p>&copy; 2024 Simple Task Tracker. All rights reserved.</p>
    </footer>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'; // Import Vuex helpers for state management

export default {
  name: 'App',
  computed: {
    // Map the 'isAuthenticated' getter from the Vuex 'auth' module
    ...mapGetters('auth', ['isAuthenticated']),
  },
  methods: {
    // Map the 'logout' action from the Vuex 'auth' module
    ...mapActions('auth', ['logout']),
    
    /**
     * Handles the user logout process.
     * Calls the Vuex logout action and redirects to the login page.
     */
    async logout() {
      try {
        await this.$store.dispatch('auth/logout'); // Dispatch the logout action
        this.$router.push('/login'); // Redirect to login page after successful logout
      } catch (error) {
        // Log any errors during logout, though the Vuex action should handle most
        console.error('Logout failed:', error);
        // Optionally, display a user-friendly error message
        alert('Failed to log out. Please try again.');
      }
    }
  },
  created() {
    // On application load, attempt to load the user from local storage
    // This helps maintain login state across page refreshes
    this.$store.dispatch('auth/loadUserFromLocalStorage');
  }
};
</script>

<style>
/* Basic global styles for the application */
:root {
  --primary-color: #4CAF50; /* Green */
  --primary-dark-color: #45a049;
  --secondary-color: #f44336; /* Red */
  --background-color: #f0f2f5;
  --text-color: #333;
  --header-bg-color: #2c3e50; /* Dark blue/grey */
  --header-text-color: #ecf0f1; /* Light grey */
  --border-color: #ddd;
  --box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

body {
  margin: 0;
  font-family: 'Arial', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: var(--background-color);
  color: var(--text-color);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  width: 100%;
}

.app-header {
  background-color: var(--header-bg-color);
  color: var(--header-text-color);
  padding: 15px 20px;
  box-shadow: var(--box-shadow);
}

.app-header nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.app-title {
  font-size: 1.8em;
  font-weight: bold;
  color: var(--header-text-color);
  text-decoration: none;
}

.nav-links a, .nav-links button {
  color: var(--header-text-color);
  text-decoration: none;
  margin-left: 20px;
  padding: 8px 12px;
  border-radius: 5px;
  transition: background-color 0.3s ease;
  font-size: 1em;
  cursor: pointer;
}

.nav-links a:hover, .nav-links button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.nav-links .router-link-exact-active {
  background-color: rgba(255, 255, 255, 0.2);
}

.logout-button {
  background: none;
  border: 1px solid var(--header-text-color);
  color: var(--header-text-color);
  padding: 8px 12px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.logout-button:hover {
  background-color: var(--secondary-color);
  border-color: var(--secondary-color);
}

.app-main {
  flex-grow: 1; /* Allows the main content area to take up available space */
  padding: 20px;
  max-width: 1200px;
  margin: 20px auto;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: var(--box-shadow);
}

.app-footer {
  background-color: var(--header-bg-color);
  color: var(--header-text-color);
  text-align: center;
  padding: 15px 20px;
  margin-top: auto; /* Pushes the footer to the bottom */
  box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
}

/* General button styles */
button {
  background-color: var(--primary-color);
  color: white;
  padding: 10px 15px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.3s ease;
}

button:hover {
  background-color: var(--primary-dark-color);
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

/* General form input styles */
input[type="text"],
input[type="email"],
input[type="password"],
textarea {
  width: 100%;
  padding: 10px;
  margin-bottom: 15px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  box-sizing: border-box; /* Ensures padding doesn't increase width */
  font-size: 1em;
}

input[type="text"]:focus,
input[type="email"]:focus,
input[type="password"]:focus,
textarea:focus {
  border-color: var(--primary-color);
  outline: none;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

/* Error message styling */
.error-message {
  color: var(--secondary-color);
  font-size: 0.9em;
  margin-top: -10px;
  margin-bottom: 10px;
}
</style>