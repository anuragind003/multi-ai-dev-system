<template>
  <div class="space-y-4">
    <!-- Current Active Agent Indicator -->
    <div
      v-if="currentActiveAgent"
      class="bg-gradient-to-r from-blue-900/50 to-purple-900/50 p-4 rounded-xl border border-blue-400/30"
    >
      <div class="flex items-center space-x-3">
        <div class="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
        <div>
          <p class="text-sm font-semibold text-blue-300">Currently Active</p>
          <p class="text-white font-medium">{{ currentActiveAgent.name }}</p>
          <p class="text-xs text-gray-300">{{ currentActiveAgent.process }}</p>
        </div>
      </div>
    </div>

    <div v-if="logs.length > 0">
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="bg-slate-800/50 p-5 rounded-2xl shadow-lg border border-white/10"
        :class="getLogStyling(log)"
      >
        <p class="font-mono text-xs text-gray-400">
          <span class="text-indigo-400">{{ log.timestamp }}</span>
          <span class="text-green-400"> [{{ log.agent }}]</span>
          <span class="text-cyan-400"> ({{ log.phase }})</span>
          <span v-if="log.workItem" class="text-yellow-400"> - Work Item: {{ log.workItem }}</span>
        </p>
        <p class="mt-2 text-gray-200">{{ log.message }}</p>
        <div v-if="log.details" class="mt-2 text-xs text-gray-400 bg-slate-700/50 p-2 rounded">
          {{ log.details }}
        </div>
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
import { computed, ref } from "vue";
import { useWorkflowStore } from "@/stores/workflow";
import { storeToRefs } from "pinia";

interface LogEntry {
  timestamp: string;
  agent: string;
  phase: string;
  message: string;
  workItem?: string;
  details?: string;
  type: "info" | "success" | "warning" | "error" | "active";
}

interface ActiveAgent {
  name: string;
  process: string;
}

// Track the current active agent
const currentActiveAgent = ref<ActiveAgent | null>(null);

// This is a placeholder as the new store doesn't have detailed logs yet.
// This can be expanded later to parse the raw websocket events.
const logs = computed<LogEntry[]>(() => {
  // Convert workflow events to log entries
  const logEntries = workflowEvents.value.map((event, index) => {
    const agent = getAgentFromEvent(event.event);
    const phase = getPhaseFromEvent(event.event);
    const message = getMessageFromEvent(event);
    const workItem = getWorkItemFromEvent(event);
    const details = getDetailsFromEvent(event);
    const type = getLogType(event);

    // Update current active agent
    updateCurrentActiveAgent(event, agent, phase);

    return {
      timestamp: new Date(event.timestamp).toLocaleTimeString(),
      agent,
      phase,
      message,
      workItem,
      details,
      type,
    };
  });

  return logEntries;
});

// Helper function to update current active agent
const updateCurrentActiveAgent = (event: any, agent: string, phase: string) => {
  const eventType = event.event;

  // Set active agent for code generation processes
  if (
    eventType.includes("code_generation") ||
    eventType.includes("work_item_iterator") ||
    eventType.includes("code_quality") ||
    eventType.includes("test_execution") ||
    eventType.includes("integration")
  ) {
    let process = "Processing...";

    if (eventType.includes("work_item_iterator")) {
      process = "Selecting next work item for development";
    } else if (eventType.includes("code_generation_dispatcher")) {
      process = "Routing to specialized code generation agent";
    } else if (eventType.includes("architecture")) {
      process = "Generating project architecture and structure";
    } else if (eventType.includes("database")) {
      process = "Creating database schemas and models";
    } else if (eventType.includes("backend")) {
      process = "Developing backend APIs and business logic";
    } else if (eventType.includes("frontend")) {
      process = "Building user interface components";
    } else if (eventType.includes("code_quality")) {
      process = "Analyzing code quality and best practices";
    } else if (eventType.includes("test_execution")) {
      process = "Running unit tests and validation";
    } else if (eventType.includes("integration")) {
      process = "Integrating code and running system tests";
    }

    currentActiveAgent.value = { name: agent, process };
  }

  // Set active agent for main workflow stages
  else if (eventType === "workflow_event" && event.data) {
    // Check which node is currently active
    for (const key of Object.keys(event.data)) {
      if (key.includes("_node")) {
        if (key === "brd_analysis_node") {
          currentActiveAgent.value = {
            name: "BRD Analyst",
            process: "Analyzing requirements and business objectives",
          };
        } else if (key === "tech_stack_recommendation_node") {
          currentActiveAgent.value = {
            name: "Tech Stack Advisor",
            process: "Evaluating technologies and frameworks",
          };
        } else if (key === "system_design_node") {
          currentActiveAgent.value = {
            name: "System Designer",
            process: "Creating system architecture and design",
          };
        } else if (key === "planning_node" || key === "unified_planning_node") {
          currentActiveAgent.value = {
            name: "Plan Compiler",
            process: "Organizing implementation plan and work items",
          };
        } else if (key === "code_generation_node") {
          currentActiveAgent.value = {
            name: "Code Generator",
            process: "Generating project code and structure",
          };
        }
        break;
      }
    }
  }

  // Clear active agent when workflow completes or pauses for human input
  if (eventType === "workflow_completed" || eventType === "workflow_paused") {
    currentActiveAgent.value = null;
  }
};

