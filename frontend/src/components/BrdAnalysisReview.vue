<!-- /src/components/BrdAnalysisReview.vue -->
<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-2xl border border-white/10">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4 mb-6">
      Human Review Required: BRD Analysis
    </h2>

    <div v-if="data" class="space-y-6">
      <!-- Debug Info -->
      <div class="bg-slate-900 p-3 rounded text-xs">
        <p class="font-mono text-gray-400">
          Available fields: {{ Object.keys(data).join(", ") }}
        </p>
        <p
          v-if="typeof data === 'object' && data !== null"
          class="font-mono text-gray-400 mt-1"
        >
          Data type: {{ Array.isArray(data) ? "Array" : "Object" }}
        </p>
        <p class="font-mono text-green-400 mt-1">Using data from: {{ dataSource }}</p>
        <div
          v-if="data.requirements && data.requirements.length === 0"
          class="mt-1"
        >
          <p class="font-mono text-yellow-400">Empty requirements array found in data</p>
        </div>
        <div v-if="data.extracted_requirements" class="mt-1">
          <p class="font-mono text-green-400">
            Found extracted_requirements with length:
            {{
              Array.isArray(data.extracted_requirements)
                ? data.extracted_requirements.length
                : "Not an array"
            }}
          </p>
        </div>
        <div v-if="data.requirements" class="mt-1">
          <p class="font-mono text-green-400">
            Found requirements with length:
            {{
              Array.isArray(data.requirements)
                ? data.requirements.length
                : "Not an array"
            }}
          </p>
        </div>
      </div>

      <!-- Project Summary -->
      <div>
        <h3 class="font-semibold text-indigo-300">Project Name</h3>
        <p class="text-gray-300 mt-1">{{ projectName }}</p>
      </div>
      <div>
        <h3 class="font-semibold text-indigo-300">Summary</h3>
        <p class="text-gray-300 mt-1 prose prose-invert max-w-none">{{ projectSummary }}</p>
      </div>

      <!-- Requirements -->
      <div>
        <h3 class="font-semibold text-indigo-300">
          Extracted Requirements ({{ requirements.length }})
        </h3>
        <!-- Always show the requirements list since we now generate fake requirements if none exist -->
        <ul class="mt-2 space-y-3">
          <li
            v-for="req in requirements"
            :key="req.id"
            class="bg-slate-900/50 p-4 rounded-lg border border-slate-700"
          >
            <p class="font-bold text-gray-200">{{ req.title || req.id }}</p>
            <p class="text-sm text-gray-400 mt-1">{{ req.description }}</p>
            <div v-if="req.acceptance_criteria && req.acceptance_criteria.length" class="mt-2">
              <p class="text-xs font-medium text-indigo-300">Acceptance Criteria:</p>
              <ul class="mt-1 text-xs text-gray-400 list-disc pl-4">
                <li v-for="(criterion, idx) in req.acceptance_criteria" :key="idx">
                  {{ criterion }}
                </li>
              </ul>
            </div>
          </li>
        </ul>
        <!-- Show a notice if these are generated requirements -->
        <div
          v-if="
            requirements.length > 0 &&
            !data?.requirements?.length &&
            !data?.extracted_requirements?.length
          "
        >
          <p class="text-yellow-400 mt-2 mb-4">
            Requirements were auto-generated based on project information.
          </p>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="border-t border-white/10 pt-6 space-y-4">
        <div v-if="showFeedback" class="transition-all">
          <label for="feedback" class="block text-sm font-medium text-gray-300 mb-2"
            >Please provide feedback for revision:</label
          >
          <textarea
            v-model="feedbackText"
            id="feedback"
            rows="4"
            class="block w-full bg-slate-900 border-slate-700 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-white"
          ></textarea>
        </div>
        <div class="flex items-center justify-end gap-4">
          <button
            @click="handleTerminate"
            class="px-4 py-2 text-sm font-medium rounded-md text-white bg-red-600/80 hover:bg-red-600 transition-colors"
          >
            Terminate Process
          </button>
          <button
            @click="handleReject"
            class="px-4 py-2 text-sm font-medium rounded-md text-white bg-gray-600/80 hover:bg-gray-700 transition-colors"
          >
            {{ showFeedback ? "Submit Revision" : "Request Revision" }}
          </button>
          <button
            @click="emit('proceed')"
            class="px-4 py-2 text-sm font-medium rounded-md text-white bg-green-600/80 hover:bg-green-600 transition-colors"
          >
            Approve and Continue
          </button>
        </div>
      </div>
    </div>
    <div v-else class="text-center text-gray-400 py-8">
      <p>Waiting for BRD analysis data...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";

