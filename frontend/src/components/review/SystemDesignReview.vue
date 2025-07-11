<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-2xl border border-white/10 space-y-6">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4">
      Human Review Required: System Design
    </h2>

    <div
      v-if="design"
      class="bg-slate-900/70 border border-slate-700 p-4 rounded-lg max-h-[60vh] overflow-y-auto space-y-6"
    >
      <!-- Enhanced System Design Visualization -->
      <SystemDesignVisualization :systemDesign="design" />

      <!-- Architecture Overview Section -->
      <div v-if="design.architecture" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">
          Architecture Overview
        </h4>
        <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
          <p class="text-sm text-gray-300">
            {{ design.architecture.pattern || "No architecture pattern provided." }}
          </p>
          <p v-if="design.architecture.justification" class="text-sm text-gray-400 mt-2">
            {{ design.architecture.justification }}
          </p>
          <div
            v-if="design.architecture.key_benefits && design.architecture.key_benefits.length"
            class="mt-3"
          >
            <p class="text-xs text-green-300 mb-1"><strong>Key Benefits:</strong></p>
            <ul class="list-disc list-inside text-xs text-gray-400">
              <li v-for="benefit in design.architecture.key_benefits" :key="benefit">
                {{ benefit }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Components Section -->
      <div v-if="design.components && design.components.length" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">
          System Components
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="component in design.components"
            :key="component.name"
            class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
          >
            <p class="font-bold text-gray-200">{{ component.name }}</p>
            <p class="text-sm text-gray-400 mt-1">
              {{ component.description || "No description provided." }}
            </p>
            <div v-if="component.technologies && component.technologies.length" class="mt-2">
              <p class="text-xs text-blue-300">
                <strong>Technologies:</strong> {{ component.technologies.join(", ") }}
              </p>
            </div>
            <div
              v-if="component.responsibilities && component.responsibilities.length"
              class="mt-2"
            >
              <p class="text-xs text-green-300"><strong>Responsibilities:</strong></p>
              <ul class="list-disc list-inside text-xs text-gray-400 mt-1">
                <li v-for="responsibility in component.responsibilities" :key="responsibility">
                  {{ responsibility }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Data Flow Section -->
      <div v-if="design.data_flow" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">
          Data Flow
        </h4>
        <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
          <p class="text-sm text-gray-300">{{ design.data_flow }}</p>
        </div>
      </div>

      <!-- Security Architecture Section -->
      <div v-if="design.security" class="space-y-3">
        <h4 class="text-md font-semibold text-red-300 border-b border-slate-700 pb-2">
          Security Architecture
        </h4>
        <div class="bg-red-900/30 p-4 rounded-lg border border-red-700/50 space-y-3">
          <div v-if="design.security.authentication_method">
            <p class="text-sm text-red-100">
              <strong>Authentication:</strong> {{ design.security.authentication_method }}
            </p>
          </div>
          <div v-if="design.security.authorization_strategy">
            <p class="text-sm text-red-100">
              <strong>Authorization:</strong> {{ design.security.authorization_strategy }}
            </p>
          </div>
          <div v-if="design.security.security_measures && design.security.security_measures.length">
            <p class="text-sm text-red-100 mb-2"><strong>Security Measures:</strong></p>
            <ul class="list-disc list-inside text-xs text-red-200 space-y-1">
              <li v-for="measure in design.security.security_measures" :key="measure.category">
                <strong>{{ measure.category }}:</strong> {{ measure.implementation }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Scalability & Performance Section -->
      <div
        v-if="
          design.scalability_and_performance &&
          Object.keys(design.scalability_and_performance).length
        "
        class="space-y-3"
      >
        <h4 class="text-md font-semibold text-green-300 border-b border-slate-700 pb-2">
          Scalability & Performance
        </h4>
        <div class="bg-green-900/30 p-4 rounded-lg border border-green-700/50 space-y-2">
          <div v-for="(value, key) in design.scalability_and_performance" :key="key">
            <p class="text-sm text-green-100">
              <strong class="capitalize">{{ String(key).replace(/_/g, " ") }}:</strong>
              <span v-if="Array.isArray(value)">
                <ul class="list-disc list-inside text-xs text-green-200 pl-4">
                  <li v-for="item in value" :key="item">{{ item }}</li>
                </ul>
              </span>
              <span v-else> {{ value }}</span>
            </p>
          </div>
        </div>
      </div>

      <!-- Deployment Strategy Section -->
      <div
        v-if="design.deployment_strategy && Object.keys(design.deployment_strategy).length"
        class="space-y-3"
      >
        <h4 class="text-md font-semibold text-purple-300 border-b border-slate-700 pb-2">
          Deployment Strategy
        </h4>
        <div class="bg-purple-900/30 p-4 rounded-lg border border-purple-700/50 space-y-2">
          <div v-for="(value, key) in design.deployment_strategy" :key="key">
            <p class="text-sm text-purple-100">
              <strong class="capitalize">{{ String(key).replace(/_/g, " ") }}:</strong> {{ value }}
            </p>
          </div>
        </div>
      </div>

      <!-- Data Model Section -->
      <div v-if="design.data_model" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">
          Data Model
        </h4>
        <div class="bg-slate-800 p-3 rounded-lg border border-slate-600/50">
          <div v-if="design.data_model.schema_type" class="mb-3">
            <p class="text-sm text-indigo-200">
              <strong>Schema Type:</strong> {{ design.data_model.schema_type }}
            </p>
          </div>
          <div v-if="design.data_model.tables && design.data_model.tables.length" class="space-y-2">
            <p class="text-sm text-indigo-200"><strong>Tables:</strong></p>
            <div
              v-for="table in design.data_model.tables"
              :key="table.name"
              class="bg-slate-700 p-2 rounded text-xs"
            >
              <p class="font-bold text-gray-200">{{ table.name }}</p>
              <p class="text-gray-400">{{ table.purpose }}</p>
              <div v-if="table.fields && table.fields.length" class="mt-1">
                <span class="text-blue-300">Fields: </span>
                <span class="text-gray-300">{{
                  table.fields.map((f: any) => f.name).join(", ")
                }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- API Endpoints Section -->
      <div
        v-if="
          design.api_endpoints &&
          design.api_endpoints.endpoints &&
          design.api_endpoints.endpoints.length
        "
        class="space-y-3"
      >
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">
          API Endpoints
        </h4>
        <div class="mb-3">
          <p class="text-sm text-indigo-200">
            <strong>API Style:</strong> {{ design.api_endpoints.style || "REST" }}
          </p>
          <p class="text-sm text-indigo-200">
            <strong>Authentication:</strong>
            {{ design.api_endpoints.authentication || "Not specified" }}
          </p>
        </div>
        <div class="grid grid-cols-1 gap-3">
          <div
            v-for="endpoint in design.api_endpoints.endpoints"
            :key="endpoint.path"
            class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
          >
            <p class="font-bold text-gray-200">
              <span
                class="font-mono text-cyan-400 mr-2 rounded-md bg-slate-700 px-2 py-1 text-xs"
                >{{ endpoint.method }}</span
              >
              {{ endpoint.path }}
            </p>
            <p class="text-sm text-gray-400 mt-2">
              {{ endpoint.purpose || endpoint.description || "No description provided." }}
            </p>
            <div v-if="endpoint.parameters && endpoint.parameters.length" class="mt-2">
              <p class="text-xs text-yellow-300"><strong>Parameters:</strong></p>
              <ul class="list-disc list-inside text-xs text-gray-400 mt-1">
                <li v-for="param in endpoint.parameters" :key="param.name">
                  {{ param.name }} ({{ param.type }}): {{ param.description }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Raw Design Debug (only show if other sections are empty) -->
      <div v-if="!hasDisplayableData" class="space-y-3">
        <h4 class="text-md font-semibold text-yellow-300 border-b border-slate-700 pb-2">
          Raw Design Data
        </h4>
        <div class="bg-slate-800 p-3 rounded-lg border border-slate-600/50">
          <pre class="text-xs whitespace-pre-wrap font-mono text-gray-300 overflow-x-auto">{{
            JSON.stringify(design, null, 2)
          }}</pre>
        </div>
      </div>
    </div>
    <div v-else class="text-center text-gray-400 py-8">
      <p>Waiting for system design data...</p>
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
          placeholder="e.g., 'Add a separate table for user profiles.'"
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
          @click="emit('proceed')"
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
import SystemDesignVisualization from "../SystemDesignVisualization.vue";

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

const design = computed(() => {
  // The comprehensive system design is now nested - match the actual agent output
  const systemDesign = props.data?.system_design || props.data;

  // If we have a properly structured ComprehensiveSystemDesignOutput, use it directly
  if (systemDesign && typeof systemDesign === "object") {
    return systemDesign;
  }

  return null;
});

const hasDisplayableData = computed(() => {
  if (!design.value) return false;
  return !!(
    design.value.architecture ||
    (design.value.components && design.value.components.length) ||
    design.value.data_flow ||
    design.value.data_model ||
    design.value.api_endpoints ||
    design.value.security ||
    design.value.scalability_and_performance ||
    design.value.deployment_strategy
  );
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