// Helper function to get work item information
const getWorkItemFromEvent = (event: any): string | undefined => {
  // Try to extract work item info from event data
  if (event.data?.current_work_item?.id) {
    return event.data.current_work_item.id;
  }
  if (event.data?.work_item?.id) {
    return event.data.work_item.id;
  }
  return undefined;
};

// Helper function to get additional details
const getDetailsFromEvent = (event: any): string | undefined => {
  if (event.data?.current_work_item?.description) {
    return `Task: ${event.data.current_work_item.description}`;
  }
  if (event.data?.agent_role) {
    return `Agent Role: ${event.data.agent_role}`;
  }
  if (event.data?.status) {
    return `Status: ${event.data.status}`;
  }
  return undefined;
};

// Helper function to determine log type for styling
const getLogType = (event: any): LogEntry["type"] => {
  const eventType = event.event;

  if (eventType.includes("error") || event.data?.error) return "error";
  if (eventType.includes("completed") || eventType.includes("success")) return "success";
  if (eventType.includes("warning") || eventType.includes("revision")) return "warning";
  if (eventType.includes("code_generation") || eventType.includes("active")) return "active";

  return "info";
};

// Helper function for log styling
const getLogStyling = (log: LogEntry): string => {
  switch (log.type) {
    case "success":
      return "border-green-400/30 bg-green-900/20";
    case "error":
      return "border-red-400/30 bg-red-900/20";
    case "warning":
      return "border-yellow-400/30 bg-yellow-900/20";
    case "active":
      return "border-blue-400/30 bg-blue-900/20";
    default:
      return "";
  }
};

// Enhanced helper functions to extract meaningful data from events
const getAgentFromEvent = (eventType: string): string => {
  // Code Generation Agents
  if (eventType.includes("architecture_generator") || eventType.includes("architecture_specialist"))
    return "Architecture Generator";
  if (eventType.includes("database_generator") || eventType.includes("database_specialist"))
    return "Database Generator";
  if (eventType.includes("backend_orchestrator") || eventType.includes("backend_developer"))
    return "Backend Orchestrator";
  if (eventType.includes("frontend_generator") || eventType.includes("frontend_developer"))
    return "Frontend Generator";
  if (eventType.includes("integration_generator")) return "Integration Generator";
  if (eventType.includes("code_optimizer")) return "Code Optimizer";

  // Specialized Sub-Agents
  if (eventType.includes("core_backend")) return "Core Backend Agent";
  if (eventType.includes("security_compliance")) return "Security Compliance Agent";
  if (eventType.includes("devops_infrastructure")) return "DevOps Infrastructure Agent";
  if (eventType.includes("documentation")) return "Documentation Agent";
  if (eventType.includes("monitoring_observability")) return "Monitoring Agent";
  if (eventType.includes("testing_qa")) return "Testing QA Agent";

  // Main Workflow Agents
  if (eventType.includes("brd_analysis")) return "BRD Analyst";
  if (eventType.includes("tech_stack")) return "Tech Stack Advisor";
  if (eventType.includes("system_design")) return "System Designer";
  if (eventType.includes("planning") || eventType.includes("plan_compiler")) return "Plan Compiler";
  if (eventType.includes("code_quality")) return "Code Quality Agent";

  // Workflow Control
  if (eventType.includes("work_item_iterator")) return "Work Item Iterator";
  if (eventType.includes("code_generation_dispatcher")) return "Code Generation Dispatcher";
  if (eventType.includes("test_execution")) return "Test Execution Engine";
  if (eventType.includes("integration_node")) return "Integration Engine";
  if (eventType.includes("phase_completion")) return "Phase Completion";
  if (eventType.includes("increment_revision")) return "Revision Controller";

  // System
  if (eventType.includes("initialize")) return "System Initializer";
  if (eventType.includes("finalize")) return "Workflow Finalizer";

  return "Workflow Manager";
};

