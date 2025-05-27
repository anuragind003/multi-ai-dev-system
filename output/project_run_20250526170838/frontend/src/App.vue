<template>
  <div id="app">
    <header class="app-header">
      <nav>
        <router-link to="/" class="nav-link">Home</router-link>
        <router-link to="/upload" class="nav-link">Upload Data</router-link>
        <router-link to="/downloads" class="nav-link">Downloads</router-link>
        <router-link to="/reports" class="nav-link">Reports</router-link>
        <!-- More navigation links can be added here as features expand -->
      </nav>
    </header>
    <main class="app-main">
      <router-view/>
    </main>
  </div>
</template>

<script>
// App.vue serves as the root component for the Vue.js application.
// Its primary role is to define the overall layout and integrate Vue Router
// to manage navigation between different views/pages of the application.
// Specific business logic and API interactions are handled within child components
// that are rendered by <router-view>.

export default {
  name: 'App',
  // No specific data, methods, or lifecycle hooks are typically needed
  // directly within the root App component itself, as it mainly orchestrates
  // the layout and routing.
}
</script>

<style>
/* Basic global styles for the application */
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin: 0; /* Reset default body margin */
  display: flex;
  flex-direction: column;
  min-height: 100vh; /* Ensure the app takes full viewport height */
  background-color: #f8f8f8; /* Light background for the whole app */
}

.app-header {
  background-color: #42b983; /* A pleasant green, often associated with Vue */
  padding: 15px 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  color: white;
}

.app-header nav {
  display: flex;
  justify-content: center;
  gap: 25px; /* Space between navigation links */
}

.nav-link {
  font-weight: bold;
  color: #ffffff; /* White text for links */
  text-decoration: none;
  padding: 8px 15px;
  border-radius: 5px;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.nav-link:hover {
  background-color: #368a6a; /* Slightly darker green on hover */
}

/* Style for the active route link */
.nav-link.router-link-exact-active {
  background-color: #368a6a;
  box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.2);
}

.app-main {
  flex-grow: 1; /* Allows the main content area to expand and fill available space */
  padding: 20px;
  max-width: 1200px; /* Max width for content to prevent it from stretching too wide */
  margin: 20px auto; /* Center the main content area */
  background-color: #ffffff; /* White background for content area */
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
}

/* Basic reset for body margin/padding */
body {
  margin: 0;
  padding: 0;
}
</style>