import { ref, onUnmounted, onMounted, readonly, type Ref } from "vue";
import type {
  WebSocketMessage,
  WebSocketMessageTypes,
  AgentEventMessage,
  WorkflowStatusMessage,
  WorkflowPausedMessage,
  ErrorMessage,
  HumanResponseMessage,
} from "../types/websocket-schema";

/**
 * SECONDARY WEBSOCKET - Global Server Health Monitoring
 *
 * This composable manages the SECONDARY WebSocket connection for global server monitoring.
 * WebSocket URL: /ws/agent-monitor
 * Purpose: Server connectivity checks, global health monitoring, general system status
 *
 * For session-specific workflow events, use the PRIMARY WebSocket in workflow.ts store.
 * WebSocket URL: /api/workflow/stream/{sessionId}
 *
 * Both WebSockets serve distinct purposes:
 * - This one: "Is the server alive and responsive?"
 * - Primary one: "What's happening with my specific workflow?"
 */

interface LogEvent {
  timestamp: string;
  event_type?: string;
  [key: string]: any;
}

// --- Singleton WebSocket Manager ---
let ws: WebSocket | null = null;
const logs = ref<LogEvent[]>([]);
const isConnected = ref(false);
const interruptPayload = ref<any>(null);
const pausedAtNode: Ref<string | string[] | null> = ref(null);
const socketErrors = ref<ErrorMessage[]>([]);
const apiVersion = ref<string | null>(null);

const sendMessage = (message: Partial<WebSocketMessage>) => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error("WebSocket not connected. Cannot send message.");
    return;
  }

  try {
    ws.send(JSON.stringify(message));
  } catch (error) {
    console.error("Failed to send WebSocket message:", error);
  }
};

const connect = () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    isConnected.value = true;
    return;
  }

  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/agent-monitor`);

  ws.onopen = () => {
    isConnected.value = true;
    console.log("WebSocket connection established.");

    // Request health check upon connection
    sendMessage({
      type: "health_check_request",
    });
  };

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data) as WebSocketMessageTypes;

      // Log all incoming messages for debugging
      console.debug("WebSocket message received:", msg.type || msg.event, msg);

      if (msg.type === "error") {
        console.error("WebSocket error from server:", (msg as ErrorMessage).error);
        socketErrors.value.push(msg as ErrorMessage);
        return;
      }

      if (msg.type === "health_check") {
        console.log("Health check received:", msg);
        apiVersion.value = (msg as any).api_version;
        return;
      }

      if (msg.event === "on_chain_stream" && (msg as any).data?.chunk?.__interrupt__) {
        const interruptData = (msg as any).data.chunk.__interrupt__;
        console.log("Workflow interrupted. Current state:", interruptData);
        // This interrupt often doesn't have the full payload, so we rely on workflow_paused
        if (interruptData && Object.keys(interruptData).length > 0) {
            interruptPayload.value = interruptData;
        }
      }

      if (msg.event === "workflow_paused") {
        const pausedMsg = msg as WorkflowPausedMessage;
        console.log("Workflow paused at:", pausedMsg.data.paused_at);
        pausedAtNode.value = pausedMsg.data.paused_at;

        // Generic handler for ANY human approval node.
        // The backend payload should contain 'details' and 'current_node'.
        if (pausedMsg.data.details && pausedMsg.data.current_node) {
          console.log(`Setting interrupt payload for approval at: ${pausedMsg.data.current_node}`);
          interruptPayload.value = {
            ...pausedMsg.data, // Spread all data from the backend
            options: ["proceed", "revise", "end"], // Ensure options are always present
          };
          console.log("Interrupt payload set:", interruptPayload.value);
        } else {
          console.warn("Received a 'workflow_paused' event, but it was missing the expected 'details' and 'current_node' properties. The UI may not update correctly.", pausedMsg.data);
        }
      }

      logs.value.push({ ...msg, timestamp: new Date().toISOString() });
    } catch (e) {
      console.error("Failed to parse WebSocket message:", e);
    }
  };

  ws.onclose = () => {
    isConnected.value = false;
    console.log("WebSocket connection closed.");
    ws = null;
    interruptPayload.value = null;
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
    isConnected.value = false;
    ws = null;
  };
};

// Automatically connect on module load
connect();

// Export the global connection status so other components can use it
export { isConnected };

// --- Composable ---
export function useWorkflowSocket(sessionId: Ref<string>) {
  const sendHumanResponse = async (
    sessionId: string,
    decision: "proceed" | "revise" | "end",
    payload: { comments?: string; [key: string]: any } = {}
  ) => {
    if (!sessionId) {
      console.error("Cannot send human response without a session ID.");
      return;
    }

    try {
      // Structure the payload to match what the backend expects
      const requestBody: HumanResponseMessage = {
        decision: decision,
        feedback: payload,
      };

      console.log("Sending human decision:", requestBody);

      const response = await fetch(`/api/workflow/resume/${sessionId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API call failed with status: ${response.status} - ${errorText}`);
      }

      const responseData = await response.json();
      console.log(`Successfully sent human decision: ${decision}`, responseData);

      interruptPayload.value = null;

      return responseData;
    } catch (error) {
      console.error("Error sending human response:", error);
      throw error; // Re-throw so the UI can handle it
    }
  };

  const startWorkflow = (brd: string) => {
    // This is a placeholder. In a real app, you'd make an HTTP request
    // and the backend would start sending WebSocket messages for that session.
    // For now, we'll just log it.
    console.log("Starting workflow for BRD:", brd);
    logs.value = []; // Clear previous logs
  };

  return {
    logs: readonly(logs),
    isConnected: readonly(isConnected),
    interruptPayload: readonly(interruptPayload),
    pausedAtNode: readonly(pausedAtNode),
    sendHumanResponse,
    startWorkflow,
  };
}