const getPhaseFromEvent = (eventType: string): string => {
  // Code Generation Phases
  if (eventType.includes("work_item_iterator")) return "Work Item Selection";
  if (eventType.includes("code_generation_dispatcher")) return "Agent Routing";
  if (eventType.includes("architecture")) return "Architecture";
  if (eventType.includes("database")) return "Database";
  if (eventType.includes("backend")) return "Backend Development";
  if (eventType.includes("frontend")) return "Frontend Development";
  if (eventType.includes("integration_generator")) return "Integration";
  if (eventType.includes("code_optimizer")) return "Optimization";

  // Quality Assurance Phases
  if (eventType.includes("code_quality")) return "Quality Review";
  if (eventType.includes("test_execution")) return "Testing";
  if (eventType.includes("integration_node")) return "Integration Testing";

  // Main Workflow Phases
  if (eventType.includes("brd_analysis")) return "Requirements Analysis";
  if (eventType.includes("tech_stack")) return "Technology Planning";
  if (eventType.includes("system_design")) return "System Design";
  if (eventType.includes("planning")) return "Implementation Planning";

  // Control Phases
  if (eventType.includes("phase_completion")) return "Phase Completion";
  if (eventType.includes("increment_revision")) return "Revision";
  if (eventType.includes("initialize")) return "Initialization";
  if (eventType.includes("finalize")) return "Finalization";

  return "Processing";
};

