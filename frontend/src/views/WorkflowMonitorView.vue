<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">Workflow Monitor</h1>
      <router-link
        to="/"
        class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
      >
        New Project
      </router-link>
    </div>

    <div class="bg-white p-6 rounded-lg shadow-md">
      <div class="flex items-center space-x-4 mb-4">
        <h2 class="text-xl font-semibold">Status:</h2>
        <span :class="statusClass" class="px-3 py-1 rounded-full text-sm font-medium">
          {{ workflow.status.toUpperCase() }}
        </span>
      </div>

      <div
        v-if="workflow.error"
        class="bg-red-100 border-l-4 border-red-500 text-red-700 p-4"
        role="alert"
      >
        <p class="font-bold">An Error Occurred</p>
        <p>{{ workflow.error }}</p>
      </div>

      <h3 class="text-lg font-semibold mt-6 mb-2">Live Logs:</h3>
      <div
        ref="logsContainer"
        class="bg-gray-900 text-white font-mono text-sm rounded-lg p-6 h-96 overflow-y-auto"
      >
        <div v-for="(log, index) in workflow.logs" :key="index" class="flex">
          <span class="text-gray-500 mr-4 flex-shrink-0">{{ formatTimestamp(log.timestamp) }}</span>
          <span :class="getPhaseClass(log.phase)" class="w-32 flex-shrink-0">{{ log.phase }}</span>
          <span class="text-cyan-400 w-48 flex-shrink-0">{{ log.agent }}</span>
          <span class="flex-grow">{{ log.message }}</span>
        </div>
        <div v-if="workflow.logs.length === 0">
          <p>&gt; Waiting for real-time logs from the server...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from "vue";
import { useWorkflowStore } from "@/stores/workflow";

const workflow = useWorkflowStore();
const logsContainer = ref<HTMLElement | null>(null);

const statusClass = computed(() => {
  switch (workflow.status) {
    case "running":
      return "bg-blue-100 text-blue-800 animate-pulse";
    case "completed":
      return "bg-green-100 text-green-800";
    case "error":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
});

const getPhaseClass = (phase: string) => {
  if (phase.includes("Error")) return "text-red-400";
  if (phase.includes("Success")) return "text-green-400";
  return "text-yellow-400";
};

const formatTimestamp = (isoString: string) => {
  return new Date(isoString).toLocaleTimeString();
};

const scrollToBottom = () => {
  nextTick(() => {
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight;
    }
  });
};

watch(
  () => workflow.logs,
  () => {
    scrollToBottom();
  },
  { deep: true }
);

onMounted(() => {
  scrollToBottom();
});

onUnmounted(() => {
  // Disconnect from WebSocket when the user navigates away
  workflow.disconnectWebSocket();
});
</script>
