<template>
  <div class="space-y-6">
    <div class="bg-slate-900/70 border border-slate-700 p-6 rounded-lg">
      <h3 class="text-lg font-semibold text-gray-200 mb-4">Workflow Results History</h3>

      <div v-if="loading" class="text-center text-gray-400">Loading workflow results...</div>

      <div v-else-if="error" class="text-red-400 bg-red-900/20 p-4 rounded-lg">
        Error loading results: {{ error }}
      </div>

      <div
        v-else-if="!results || Object.keys(results).length === 0"
        class="text-gray-400 text-center py-8"
      >
        No workflow results available yet. Results will appear here after each approval step.
      </div>

      <div v-else class="space-y-4">
        <!-- BRD Analysis Results -->
        <div
          v-if="results.brd_analysis"
          class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
        >
          <div class="flex justify-between items-center mb-3">
            <h4 class="text-md font-semibold text-blue-300">BRD Analysis</h4>
            <span class="text-xs text-gray-400">{{
              formatTimestamp(results.brd_analysis.timestamp)
            }}</span>
          </div>
          <div class="space-y-2 text-sm text-gray-300">
            <p>
              <strong>Project Summary:</strong>
              {{ results.brd_analysis.data.project_summary || "N/A" }}
            </p>
            <p>
              <strong>Requirements:</strong>
              {{ (results.brd_analysis.data.requirements || []).length }} items
            </p>
            <p>
              <strong>Functional Requirements:</strong>
              {{ (results.brd_analysis.data.functional_requirements || []).length }} items
            </p>
          </div>
        </div>

        <!-- Tech Stack Results -->
        <div
          v-if="results.tech_stack_recommendation || results.tech_stack"
          class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
        >
          <div class="flex justify-between items-center mb-3">
            <h4 class="text-md font-semibold text-green-300">Tech Stack Recommendation</h4>
            <span class="text-xs text-gray-400">{{
              formatTimestamp((results.tech_stack_recommendation || results.tech_stack).timestamp)
            }}</span>
          </div>
          <div class="space-y-2 text-sm text-gray-300">
            <div v-if="techStackSummary">
              <p>
                <strong>Frontend:</strong> {{ techStackSummary.frontend || "N/A" }}
              </p>
              <p>
                <strong>Backend:</strong> {{ techStackSummary.backend || "N/A" }}
              </p>
              <p><strong>Database:</strong> {{ techStackSummary.database || "N/A" }}</p>
              <p v-if="techStackSummary.architecture">
                <strong>Architecture:</strong> {{ techStackSummary.architecture }}
              </p>
              <p v-if="techStackSummary.cloud">
                <strong>Cloud:</strong> {{ techStackSummary.cloud }}
              </p>
              <div class="mt-3">
                <p class="text-xs text-gray-400">
                  <strong>Options Available:</strong>
                  {{ techStackSummary.optionsCounts || "N/A" }}
                </p>
              </div>
            </div>
            <div v-else class="text-gray-400">
              Tech stack data structure not recognized. Please refresh results.
            </div>
          </div>
        </div>

        <!-- System Design Results -->
        <div
          v-if="results.system_design"
          class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
        >
          <div class="flex justify-between items-center mb-3">
            <span class="text-xs text-gray-400">{{
              formatTimestamp(results.system_design.timestamp)
            }}</span>
          </div>
          <SystemDesignVisualization :systemDesign="results.system_design.data" />
        </div>

        <!-- Implementation Plan Results -->
        <div
          v-if="results.implementation_plan"
          class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
        >
          <div class="flex justify-between items-center mb-3">
            <span class="text-xs text-gray-400">{{
              formatTimestamp(results.implementation_plan.timestamp)
            }}</span>
          </div>
          <ImplementationPlanVisualization :implementationPlan="results.implementation_plan.data" />
        </div>

        <!-- Generated Code Browser -->
        <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
          <div class="flex justify-between items-center mb-3">
            <h4 class="text-md font-semibold text-emerald-300">Generated Code</h4>
            <span class="text-xs text-gray-400">Live Code Browser</span>
          </div>
          <GeneratedCodeBrowser 
            :sessionId="sessionId"
            height="700px"
            @file-selected="handleFileSelected"
            @files-loaded="handleFilesLoaded"
          />
        </div>
      </div>

      <div class="mt-6 flex justify-end">
        <button
          @click="refreshResults"
          :disabled="loading"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
        >
          <span v-if="loading">Refreshing...</span>
          <span v-else>Refresh Results</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import SystemDesignVisualization from "./SystemDesignVisualization.vue";
import ImplementationPlanVisualization from "./ImplementationPlanVisualization.vue";
import GeneratedCodeBrowser from "./GeneratedCodeBrowser.vue";

interface Props {
  sessionId: string;
}

const props = defineProps<Props>();

const results = ref<any>({});
const loading = ref(true);
const error = ref<string | null>(null);

const formatTimestamp = (timestamp: number) => {
  return new Date(timestamp * 1000).toLocaleString();
};

