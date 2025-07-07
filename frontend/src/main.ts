import "./styles/main.css";

import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import router from "./router";

const app = createApp(App);

app.use(createPinia());
app.use(router);

// Add debug utilities in development mode
if (import.meta.env.DEV) {
  import("./utils/debug").then(({ debugWorkflow }) => {
    console.log("Debug utilities loaded. Use window.debugWorkflow to debug workflow connections.");
  });
}

app.mount("#app");
