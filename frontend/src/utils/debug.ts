/**
 * Debug utilities for the workflow system
 * These can be accessed from the browser console for debugging
 */

import { useWorkflowStore } from "@/stores/workflow";

// Make debug functions available globally
declare global {
  interface Window {
    debugWorkflow: {
      getConnectionInfo: () => any;
      testConnection: (sessionId: string) => void;
      reconnect: () => void;
    };
  }
}

// Debug utilities
export const debugWorkflow = {
  getConnectionInfo() {
    const store = useWorkflowStore();
    return store.getConnectionInfo();
  },

  testConnection(sessionId: string) {
    const store = useWorkflowStore();
    console.log("Testing connection with session ID:", sessionId);
    store.setSessionId(sessionId);
  },

  reconnect() {
    const store = useWorkflowStore();
    console.log("Reconnecting WebSocket...");
    store.connectWebSocket();
  },
};

// Make available globally for console debugging
if (typeof window !== "undefined") {
  window.debugWorkflow = debugWorkflow;
}
