<template>
  <div class="space-y-4">
    <div v-if="logs.length > 0">
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="bg-slate-800/50 p-5 rounded-2xl shadow-lg border border-white/10"
      >
        <p class="font-mono text-xs text-gray-400">
          <span class="text-indigo-400">{{ log.timestamp }}</span>
          <span class="text-green-400"> [{{ log.agent }}]</span>
          <span class="text-cyan-400"> ({{ log.phase }})</span>
        </p>
        <p class="mt-2 text-gray-200">{{ log.message }}</p>
      </div>
    </div>
    <div
      v-else
      class="text-center py-16 bg-slate-800/50 rounded-2xl shadow-lg border border-white/10"
    >
      <p class="text-gray-400">> Waiting for workflow to start...</p>
      <div v-if="status === 'error' || !isConnected" class="mt-4 space-y-2">
        <p class="text-red-400 font-semibold">WebSocket not connected</p>
        <div class="text-xs text-gray-500 space-y-1">
          <p>Status: {{ status }}</p>
          <p>Connected: {{ isConnected }}</p>
          <p>Session ID: {{ sessionId || "None" }}</p>
          <p>Socket State: {{ socketState }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useWorkflowStore } from "@/stores/workflow";
import { storeToRefs } from "pinia";

interface LogEntry {
  timestamp: string;
  agent: string;
  phase: string;
  message: string;
}

// This is a placeholder as the new store doesn't have detailed logs yet.
// This can be expanded later to parse the raw websocket events.
const logs = computed<LogEntry[]>(() => {
  // Convert workflow events to log entries
  return workflowEvents.value.map((event, index) => ({
    timestamp: new Date(event.timestamp).toLocaleTimeString(),
    agent: getAgentFromEvent(event.event),
    phase: getPhaseFromEvent(event.event),
    message: getMessageFromEvent(event),
  }));
});

// Helper functions to extract meaningful data from events
const getAgentFromEvent = (eventType: string): string => {
  if (eventType.includes("brd_analysis")) return "BRD Analyst";
  if (eventType.includes("tech_stack")) return "Tech Stack Agent";
  if (eventType.includes("system_design")) return "System Designer";
  if (eventType.includes("database")) return "Database Agent";
  if (eventType.includes("backend")) return "Backend Agent";
  if (eventType.includes("frontend")) return "Frontend Agent";
  if (eventType.includes("integration")) return "Integration Agent";
  if (eventType.includes("code_generation")) return "Code Generator";
  if (eventType.includes("initialize")) return "System";
  if (eventType.includes("planning")) return "Plan Compiler";
  return "Workflow";
};

const getPhaseFromEvent = (eventType: string): string => {
  if (eventType.includes("brd_analysis")) return "Analysis";
  if (eventType.includes("tech_stack")) return "Planning";
  if (eventType.includes("system_design")) return "Design";
  if (eventType.includes("database")) return "Database";
  if (eventType.includes("backend")) return "Backend";
  if (eventType.includes("frontend")) return "Frontend";
  if (eventType.includes("integration")) return "Integration";
  if (eventType.includes("code_generation")) return "Generation";
  if (eventType.includes("initialize")) return "Setup";
  if (eventType.includes("planning")) return "Planning";
  return "Processing";
};

const getMessageFromEvent = (event: any): string => {
  if (event.message) return event.message;

  // Extract meaningful messages from event data
  if (event.event === "workflow_paused") {
    const approvalType = event.data?.approval_type || "approval";
    const displayName = event.data?.display_name || approvalType.replace(/_/g, " ").replace(/node$/, "").trim().replace(/\b\w/g, (c: string) => c.toUpperCase());
    
    // Add tech stack summary for tech stack approvals
    if (approvalType === "tech_stack_recommendation" && event.data?.data) {
      const data = event.data.data;
      if (data.frontend_options && data.backend_options && data.database_options) {
        const frontendCount = data.frontend_options.length;
        const backendCount = data.backend_options.length;
        const databaseCount = data.database_options.length;
        return `Human Review Required: ${displayName} (${frontendCount} frontend, ${backendCount} backend, ${databaseCount} database options)`;
      }
    }
    
    return `Human Review Required: ${displayName}`;
  }

  // Handle generic 'workflow_event' which encapsulates specific backend events
  if (event.event === "workflow_event" && event.data && typeof event.data === 'object') {
    const innerEvent = event.data.event;
    if (innerEvent) {
      if (innerEvent === "workflow_completed") return "Workflow completed successfully.";
      if (innerEvent.includes("brd_analysis_node")) return "Requirements Analysis completed.";
      if (innerEvent.includes("tech_stack_node")) {
        // Try to extract tech stack summary
        const techStackData = event.data?.tech_stack_recommendation_node?.tech_stack_result;
        if (techStackData && techStackData.selected_stack) {
          const selected = techStackData.selected_stack;
          return `Tech Stack Recommendation completed. Selected: ${selected.frontend_selection || 'N/A'} + ${selected.backend_selection || 'N/A'} + ${selected.database_selection || 'N/A'}`;
        }
        return "Tech Stack Recommendation completed.";
      }
      if (innerEvent.includes("system_design_node")) return "System Design completed.";
      if (innerEvent.includes("planning_node")) return "Implementation Planning completed.";
      if (innerEvent.includes("code_generation_node")) return "Code Generation initiated."; // or completed based on context
      
      // For other internal node events, try to make them readable
      const nodeName = Object.keys(event.data).find(key => key.includes("_node"));
      if (nodeName) {
        return `Node processing: ${nodeName.replace(/_/g, " ").replace(/node$/, "").trim()}`;
      }
      // Fallback for other workflow_event types with data
      return `Workflow event: ${innerEvent.replace(/_/g, " ")}`;
    }
    // Fallback if innerEvent is not found but there's other data
    const eventKeys = Object.keys(event.data || {});
    if (eventKeys.length > 0) {
      const mainKey = eventKeys[0];
      return `Updated: ${mainKey.replace(/_/g, " ")}`;
    }
  }

  if (event.event.endsWith("_node")) {
    return `Node processing: ${event.event.replace(/_node$/, "").replace(/_/g, " ")}`;
  }

  // Default generic message
  return `Event: ${event.event.replace(/_/g, " ")}`;
};
const workflowStore = useWorkflowStore();
const { status, isConnected, sessionId, socket, workflowEvents } = storeToRefs(workflowStore);

// Computed to show socket readyState in human-readable format
const socketState = computed(() => {
  if (!socket.value) return "No socket";
  switch (socket.value.readyState) {
    case WebSocket.CONNECTING:
      return "Connecting";
    case WebSocket.OPEN:
      return "Open";
    case WebSocket.CLOSING:
      return "Closing";
    case WebSocket.CLOSED:
      return "Closed";
    default:
      return "Unknown";
  }
});
</script>