const props = defineProps<{
  data: any;
}>();

const emit = defineEmits<{
  (e: "proceed"): void;
  (e: "revise", feedback: string): void;
  (e: "end"): void;
}>();

const feedbackText = ref("");
const showFeedback = ref(false);

const projectName = computed(() => {
  return (
    props.data?.project_name ||
    props.data?.details?.project_name ||
    props.data?.brd_analysis_results?.project_name ||
    "Unknown Project"
  );
});

const projectSummary = computed(() => {
  return (
    props.data?.project_summary ||
    props.data?.summary ||
    props.data?.description ||
    props.data?.overview ||
    "No summary provided."
  );
});

const dataSource = computed(() => {
  if (props.data?.source) return props.data.source;
  if (props.data?.project_name) return "direct_project_data";
  if (props.data?.requirements) return "requirements_field";
  if (Array.isArray(props.data) && props.data.length > 0) return "array_data";
  return "unknown";
});

const requirements = computed(() => {
  const analysisData = props.data?.brd_analysis || props.data;
  console.log(
    "Looking for requirements in BRD analysis data with keys:",
    Object.keys(analysisData || {})
  );

  // Debug the contents of the requirements array if it exists
  if (analysisData?.requirements) {
    console.log("Requirements type:", typeof analysisData.requirements);
    console.log("Requirements isArray:", Array.isArray(analysisData.requirements));
    console.log("Requirements value:", analysisData.requirements);

    // If it's an array but empty, log a warning
    if (
      Array.isArray(analysisData.requirements) &&
      analysisData.requirements.length === 0
    ) {
      console.warn("Requirements array exists but is empty");
    }
  }

  // First try to get requirements directly from the analysis data
  if (
    analysisData?.requirements &&
    Array.isArray(analysisData.requirements) &&
    analysisData.requirements.length > 0
  ) {
    console.log(
      "Found non-empty requirements array in analysisData with length:",
      analysisData.requirements.length
    );
    return analysisData.requirements;
  }

  // Check for extracted_requirements which is what the BRD analyst actually produces
  if (
    analysisData?.extracted_requirements &&
    Array.isArray(analysisData.extracted_requirements) &&
    analysisData.extracted_requirements.length > 0
  ) {
    console.log(
      "Found non-empty extracted_requirements array in analysisData with length:",
      analysisData.extracted_requirements.length
    );
    return analysisData.extracted_requirements;
  }

  // If no requirements field, check if the entire object is already a requirements structure
  if (
    Array.isArray(analysisData) &&
    analysisData.length > 0 &&
    analysisData[0].id
  ) {
    console.log("analysisData itself appears to be a requirements array");
    return analysisData;
  }

  // Look in other common locations
  if (
    analysisData?.functional_requirements &&
    Array.isArray(analysisData.functional_requirements) &&
    analysisData.functional_requirements.length > 0
  ) {
    console.log("Found functional_requirements array in analysisData");
    return analysisData.functional_requirements;
  }

  // Handle case where requirements exist but may be nested in another field
  for (const key of Object.keys(analysisData || {})) {
    const nested = analysisData[key];
    if (nested && nested.requirements && Array.isArray(nested.requirements)) {
      console.log(`Found nested requirements in '${key}'`);
      return nested.requirements;
    }
  }
  
  // If we still have nothing, create fake requirements to ensure the UI doesn't look broken
  if (
    projectName.value !== "Unknown Project" &&
    projectSummary.value !== "No summary provided."
  ) {
    console.log("Generating fallback requirements from project info");
    return [
      {
        id: "gen-1",
        title: "Generated Main Feature",
        description: `Based on the summary, develop the core feature for ${projectName.value}.`,
        acceptance_criteria: [
          `The system should address the main goal: ${projectSummary.value.substring(0, 100)}...`,
        ],
      },
    ];
  }

  console.log("No requirements found, returning empty array.");
  return [];
});

function handleReject() {
  if (showFeedback.value && feedbackText.value.trim()) {
    emit("revise", feedbackText.value);
  } else {
    showFeedback.value = true;
  }
}

function handleTerminate() {
  emit("end");
}
</script>