const getMessageFromEvent = (event: any): string => {
  if (event.message) return event.message;

  const eventType = event.event;

  // Code Generation Messages
  if (eventType.includes("work_item_iterator_node")) {
    if (event.data?.current_work_item) {
      const workItem = event.data.current_work_item;
      return `Starting work item: ${workItem.id} (${workItem.agent_role || "unknown role"})`;
    }
    return "Selecting next work item for development";
  }

  if (eventType.includes("code_generation_dispatcher_node")) {
    if (event.data?.current_work_item?.agent_role) {
      return `Routing to ${event.data.current_work_item.agent_role} for code generation`;
    }
    return "Dispatching to specialized code generation agent";
  }

  if (eventType.includes("code_generation_node")) {
    return "Generating code using specialized agent";
  }

  if (eventType.includes("code_quality_node")) {
    if (event.data?.code_review_feedback?.approved) {
      return "Code quality review passed - proceeding to testing";
    } else if (event.data?.code_review_feedback?.approved === false) {
      return "Code quality issues found - requesting revision";
    }
    return "Analyzing code quality and best practices";
  }

  if (eventType.includes("test_execution_node")) {
    if (event.data?.test_validation_result?.passed) {
      return "Unit tests passed - proceeding to integration";
    } else if (event.data?.test_validation_result?.passed === false) {
      return "Unit tests failed - requesting revision";
    }
    return "Executing unit tests and validation";
  }

  if (eventType.includes("integration_node")) {
    if (event.data?.integration_test_result?.passed) {
      return "Integration tests passed - work item completed";
    }
    return "Running integration tests and merging code";
  }

  if (eventType.includes("phase_completion_node")) {
    return "Work item completed successfully - moving to next item";
  }

  if (eventType.includes("increment_revision_node")) {
    return "Incrementing revision count - retrying code generation";
  }

  // Extract meaningful messages from event data
  if (event.event === "workflow_paused") {
    const approvalType = event.data?.approval_type || "approval";
    const displayName =
      event.data?.display_name ||
      approvalType
        .replace(/_/g, " ")
        .replace(/node$/, "")
        .trim()
        .replace(/\b\w/g, (c: string) => c.toUpperCase());

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
  if (event.event === "workflow_event" && event.data && typeof event.data === "object") {
    // Check for node completion events with better descriptions
    for (const key of Object.keys(event.data)) {
      if (key.includes("_node")) {
        if (key === "brd_analysis_node") {
          return "Requirements analysis completed. Business objectives and technical requirements identified.";
        }
        if (key === "tech_stack_recommendation_node") {
          return "Technology stack analysis completed. Framework and technology recommendations generated.";
        }
        if (key === "system_design_node") {
          return "System design completed. Architecture patterns and component structure defined.";
        }
        if (key === "planning_node" || key === "unified_planning_node") {
          return "Implementation plan compiled. Development phases and work items organized.";
        }
        if (key === "code_generation_node" || key === "unified_code_generation_dispatcher_node") {
          return "Code generation phase initiated. Project structure and files being created.";
        }
        // Generic fallback for other nodes
        const nodeName = key.replace("_node", "").replace("_", " ");
        return `${nodeName.charAt(0).toUpperCase() + nodeName.slice(1)} completed successfully.`;
      }

      // Check for state field updates
      if (key === "requirements_analysis") {
        return "Requirements analysis results saved. Moving to technology recommendations.";
      }
      if (key === "tech_stack_recommendation") {
        return "Technology stack recommendations saved. Proceeding to system design.";
      }
      if (key === "system_design") {
        return "System design specifications saved. Moving to implementation planning.";
      }
      if (key === "implementation_plan") {
        return "Implementation plan saved. Ready for code generation phase.";
      }
      if (key === "completed_stages" && Array.isArray(event.data[key])) {
        const completedStages = event.data[key];
        const latestStage = completedStages[completedStages.length - 1];
        return `Stage '${latestStage}' marked as completed. Workflow progressing to next phase.`;
      }
    }

    const innerEvent = event.data.event;
    if (innerEvent) {
      if (innerEvent === "workflow_completed") return "🎉 Workflow completed successfully!";
      if (innerEvent.includes("brd_analysis_node")) return "✅ Requirements Analysis completed";
      if (innerEvent.includes("tech_stack_node")) {
        // Try to extract tech stack summary - handle both nested and direct formats
        let techStackData = event.data?.tech_stack_recommendation_node?.tech_stack_result;

        // If not found in nested format, try direct format
        if (!techStackData) {
          techStackData = event.data?.tech_stack_recommendation_node;
        }

        if (techStackData && techStackData.selected_stack) {
          const selected = techStackData.selected_stack;
          return `✅ Tech Stack selected: ${selected.frontend_selection || "N/A"} + ${
            selected.backend_selection || "N/A"
          } + ${selected.database_selection || "N/A"}`;
        }
        return "✅ Tech Stack Recommendation completed";
      }
      if (innerEvent.includes("system_design_node")) return "✅ System Design completed";
      if (innerEvent.includes("planning_node")) return "✅ Implementation Planning completed";
      if (innerEvent.includes("code_generation")) return "🔧 Code Generation in progress";

      // For other internal node events, try to make them readable
      const nodeName = Object.keys(event.data).find((key) => key.includes("_node"));
      if (nodeName) {
        return `Processing: ${nodeName.replace(/_/g, " ").replace(/node$/, "").trim()}`;
      }
      // Fallback for other workflow_event types with data
      return `Event: ${innerEvent.replace(/_/g, " ")}`;
    }
    // Fallback if innerEvent is not found but there's other data
    const eventKeys = Object.keys(event.data || {});
    if (eventKeys.length > 0) {
      const mainKey = eventKeys[0];
      return `Updated: ${mainKey.replace(/_/g, " ")}`;
    }
  }

  if (event.event.endsWith("_node")) {
    return `Processing: ${event.event.replace(/_node$/, "").replace(/_/g, " ")}`;
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
