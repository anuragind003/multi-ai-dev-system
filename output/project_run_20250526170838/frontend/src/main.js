import { createApp } from 'vue';
import App from './App.vue';
import { createRouter, createWebHistory } from 'vue-router';

// Import components for different views/pages
// These components would typically be defined in separate .vue files
// within a 'views' directory (e.g., frontend/src/views/).
import Home from './views/Home.vue';
import AdminUpload from './views/AdminUpload.vue';
import MoengageDownload from './views/MoengageDownload.vue';
import DuplicateDownload from './views/DuplicateDownload.vue';
import UniqueDownload from './views/UniqueDownload.vue';
import ErrorDownload from './views/ErrorDownload.vue';
import DailyReports from './views/DailyReports.vue';
import CustomerView from './views/CustomerView.vue';

// Define application routes based on functional requirements and system design
const routes = [
  { path: '/', name: 'Home', component: Home },
  // FR35: Admin Portal for uploading customer details
  { path: '/admin/upload', name: 'AdminUpload', component: AdminUpload },
  // FR31: Screen for users to download Moengage format file
  { path: '/downloads/moengage', name: 'MoengageDownload', component: MoengageDownload },
  // FR32: Screen for users to download Duplicate Data File
  { path: '/downloads/duplicates', name: 'DuplicateDownload', component: DuplicateDownload },
  // FR33: Screen for users to download Unique Data File
  { path: '/downloads/unique', name: 'UniqueDownload', component: UniqueDownload },
  // FR34: Screen for users to download Error Excel file
  { path: '/downloads/errors', name: 'ErrorDownload', component: ErrorDownload },
  // FR39: Front-end for daily reports for data tally
  { path: '/reports/daily', name: 'DailyReports', component: DailyReports },
  // FR40: Front-end for customer-level view with stages
  { path: '/customers/:id', name: 'CustomerView', component: CustomerView, props: true },
];

// Create the router instance
const router = createRouter({
  history: createWebHistory(), // Use HTML5 History API for clean URLs
  routes, // Short for `routes: routes`
});

// Create the Vue application instance
const app = createApp(App);

// Use the router plugin with the application
app.use(router);

// Mount the application to the DOM element with id 'app'
app.mount('#app');

// Note: This file serves as the entry point for the Vue.js frontend.
// It sets up the main application instance and configures client-side routing.
// Actual data fetching and interaction with the Flask backend API endpoints
// (e.g., /admin/customer-data/upload, /campaigns/moengage-export)
// will be implemented within the individual Vue components (e.g., AdminUpload.vue, MoengageDownload.vue)
// using HTTP client libraries like Axios or the native Fetch API.