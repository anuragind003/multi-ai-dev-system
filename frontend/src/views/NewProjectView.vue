<!-- /src/views/NewProjectView.vue -->
<template>
  <div class="bg-slate-900 min-h-full -m-4 sm:-m-6 lg:-m-8 p-4 sm:p-6 lg:p-8">
    <div
      class="max-w-4xl mx-auto bg-slate-800/50 p-8 rounded-2xl shadow-2xl border border-white/10"
    >
      <div class="text-center mb-8">
        <h1 class="text-3xl font-extrabold text-white sm:text-4xl mb-4">Create New Project</h1>
        <p class="mt-2 text-lg text-gray-400">
          Paste your Business Requirements Document (BRD) below or upload a file to get started.
        </p>
      </div>

      <!-- WebSocket Status Indicator -->
      <div class="mb-6 flex items-center justify-center p-3 rounded-lg border" :class="statusClass">
        <div class="flex items-center">
          <div class="w-3 h-3 rounded-full mr-3" :class="dotClass"></div>
          <span class="text-sm font-medium">{{ statusText }}</span>
        </div>
      </div>

      <form @submit.prevent="startBuild" class="space-y-6">
        <div>
          <label for="brd" class="block text-sm font-medium text-gray-300 mb-2">
            Business Requirements Document
          </label>
          <textarea
            id="brd"
            v-model="requirements"
            rows="12"
            class="w-full p-4 border border-slate-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 transition bg-slate-900 text-gray-200 placeholder-gray-500"
            placeholder="Paste your full BRD content here..."
            :disabled="isProcessing"
          ></textarea>
        </div>

        <div class="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <!-- File Upload Button -->
          <button
            type="button"
            class="w-full sm:w-auto inline-flex items-center justify-center px-4 py-2 border border-slate-600 text-sm font-medium rounded-lg text-gray-300 bg-slate-700 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 focus:ring-offset-slate-900 disabled:opacity-50 transition"
            :disabled="isProcessing"
          >
            <svg class="w-5 h-5 mr-2 -ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              ></path>
            </svg>
            Upload File
          </button>

          <!-- Start Build Button -->
          <button
            type="submit"
            class="w-full sm:w-auto inline-flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-lg shadow-lg text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition hover:scale-105"
            :disabled="isProcessing || requirements.length === 0 || !isConnected"
          >
            <svg
              v-if="isProcessing"
              class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            {{ isProcessing ? "Processing..." : "Start Build" }}
          </button>
        </div>
      </form>
    </div>
    <AppFooter class="-mx-4 sm:-mx-6 lg:-mx-8" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import AppFooter from "@/components/AppFooter.vue";
import { useWorkflowSocket } from "@/composables/useWorkflowSocket";

// Reactive state for the form
const requirements = ref("");
const isProcessing = ref(false);
const httpHealthStatus = ref<boolean | null>(null);
const router = useRouter();

// Import the global connection status from useWorkflowSocket
// The useWorkflowSocket manages a singleton WebSocket connection to /ws/agent-monitor
const { startWorkflow } = useWorkflowSocket(ref(""));

// Import the global isConnected directly
import { isConnected } from "@/composables/useWorkflowSocket";

// --- Enhanced Health Check System ---
const checkServerHealth = async (): Promise<boolean> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000); // 5-second timeout

  try {
    const response = await fetch("/api/health", {
      method: "GET",
      signal: controller.signal, // Attach the AbortController signal
    });
    return response.ok;
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      console.warn("HTTP health check timed out.");
    } else {
      console.warn("HTTP health check failed:", error);
    }
    return false;
  } finally {
    clearTimeout(timeoutId); // Clear the timeout
  }
};

// Combined connection status (WebSocket + HTTP health)
const isServerHealthy = computed(() => {
  // Primary: WebSocket connection for real-time status
  // Fallback: HTTP health check for basic connectivity
  return isConnected.value || httpHealthStatus.value === true;
});

// --- WebSocket Status ---
const statusText = computed(() => {
  if (isProcessing.value) return "Processing...";
  if (isConnected.value) return "Connected to server";
  if (httpHealthStatus.value === true) return "Server responsive (limited connectivity)";
  if (httpHealthStatus.value === false) return "Server not responding";
  return "Checking server status...";
});

const statusClass = computed(() => {
  if (isServerHealthy.value) return "bg-green-900/50 border-green-500/50 text-green-300";
  if (httpHealthStatus.value === false) return "bg-red-900/50 border-red-500/50 text-red-300";
  return "bg-yellow-900/50 border-yellow-500/50 text-yellow-300";
});

const dotClass = computed(() => {
  if (isConnected.value) return "bg-green-500";
  if (httpHealthStatus.value === true) return "bg-yellow-500";
  if (httpHealthStatus.value === false) return "bg-red-500";
  return "bg-yellow-500 animate-pulse";
});

// Define the interval variable in the setup scope
let healthCheckInterval: number | undefined;

// Initialize health checks on mount
onMounted(async () => {
  httpHealthStatus.value = await checkServerHealth();

  // Periodically check HTTP health if WebSocket is down
  healthCheckInterval = window.setInterval(async () => {
    if (!isConnected.value) {
      httpHealthStatus.value = await checkServerHealth();
    }
  }, 10000); // Check every 10 seconds
});

// Cleanup interval on component unmount
onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval);
  }
});

// Handler for the form submission
const startBuild = async () => {
  if (!requirements.value) {
    alert("Please enter some requirements before starting the build.");
    return;
  }

  // Enhanced connectivity check
  if (!isServerHealthy.value) {
    alert("Server is not responding. Please check your connection and try again.");
    return;
  }

  isProcessing.value = true;
  startWorkflow(requirements.value); // Clear logs and indicate start

  try {
    const response = await fetch("/api/workflow/run_interactive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        inputs: {
          brd_content: requirements.value,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (result.status === "started" && result.session_id) {
      // Navigate to the monitor page with the session ID
      router.push({ name: "workflow", params: { sessionId: result.session_id } });
    } else {
      throw new Error("Failed to start interactive workflow session.");
    }
  } catch (error) {
    console.error("Error starting build:", error);
    alert("Failed to start the build process. Please check the console for details.");
  } finally {
    isProcessing.value = false;
  }
};
</script>
