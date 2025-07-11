<!-- /src/views/WorkflowMonitorView.vue -->
<template>
  <div class="bg-slate-900 text-white min-h-screen -m-4 sm:-m-6 lg:-m-8">
    <div class="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      <div class="flex flex-col lg:flex-row items-start justify-between gap-4 mb-8">
        <div>
          <h1 class="text-2xl font-bold text-white sm:text-3xl">
            {{ projectName || "Workflow Monitor" }}
          </h1>
          <p v-if="sessionId" class="text-sm text-gray-400 mt-1">
            Session ID:
            <span class="font-mono bg-slate-700/50 text-indigo-300 px-2 py-1 rounded-md">
              {{ sessionId }}
            </span>
          </p>
        </div>
        <router-link
          to="/new-project"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 transition hover:scale-105"
        >
          Start New Project
        </router-link>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        <!-- Left Column: Progress Tracker -->
        <div class="lg:col-span-1 h-fit sticky top-24">
          <WorkflowProgressTracker />
        </div>

        <!-- Right Column: Main Content -->
        <div class="lg:col-span-2 space-y-4">
          <!-- GENERIC HUMAN APPROVAL SECTION (Always visible if active) -->
          <template
            v-if="
              status === 'paused' && humanApprovalRequest && currentReviewComponent && sessionId
            "
          >
            <!-- Debug info -->
            <div class="bg-orange-900/50 border border-orange-700 p-3 rounded-lg text-xs text-orange-200 mb-4 animate-pulse-once">
              <p class="font-bold text-lg mb-2">Human Approval Required!</p>
              <p>Approval Type: {{ humanApprovalRequest.step_name }}</p>
              <p>Step Name: {{ humanApprovalRequest.display_name }}</p>
              <p v-if="humanApprovalRequest.data">
                Data keys: {{ Object.keys(humanApprovalRequest.data).join(", ") }}
              </p>
            </div>

            <component
              :is="currentReviewComponent"
              :data="humanApprovalRequest.data"
              @proceed="handleDecision('proceed', undefined, $event)"
              @revise="handleReviseDecision"
              @end="handleDecision('end')"
            />
          </template>

          <!-- Tab Navigation -->
          <div class="flex border-b border-slate-700 mb-4">
            <button
              @click="selectedTab = 'logs'"
              :class="{
                'py-2 px-4 border-b-2': true,
                'border-indigo-500 text-indigo-300 font-semibold': selectedTab === 'logs',
                'border-transparent text-gray-400 hover:text-gray-200': selectedTab !== 'logs',
              }"
            >
              Workflow Logs
            </button>
            <button
              @click="selectedTab = 'code'"
              :class="{
                'py-2 px-4 border-b-2': true,
                'border-indigo-500 text-indigo-300 font-semibold': selectedTab === 'code',
                'border-transparent text-gray-400 hover:text-gray-200': selectedTab !== 'code',
              }"
            >
              Code Browser
            </button>
          </div>

          <!-- Tab Content -->
          <template v-if="selectedTab === 'logs'">
            <WorkflowLogViewer />
          </template>
          <template v-else-if="selectedTab === 'code'">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 h-[70vh]">
              <!-- File Tree Section -->
              <div class="md:col-span-1">
                <FileTree v-if="sessionId" :sessionId="sessionId" @file-selected="handleFileSelected" />
                <div v-else class="bg-slate-800/50 p-4 rounded-lg text-center text-gray-400">
                  No session active to browse files.
                </div>
              </div>
              <!-- Code Viewer Section -->
              <div class="md:col-span-1">
                <CodeViewer v-if="sessionId" :sessionId="sessionId" :filePath="selectedFilePath" />
                <div v-else class="bg-slate-800/50 p-4 rounded-lg text-center text-gray-400">
                  No session active or file selected.
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Workflow Results Section -->
      <div class="mt-12 grid grid-cols-1 gap-8">
        <WorkflowResults v-if="sessionId" :sessionId="sessionId" />
      </div>
    </div>
    <AppFooter class="-mx-4 sm:-mx-6 lg:-mx-8" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, markRaw, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useWorkflowStore } from "@/stores/workflow";
import { storeToRefs } from "pinia";

// Import all possible review components
import BrdAnalysisReview from "@/components/BrdAnalysisReview.vue";
import TechStackReview from "@/components/review/TechStackReview.vue";
import SystemDesignReview from "@/components/review/SystemDesignReview.vue";
import PlanReview from "@/components/review/PlanReview.vue";
import CodeGenerationReview from "@/components/review/CodeGenerationReview.vue";

import AppFooter from "@/components/AppFooter.vue";
import WorkflowProgressTracker from "@/components/WorkflowProgressTracker.vue";
import WorkflowLogViewer from "@/components/WorkflowLogViewer.vue";
import WorkflowResults from "@/components/WorkflowResults.vue";
import FileTree from "@/components/file_browser/FileTree.vue";
import CodeViewer from "@/components/file_browser/CodeViewer.vue";

const route = useRoute();
const router = useRouter();
const workflowStore = useWorkflowStore();

// Make store state and getters reactive
const { sessionId, status, humanApprovalRequest, projectName } = storeToRefs(workflowStore);

// Reactive state for tab selection and selected file
const selectedTab = ref("logs");
const selectedFilePath = ref<string | null>(null);

// Set the session ID from the route params and connect WebSocket
if (route.params.sessionId) {
  workflowStore.setSessionId(route.params.sessionId as string);
}

// Map approval types to the components that should render them
const reviewComponentMap: Record<string, any> = {
  brd_analysis: markRaw(BrdAnalysisReview),
  tech_stack: markRaw(TechStackReview),
  tech_stack_recommendation: markRaw(TechStackReview), // Add the exact key from backend
  system_design: markRaw(SystemDesignReview),
  implementation_plan: markRaw(PlanReview),
  code_generation: markRaw(CodeGenerationReview),
};

// Dynamically determine which review component to show
const currentReviewComponent = computed(() => {
  if (status.value === "paused" && humanApprovalRequest.value) {
    const approvalType = humanApprovalRequest.value.approval_type;
    const component = reviewComponentMap[approvalType];
    console.log("DEBUG: Approval type:", approvalType);
    console.log("DEBUG: Component found:", !!component);
    console.log("DEBUG: Available component types:", Object.keys(reviewComponentMap));
    return component || null;
  }
  return null;
});

// Generic handler for all decisions
const handleDecision = (decision: "proceed" | "revise" | "end", feedback?: string, selectedStack?: { [key: string]: string }) => {
  workflowStore.submitHumanDecision(decision, feedback, selectedStack);
};

// Specific handler for revise decisions with multiple parameters
const handleReviseDecision = (feedback: string, selectedStack: { [key: string]: string }) => {
  handleDecision('revise', feedback, selectedStack);
};

// Handle file selection from FileTree component
const handleFileSelected = (filePath: string) => {
  selectedFilePath.value = filePath;
};

// Auto-select 'code' tab if a file is selected and not currently on 'logs' tab
watch(selectedFilePath, (newPath) => {
  if (newPath && selectedTab.value !== 'code') {
    selectedTab.value = 'code';
  }
});
</script>

<style scoped>
/* Basic animation for approval section */
@keyframes pulse-once {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.01); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}

.animate-pulse-once {
  animation: pulse-once 1.5s ease-in-out;
}

/* Tab button styles */
.border-b-2 {
  border-bottom-width: 2px;
}
</style>
