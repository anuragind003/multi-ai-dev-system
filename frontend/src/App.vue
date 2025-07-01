<template>
  <div class="p-4 font-sans bg-gray-50 min-h-screen">
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold text-gray-800 mb-2">Multi-AI Development System</h1>
      <p class="text-gray-600 mb-6">Interactive Workflow Control</p>

      <!-- Workflow Controls -->
      <div class="bg-white p-6 rounded-lg shadow-md mb-6">
        <h2 class="text-xl font-semibold mb-4">Start Workflow</h2>
        <textarea
          v-model="brdContent"
          rows="5"
          class="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500"
          placeholder="Enter your Business Requirements Document (BRD) here..."
        ></textarea>
        <button
          @click="startWorkflow"
          :disabled="workflowRunning"
          class="mt-4 px-6 py-2 bg-blue-600 text-white font-semibold rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          {{ workflowRunning ? "Running..." : "Start Resumable Workflow" }}
        </button>
      </div>

      <!-- Human Intervention Prompt -->
      <div
        v-if="needsHumanInput"
        class="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded-lg shadow-md mb-6"
      >
        <h3 class="font-bold text-lg mb-2">Human Intervention Required!</h3>
        <p class="mb-4">{{ humanPrompt.message }}</p>
        <pre class="bg-gray-800 text-white p-3 rounded-md text-sm overflow-x-auto mb-4">{{
          JSON.stringify(humanPrompt.data, null, 2)
        }}</pre>
        <div class="flex space-x-4">
          <button
            @click="sendResponse('approve')"
            class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          >
            Approve
          </button>
          <button
            @click="sendResponse('reject')"
            class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Reject
          </button>
        </div>
      </div>

      <!-- Live Log Stream -->
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h2 class="text-xl font-semibold mb-4">Live Event Log (Session: {{ sessionId }})</h2>
        <div class="bg-gray-900 text-white font-mono text-sm rounded-md p-4 h-96 overflow-y-auto">
          <div
            v-for="(log, index) in logs"
            :key="index"
            class="whitespace-pre-wrap mb-2 border-b border-gray-700 pb-2"
          >
            <span :class="getLogColor(log.type)">[{{ log.timestamp }}] [{{ log.type }}]</span>
            <pre class="overflow-x-auto">{{ log.content }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";

const brdContent = ref("");
const sessionId = ref(null);
const logs = ref([]);
const workflowRunning = ref(false);
const needsHumanInput = ref(false);
const humanPrompt = ref({});
let socket = null;

const connectWebSocket = () => {
  socket = new WebSocket("ws://localhost:8000/ws/agent-monitor");

  socket.onopen = () => {
    addLog({ type: "STATUS", content: "WebSocket Connected." });
  };

  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.event_type === "workflow_status" && message.data.status === "paused") {
      workflowRunning.value = true;
      needsHumanInput.value = true;
      humanPrompt.value = {
        message: message.data.message,
        data: message.data.data,
      };
      addLog({ type: "PAUSED", content: `Waiting for human input... ${message.data.message}` });
    } else {
      addLog({
        type: message.event_type || "INFO",
        content: JSON.stringify(message.data, null, 2),
      });

      if (message.event_type === "workflow_status" && message.data.status === "completed") {
        workflowRunning.value = false;
      }
    }
  };

  socket.onclose = () => {
    addLog({ type: "STATUS", content: "WebSocket Disconnected." });
    workflowRunning.value = false;
  };

  socket.onerror = (error) => {
    addLog({ type: "ERROR", content: `WebSocket Error: ${error}` });
    workflowRunning.value = false;
  };
};

const startWorkflow = async () => {
  if (!brdContent.value.trim()) {
    alert("Please enter a BRD.");
    return;
  }
  logs.value = [];
  workflowRunning.value = true;
  needsHumanInput.value = false;
  sessionId.value = `session_${Date.now()}`;

  try {
    const response = await fetch("http://localhost:8000/api/workflow/run_interactive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId.value,
        inputs: {
          [StateFields.BRD_CONTENT]: brdContent.value,
        },
      }),
    });
    const data = await response.json();
    if (data.status === "started") {
      addLog({ type: "START", content: `Workflow started with session ID: ${data.session_id}` });
    } else {
      throw new Error(data.message);
    }
  } catch (error) {
    addLog({ type: "ERROR", content: `Failed to start workflow: ${error.message}` });
    workflowRunning.value = false;
  }
};

const sendResponse = (decision) => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    addLog({ type: "ERROR", content: "WebSocket is not connected." });
    return;
  }
  const response = {
    type: "human_response",
    session_id: sessionId.value,
    decision: decision,
    payload: {}, // Add payload here if you allow edits
  };
  socket.send(JSON.stringify(response));
  needsHumanInput.value = false;
  humanPrompt.value = {};
  addLog({ type: "ACTION", content: `Sent response: ${decision}` });
};

const addLog = (log) => {
  const timestamp = new Date().toLocaleTimeString();
  logs.value.unshift({ ...log, timestamp });
};

const getLogColor = (type) => {
  switch (type) {
    case "PAUSED":
      return "text-yellow-400";
    case "ERROR":
      return "text-red-400";
    case "ACTION":
      return "text-cyan-400";
    case "STATUS":
    case "START":
      return "text-blue-400";
    default:
      return "text-green-400";
  }
};

onMounted(() => {
  connectWebSocket();
});

onUnmounted(() => {
  if (socket) {
    socket.close();
  }
});

const StateFields = {
  BRD_CONTENT: "brd_content",
};
</script>

<style scoped>
header {
  line-height: 1.5;
  max-height: 100vh;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
}

nav {
  width: 100%;
  font-size: 12px;
  text-align: center;
  margin-top: 2rem;
}

nav a.router-link-exact-active {
  color: var(--color-text);
}

nav a.router-link-exact-active:hover {
  background-color: transparent;
}

nav a {
  display: inline-block;
  padding: 0 1rem;
  border-left: 1px solid var(--color-border);
}

nav a:first-of-type {
  border: 0;
}

@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  .logo {
    margin: 0 2rem 0 0;
  }

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  }

  nav {
    text-align: left;
    margin-left: -1rem;
    font-size: 1rem;

    padding: 1rem 0;
    margin-top: 1rem;
  }
}
</style>
