import { defineStore } from "pinia";
import axios from "axios";

const API_BASE_URL = "http://localhost:8001";
const WS_BASE_URL = "ws://localhost:8001";

export interface LogEntry {
  timestamp: string;
  message: string;
  agent: string;
  phase: string;
  type?: string;
  event_type?: string;
  data?: any;
}

export const useWorkflowStore = defineStore("workflow", {
  state: () => ({
    sessionId: null as string | null,
    status: "idle" as "idle" | "running" | "success" | "error" | "completed",
    logs: [] as LogEntry[],
    finalResult: null as any,
    error: null as string | null,
    socket: null as WebSocket | null,
  }),

  actions: {
    async startWorkflow(brdContent: string) {
      this.resetState();
      this.status = "running";

      try {
        const response = await axios.post(`${API_BASE_URL}/api/workflow`, {
          input: {
            brd_content: brdContent,
          },
        });

        this.sessionId = response.data.output?.workflow_id || `run-${Date.now()}`;
        this.connectWebSocket();

        console.log("Workflow initiated with session ID:", this.sessionId);
      } catch (err: any) {
        this.status = "error";
        this.error = err.response?.data?.detail || err.message || "An unknown error occurred.";
        console.error("Workflow failed to start:", err);
      }
    },

    connectWebSocket() {
      if (this.socket) {
        this.socket.close();
      }

      this.socket = new WebSocket(`${WS_BASE_URL}/ws/agent-monitor`);

      this.socket.onopen = () => {
        console.log("WebSocket connected with server.");
      };

      this.socket.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.session_id && message.session_id !== this.sessionId) {
          return;
        }

        if (message.type === "connection_established") {
          this.addLog({
            timestamp: message.timestamp,
            message: message.message,
            agent: "System",
            phase: "Connection",
          });
        } else if (message.type === "agent_event") {
          const eventData = message.data;
          let logEntry: LogEntry = {
            timestamp: message.timestamp,
            agent: eventData.agent || "System",
            phase: message.event_type,
            message: eventData.message || eventData.error || JSON.stringify(eventData),
          };
          this.addLog(logEntry);

          if (message.event_type === "workflow_status") {
            this.status = eventData.status;
            if (eventData.status === "completed" || eventData.status === "error") {
              this.disconnectWebSocket();
            }
          }
          if (message.event_type === "error") {
            this.error = eventData.error;
            this.status = "error";
            this.disconnectWebSocket();
          }
        }
      };

      this.socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.error = "A WebSocket connection error occurred.";
        this.status = "error";
      };

      this.socket.onclose = () => {
        console.log("WebSocket disconnected from server.");
        this.socket = null;
        if (this.status === "running") {
          this.status = "idle";
        }
      };
    },

    disconnectWebSocket() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
    },

    addLog(log: LogEntry) {
      this.logs.push(log);
    },

    resetState() {
      this.disconnectWebSocket();
      this.sessionId = null;
      this.status = "idle";
      this.logs = [];
      this.finalResult = null;
      this.error = null;
    },
  },
});