const fetchResults = async () => {
  try {
    loading.value = true;
    error.value = null;

    const response = await fetch(`/api/workflow/results/${props.sessionId}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    results.value = data.results || {};
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Unknown error occurred";
    console.error("Error fetching workflow results:", err);
  } finally {
    loading.value = false;
  }
};

const refreshResults = () => {
  fetchResults();
};

// Code browser handlers
const handleFileSelected = (filePath: string | null) => {
  console.log('File selected:', filePath);
  // Could add additional handling here
};

const handleFilesLoaded = (filesData: any) => {
  console.log('Files loaded:', filesData);
  // Could add additional handling here
};

// Extract session ID from props for code browser
const sessionId = computed(() => props.sessionId);

const techStackSummary = computed(() => {
  const techStackData = results.value.tech_stack_recommendation || results.value.tech_stack;
  
  if (!techStackData) return null;

  // Helper function to extract tech component name
  const getTechName = (component: any): string => {
    if (!component) return "N/A";
    if (typeof component === 'string') return component;
    if (component.name) return component.name;
    if (component.framework) return component.framework;
    return "N/A";
  };

  // Handle user selected stack (correct field names: frontend, backend, database, etc.)
  if (techStackData.selected_stack) {
    const selectedStack = techStackData.selected_stack;
    return {
      frontend: getTechName(selectedStack.frontend),
      backend: getTechName(selectedStack.backend),
      database: getTechName(selectedStack.database),
      architecture: selectedStack.architecture?.pattern || selectedStack.architecture?.name || null,
      cloud: getTechName(selectedStack.cloud),
      optionsCounts: "User selected stack"
    };
  }

  // Check for nested data structure
  const data = techStackData.data || techStackData;
  
  // Handle user selected stack in nested data
  if (data.selected_stack) {
    const selectedStack = data.selected_stack;
    return {
      frontend: getTechName(selectedStack.frontend),
      backend: getTechName(selectedStack.backend),
      database: getTechName(selectedStack.database),
      architecture: selectedStack.architecture?.pattern || selectedStack.architecture?.name || null,
      cloud: getTechName(selectedStack.cloud),
      optionsCounts: "User selected (nested)"
    };
  }

  // Handle synthesis format (most common for current system)
  if (data.synthesis) {
    const synthesis = data.synthesis;
    return {
      frontend: synthesis.frontend?.framework || synthesis.frontend?.name || "N/A",
      backend: synthesis.backend?.framework || synthesis.backend?.name || "N/A",
      database: synthesis.database?.type || synthesis.database?.name || "N/A",
      architecture: synthesis.architecture_pattern || null,
      cloud: synthesis.deployment_environment?.cloud_platform || synthesis.cloud?.name || null,
      optionsCounts: "AI recommendation"
    };
  }

  // Handle options arrays (fallback for when no user selection made yet)
  if (data.frontend_options || data.backend_options || data.database_options) {
    const options = {
      frontend_options: data.frontend_options || [],
      backend_options: data.backend_options || [],
      database_options: data.database_options || [],
      architecture_options: data.architecture_options || [],
      cloud_options: data.cloud_options || []
    };
    
         // Find selected options or use first option as default display
     const selectedFrontend = options.frontend_options.find((opt: any) => opt.selected) || options.frontend_options[0];
     const selectedBackend = options.backend_options.find((opt: any) => opt.selected) || options.backend_options[0];
     const selectedDatabase = options.database_options.find((opt: any) => opt.selected) || options.database_options[0];
     const selectedArchitecture = options.architecture_options.find((opt: any) => opt.selected) || options.architecture_options[0];
     const selectedCloud = options.cloud_options.find((opt: any) => opt.selected) || options.cloud_options[0];
    
    const optionsCounts = [];
    if (options.frontend_options?.length) optionsCounts.push(`${options.frontend_options.length} frontend`);
    if (options.backend_options?.length) optionsCounts.push(`${options.backend_options.length} backend`);
    if (options.database_options?.length) optionsCounts.push(`${options.database_options.length} database`);
    if (options.architecture_options?.length) optionsCounts.push(`${options.architecture_options.length} architecture`);
    if (options.cloud_options?.length) optionsCounts.push(`${options.cloud_options.length} cloud`);
    
    return {
      frontend: getTechName(selectedFrontend),
      backend: getTechName(selectedBackend),
      database: getTechName(selectedDatabase),
      architecture: selectedArchitecture?.pattern || selectedArchitecture?.name || null,
      cloud: getTechName(selectedCloud),
      optionsCounts: optionsCounts.join(', ') || "Available options"
    };
  }
  
  // Fallback: Handle legacy format or direct tech stack values
  return {
    frontend: data.frontend_framework || data.frontend || "N/A",
    backend: data.backend_framework || data.backend || "N/A",
    database: data.database_framework || data.database || "N/A",
    architecture: data.architecture || null,
    cloud: data.cloud || null,
    optionsCounts: "Legacy format"
  };
});

onMounted(() => {
  fetchResults();
});
</script>
