import { createApp } from 'vue';
import App from './App.vue';

// Create the Vue application instance
const app = createApp(App);

// Mount the application to the DOM element with id 'app'
// This assumes an index.html file exists with a div like <div id="app"></div>
app.mount('#app');