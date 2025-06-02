import { createApp } from 'vue';
import App from './App.vue';
import router from './router'; // Import the Vue Router instance
import store from './store';   // Import the Vuex store instance

/**
 * The main entry point for the Vue.js application.
 * This file initializes the Vue application, registers global plugins,
 * and mounts the application to the DOM.
 */

// Create the Vue application instance using the root component (App.vue).
const app = createApp(App);

// Register Vue Router for client-side navigation.
app.use(router);

// Register Vuex store for centralized state management.
app.use(store);

// Mount the application to the DOM element with ID 'app'.
app.mount('#app');

// Optional: Global error handler for Vue components.
// app.config.errorHandler = (err, vm, info) => {
//   console.error('Vue Error:', err, info);
//   // Consider sending errors to an error tracking service (e.g., Sentry, Bugsnag).
// };

// Optional: Define global properties accessible via `app.config.globalProperties`.
// For example, to expose an API base URL:
// app.config.globalProperties.$apiBaseUrl = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5000/api';