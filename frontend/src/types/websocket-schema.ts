/**
 * WebSocket Message Schema - Frontend
 * Defines the type structure for all WebSocket messages between frontend and backend
 */

// Common message structure
export interface WebSocketMessage {
  type: string;
  session_id?: string;
  timestamp?: string;
  event?: string;
}

// Agent event types
export type AgentEventType =
  | "node_end"
  | "agent_thinking"
  | "node_update"
  | "agent_action"
  | "tool_result"
  | "agent_completed"
  | "workflow_status";

// Agent event message
export interface AgentEventMessage extends WebSocketMessage {
  type: "agent_event";
  event_type: AgentEventType;
  data: any; // Specific structure depends on event_type
}

// Workflow status message
export interface WorkflowStatusMessage extends WebSocketMessage {
  type: "agent_event";
  event_type: "workflow_status";
  data: {
    status: "started" | "paused" | "resumed" | "completed" | "failed";
    message: string;
    data?: any;
    current_node?: string;
  };
}

// Workflow paused message
export interface WorkflowPausedMessage extends WebSocketMessage {
  event: "workflow_paused";
  data: {
    paused_at: string | string[];
    brd_analysis_results?: any;
    brd_analysis_output?: any;
    brd_analysis?: any;
    requirements_analysis?: any;
    extracted_requirements?: any[];
    requirements?: any[];
    brd_content?: string;
    content?: string;
    [key: string]: any;
  };
}

// Human response to send back
export interface HumanResponseMessage {
  decision: "proceed" | "revise" | "end";
  feedback?: {
    comments?: string;
    [key: string]: any;
  };
}

// Error message
export interface ErrorMessage extends WebSocketMessage {
  type: "error";
  error: string;
  details?: any;
}

// Health check message
export interface HealthCheckMessage extends WebSocketMessage {
  type: "health_check";
  status: "ok";
  version: string;
  api_version: string;
}

// Union type for all possible message types
export type WebSocketMessageTypes =
  | AgentEventMessage
  | WorkflowStatusMessage
  | WorkflowPausedMessage
  | ErrorMessage
  | HealthCheckMessage;
