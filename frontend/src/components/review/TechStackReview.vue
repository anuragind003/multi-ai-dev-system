<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-2xl border border-white/10 space-y-6">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4">
      Human Review Required: Tech Stack Recommendation
    </h2>

    <div
      v-if="techStackData && Object.keys(techStackData).length > 0"
      class="bg-slate-900/70 border border-slate-700 p-4 rounded-lg max-h-[50vh] overflow-y-auto space-y-6"
    >
      <!-- Tech Stack Recommendations -->
      <div class="space-y-4">
        <h4 class="text-lg font-semibold text-indigo-300 border-b border-slate-700 pb-2">
          Recommended Technology Stack
        </h4>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Frontend -->
          <div
            v-if="techStackData.frontend"
            class="bg-slate-800/60 p-4 rounded-lg border border-slate-700"
          >
            <h5 class="font-bold text-blue-200 mb-2">Frontend</h5>
            <p class="font-medium text-gray-100">{{ techStackData.frontend.name }}</p>
            <p class="text-sm text-gray-300 mt-1">{{ techStackData.frontend.reasoning }}</p>
          </div>

          <!-- Backend -->
          <div
            v-if="techStackData.backend"
            class="bg-slate-800/60 p-4 rounded-lg border border-slate-700"
          >
            <h5 class="font-bold text-green-200 mb-2">Backend</h5>
            <p class="font-medium text-gray-100">{{ techStackData.backend.name }}</p>
            <p class="text-sm text-gray-300 mt-1">{{ techStackData.backend.reasoning }}</p>
          </div>

          <!-- Database -->
          <div
            v-if="techStackData.database"
            class="bg-slate-800/60 p-4 rounded-lg border border-slate-700"
          >
            <h5 class="font-bold text-purple-200 mb-2">Database</h5>
            <p class="font-medium text-gray-100">{{ techStackData.database.name }}</p>
            <p class="text-sm text-gray-300 mt-1">{{ techStackData.database.reasoning }}</p>
          </div>

          <!-- Cloud -->
          <div
            v-if="techStackData.cloud"
            class="bg-slate-800/60 p-4 rounded-lg border border-slate-700"
          >
            <h5 class="font-bold text-yellow-200 mb-2">Cloud Platform</h5>
            <p class="font-medium text-gray-100">{{ techStackData.cloud.name }}</p>
            <p class="text-sm text-gray-300 mt-1">{{ techStackData.cloud.reasoning }}</p>
          </div>

          <!-- Architecture -->
          <div
            v-if="techStackData.architecture"
            class="bg-slate-800/60 p-4 rounded-lg border border-slate-700"
          >
            <h5 class="font-bold text-red-200 mb-2">Architecture</h5>
            <p class="font-medium text-gray-100">{{ techStackData.architecture.name }}</p>
            <p class="text-sm text-gray-300 mt-1">{{ techStackData.architecture.reasoning }}</p>
          </div>
        </div>
      </div>

      <!-- Tools -->
      <div v-if="techStackData.tools && techStackData.tools.length > 0" class="space-y-4">
        <h4 class="text-lg font-semibold text-cyan-300 border-b border-slate-700 pb-2">
          Development Tools
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="tool in techStackData.tools"
            :key="tool.name"
            class="bg-slate-800/60 p-4 rounded-lg border border-slate-700"
          >
            <p class="font-medium text-gray-100">{{ tool.name }}</p>
            <p class="text-sm text-gray-300 mt-1">{{ tool.reasoning }}</p>
          </div>
        </div>
      </div>

      <!-- Synthesis Section -->
      <div
        v-if="techStackData.synthesis && Object.keys(techStackData.synthesis).length > 0"
        class="space-y-4"
      >
        <h4 class="text-lg font-semibold text-green-300 border-b border-slate-700 pb-2">
          Overall Analysis
        </h4>
        <div
          class="bg-slate-800/60 p-4 rounded-lg border border-slate-700/50 text-gray-200 space-y-2"
        >
          <p v-if="techStackData.synthesis.architecture_pattern">
            <strong>Architecture Pattern:</strong>
            {{ techStackData.synthesis.architecture_pattern }}
          </p>
          <p v-if="techStackData.synthesis.estimated_complexity">
            <strong>Estimated Complexity:</strong>
            {{ techStackData.synthesis.estimated_complexity }}
          </p>
          <div v-if="techStackData.synthesis.deployment_environment">
            <p>
              <strong>Deployment:</strong>
              {{ techStackData.synthesis.deployment_environment.hosting }} with
              {{ techStackData.synthesis.deployment_environment.ci_cd }}
            </p>
          </div>
          <div
            v-if="
              techStackData.synthesis.key_libraries_tools &&
              techStackData.synthesis.key_libraries_tools.length > 0
            "
          >
            <p>
              <strong>Key Libraries & Tools:</strong>
              {{
                techStackData.synthesis.key_libraries_tools.map((lib: any) => lib.name).join(", ")
              }}
            </p>
          </div>
        </div>
      </div>

      <!-- Design Justification -->
      <div v-if="techStackData.design_justification" class="space-y-4">
        <h4 class="text-lg font-semibold text-orange-300 border-b border-slate-700 pb-2">
          Design Justification
        </h4>
        <div class="bg-slate-800/60 p-4 rounded-lg border border-slate-700/50 text-gray-200">
          <p>{{ techStackData.design_justification }}</p>
        </div>
      </div>
    </div>
    <div v-else class="text-center text-gray-400 py-8">
      <p>Waiting for tech stack recommendation data...</p>
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
          placeholder="e.g., 'Please use Vue.js instead of React for the frontend' or 'Consider using MySQL instead of PostgreSQL'"
        ></textarea>
      </div>
      <div class="flex items-center justify-end gap-4">
        <button
          @click="handleTerminate"
          class="px-4 py-2 text-sm font-medium rounded-md text-white bg-red-600/80 hover:bg-red-600 transition-colors"
        >
          Stop Workflow
        </button>
        <button
          @click="handleReject"
          class="px-4 py-2 text-sm font-medium rounded-md text-white bg-gray-600/80 hover:bg-gray-700 transition-colors"
        >
          {{ showFeedback ? "Submit Revision" : "Request Revision" }}
        </button>
        <button
          @click="handleApprove"
          class="px-6 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition hover:scale-105"
        >
          Approve & Proceed
        </button>
      </div>
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

const showFeedback = ref(false);
const feedbackText = ref("");

const techStackData = computed(() => {
  return props.data || {};
});

function handleApprove() {
  emit("proceed");
}

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

<style scoped>
.review-card {
  background-color: #1a1a1a;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 24px;
  color: #fff;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 24px;
}
.feedback-section {
  margin-top: 16px;
}
</style>
