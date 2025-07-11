import { defineStore } from "pinia";
import axios from "axios";

const API_BASE_URL = "http://localhost:8001";
const WS_BASE_URL = "ws://localhost:8001";

/**
 * WEBSOCKET ARCHITECTURE OVERVIEW:
 *
 * This store manages the PRIMARY WebSocket connection for session-specific workflow events.
 * WebSocket URL: /api/workflow/stream/{sessionId}
 * Purpose: Real-time workflow progress, human approval requests, and completion events
 *
 * There is also a SECONDARY WebSocket (in useWorkflowSocket.ts):
 * WebSocket URL: /ws/agent-monitor
 * Purpose: Global server health monitoring and connectivity checks
 *
 * Both WebSockets serve distinct purposes and should be maintained separately.
 */

export interface ApprovalData {
  session_id: string;
  approval_type: string; // The stage type (e.g., 'brd_analysis')
  step_name: string; // The specific node name (e.g., 'human_approval_brd_node')
  display_name: string; // Human-readable name for the step
  approval_data: any;
  message: string;
  project_name?: string;
  data?: any; // Additional data field for complex approval data
}

export interface WorkflowEvent {
  timestamp: string;
  event: string;
  data: any;
  message?: string;
}

export const useWorkflowStore = defineStore("workflow", {
  state: () => ({
    sessionId: null as string | null,
    status: "idle" as "idle" | "starting" | "running" | "paused" | "completed" | "error",
    socket: null as WebSocket | null,
    humanApprovalRequest: null as ApprovalData | null,
    completedStages: {} as Record<string, any>,
    projectName: "" as string,
    error: null as string | null,
    isConnected: false,
    workflowEvents: [] as WorkflowEvent[],
  }),

  actions: {
    async startWorkflow(brdContent: string) {
      this.resetState();
      this.status = "starting";

      try {
        const response = await axios.post(`${API_BASE_URL}/api/workflow/run_interactive`, {
          inputs: { brd_content: brdContent },
        });

        this.sessionId = response.data.session_id;
        if (this.sessionId) {
          this.status = "running";
          this.connectWebSocket();
          console.log("Workflow initiated with session ID:", this.sessionId);
        } else {
          throw new Error("Failed to get session ID from server.");
        }
      } catch (err: any) {
        this.status = "error";
        this.error = err.response?.data?.detail || err.message || "An unknown error occurred.";
        console.error("Workflow failed to start:", err);
      }
    },

    connectWebSocket() {
      if (this.socket) this.socket.close();

      if (!this.sessionId) {
        console.error("Cannot connect WebSocket without a session ID.");
        this.status = "error";
        this.error = "Attempted to connect WebSocket without a session ID.";
        this.isConnected = false;
        return;
      }

      const wsUrl = `${WS_BASE_URL}/api/workflow/stream/${this.sessionId}`;
      console.log(`Attempting to connect to WebSocket: ${wsUrl}`);

      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log("Workflow WebSocket connected successfully.");
        this.isConnected = true;
      };
      this.socket.onclose = (event) => {
        console.log("Workflow WebSocket disconnected.", event.code, event.reason);
        this.isConnected = false;
      };
      this.socket.onerror = (error) => {
        console.error("Workflow WebSocket error:", error);
        this.status = "error";
        this.error = "A WebSocket connection error occurred.";
        this.isConnected = false;
      };
      this.socket.onmessage = this.handleWebSocketMessage;
    },

    disconnectWebSocket() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
      this.isConnected = false;
    },

    handleWebSocketMessage(event: MessageEvent) {
      try {
        const payload = JSON.parse(event.data);

        // Enhanced logging for debugging
        console.log("=== WebSocket Message Received ===");
        console.log("Raw payload:", payload);
        console.log("Payload type:", payload.type);
        console.log("Payload event:", payload.event);
        console.log("Payload status:", payload.status);

        if (payload.data) {
          console.log("Payload data keys:", Object.keys(payload.data));
          if (payload.data.payload) {
            console.log(
              "Nested payload found in data.payload with keys:",
              Object.keys(payload.data.payload)
            );
          }
        }

        if (payload.data?.session_id && payload.data.session_id !== this.sessionId) {
          console.log(
            `Ignoring message for different session: ${payload.data.session_id} !== ${this.sessionId}`
          );
          return;
        }

        // Add all workflow events to the events array
        const workflowEvent: WorkflowEvent = {
          timestamp: new Date().toISOString(),
          event: payload.event || payload.status || "unknown",
          data: payload.data || payload.payload,
          message: payload.message,
        };
        this.workflowEvents.push(workflowEvent);

        // Handle the new human approval format
        if (payload.status === "human_approval_required" && payload.payload) {
          console.log("Processing human_approval_required format");
          this.handleHumanApprovalRequired(payload.payload, payload.session_id);
        }
        // Handle specific events (legacy format)
        else if (payload.event === "workflow_paused") {
          console.log("Processing workflow_paused format");
          this.handleWorkflowPaused(payload.data);
        } else if (payload.event === "workflow_completed") {
          console.log("Processing workflow_completed");
          this.status = "completed";
          // Mark the last completed stage if available
          if (payload.data?.current_approved_stage) {
            this.completedStages[payload.data.current_approved_stage] = true;
          }
          this.disconnectWebSocket();
        } else if (payload.event === "error") {
          console.log("Processing workflow error");
          this.status = "error";
          this.error = payload.data?.error || "An unknown workflow error occurred.";
          this.disconnectWebSocket();
        } else if (payload.event === "workflow_event") {
          console.log("Processing general workflow_event");
          // General workflow events (node completions, progress updates, etc.)
          this.status = "running";

          // Mark stages as completed when nodes finish
          if (payload.data) {
            // Enhanced node completion mapping with multiple possible keys
            const nodeCompletionMap = {
              brd_analysis_node: "brd_analysis",
              tech_stack_recommendation_node: "tech_stack_recommendation",
              system_design_node: "system_design",
              planning_node: "implementation_plan",
              unified_planning_node: "implementation_plan",
              code_generation_node: "code_generation",
              unified_code_generation_dispatcher_node: "code_generation",
            };

            // Also check for state field completions
            const stateFieldCompletionMap = {
              requirements_analysis: "brd_analysis",
              tech_stack_recommendation: "tech_stack_recommendation",
              system_design: "system_design",
              implementation_plan: "implementation_plan",
              code_generation_result: "code_generation",
            };

            // Find completed nodes in the event data keys
            for (const eventKey of Object.keys(payload.data)) {
              if (eventKey in nodeCompletionMap) {
                const stageId = nodeCompletionMap[eventKey as keyof typeof nodeCompletionMap];
                this.completedStages[stageId] = true;
                console.log(`Stage marked as complete via node: ${stageId}`);
              } else if (eventKey in stateFieldCompletionMap) {
                const stageId =
                  stateFieldCompletionMap[eventKey as keyof typeof stateFieldCompletionMap];
                this.completedStages[stageId] = true;
                console.log(`Stage marked as complete via state field: ${stageId}`);
              }
            }

            // Also check for explicit stage completion messages
            if (payload.data.completed_stages && Array.isArray(payload.data.completed_stages)) {
              payload.data.completed_stages.forEach((stage: string) => {
                this.completedStages[stage] = true;
                console.log(`Stage marked as complete via completed_stages: ${stage}`);
              });
            }
          }
        } else {
          console.log("Unhandled message type:", payload);
        }

        console.log("Current workflow status after processing:", this.status);
        console.log("=== End WebSocket Message Processing ===");
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    },

    handleWorkflowPaused(data: any) {
      console.log(`Workflow paused for ${data.approval_type} approval.`);
      console.log("Raw pause data structure:", data);
      console.log("DEBUG: approval_type from backend:", data.approval_type);
      console.log("DEBUG: session_id from backend:", data.session_id);

      // Handle the new nested payload format from the refactored backend
      if (data.payload) {
        console.log("Found nested payload structure, extracting approval data");
        const approvalPayload = data.payload;

        const approvalData: ApprovalData = {
          session_id: data.session_id,
          approval_type: data.approval_type,
          step_name: approvalPayload.step_name,
          display_name: approvalPayload.display_name || data.approval_type,
          approval_data: approvalPayload.data,
          message:
            approvalPayload.instructions || `Please review the ${data.approval_type} results`,
          project_name: approvalPayload.data?.project_name || "",
          data: approvalPayload.data, // Keep the raw data as well
        };

        this.status = "paused";
        this.humanApprovalRequest = approvalData;
        if (approvalData.project_name) {
          this.projectName = approvalData.project_name;
        }

        console.log("Set human approval request:", this.humanApprovalRequest);
      } else {
        // Fallback for legacy format (direct approval data)
        console.log("Using legacy direct approval data format");
        this.status = "paused";
        this.humanApprovalRequest = data as ApprovalData;
        if (data.project_name) {
          this.projectName = data.project_name;
        }
      }

      // Mark the PREVIOUS stage as completed when the workflow pauses for the NEXT approval
      // Determine which stage was just completed based on the current approval type
      const previousStageMap = {
        tech_stack_recommendation: "brd_analysis",
        tech_stack: "brd_analysis",
        system_design: "tech_stack_recommendation",
        implementation_plan: "system_design",
        plan: "system_design",
        code_generation: "implementation_plan",
      };

      const currentApprovalType = data.approval_type || data.humanApprovalRequest?.approval_type;
      if (
        currentApprovalType &&
        previousStageMap[currentApprovalType as keyof typeof previousStageMap]
      ) {
        const previousStage =
          previousStageMap[currentApprovalType as keyof typeof previousStageMap];
        this.completedStages[previousStage] = true;
        console.log(
          `Marked previous stage ${previousStage} as completed (pausing for ${currentApprovalType})`
        );
      }

      // Also mark from explicit stage tracking if available
      if (data?.current_approved_stage) {
        this.completedStages[data.current_approved_stage] = true;
        console.log(`Marked stage ${data.current_approved_stage} as completed.`);
      }
    },

    handleHumanApprovalRequired(payloadData: any, sessionId: string) {
      console.log(`Human approval required for step: ${payloadData.step_name}`);
      console.log("Approval payload structure:", payloadData);

      // Convert the new format to the expected ApprovalData format
      const approvalType = this.extractApprovalTypeFromStepName(payloadData.step_name);

      const approvalData: ApprovalData = {
        session_id: sessionId,
        approval_type: approvalType,
        step_name: payloadData.step_name,
        display_name: payloadData.display_name || "",
        approval_data: payloadData.data,
        message: payloadData.instructions || `Please review the ${approvalType} results`,
        project_name: payloadData.data?.project_name || "",
        data: payloadData.data, // Keep the raw data as well
      };

      this.status = "paused";
      this.humanApprovalRequest = approvalData;
      if (approvalData.project_name) {
        this.projectName = approvalData.project_name;
      }
    },

    extractApprovalTypeFromStepName(stepName: string): string {
      if (stepName.includes("brd")) return "brd_analysis";
      if (stepName.includes("tech_stack")) return "tech_stack";
      if (stepName.includes("design")) return "system_design";
      if (stepName.includes("plan")) return "implementation_plan";
      if (stepName.includes("code")) return "code_generation";
      return "unknown";
    },

    async submitHumanDecision(
      decision: "proceed" | "revise" | "end",
      feedback?: string,
      selectedStack?: { [key: string]: string }
    ) {
      if (!this.sessionId || !this.humanApprovalRequest) {
        console.error("Cannot submit decision: No active session or approval request.");
        this.error = "No active session or approval request to submit decision.";
        return;
      }

      this.status = "running"; // Indicate that the workflow is resuming
      this.error = null; // Clear any previous errors

      try {
        const feedbackPayload: { [key: string]: any } = {
          decision: decision,
        };

        if (feedback) {
          feedbackPayload.feedback_message = feedback;
        }

        if (selectedStack) {
          feedbackPayload.selected_stack = selectedStack;
        }

        const response = await axios.post(`${API_BASE_URL}/api/workflow/resume/${this.sessionId}`, {
          user_feedback: feedbackPayload,
          current_stage: this.humanApprovalRequest.step_name, // Pass the step name to resume from
        });

        console.log("Decision submitted successfully:", response.data);
        this.humanApprovalRequest = null; // Clear the approval request
        // The WebSocket will handle status updates as the workflow progresses
      } catch (err: any) {
        this.status = "error";
        this.error =
          err.response?.data?.detail || err.message || "Failed to submit human decision.";
        console.error("Error submitting human decision:", err);
      }
    },

    resetState() {
      this.disconnectWebSocket();
      this.sessionId = null;
      this.status = "idle";
      this.humanApprovalRequest = null;
      this.completedStages = {};
      this.projectName = "";
      this.error = null;
      this.isConnected = false;
      this.workflowEvents = [];
    },

    // Add a method to set session ID and connect WebSocket
    setSessionId(sessionId: string) {
      this.sessionId = sessionId;
      if (sessionId) {
        this.connectWebSocket();
      }
    },

    // Debug method to check connection status
    getConnectionInfo() {
      return {
        sessionId: this.sessionId,
        isConnected: this.isConnected,
        socketState: this.socket?.readyState,
        status: this.status,
        error: this.error,
      };
    },
  },
});
