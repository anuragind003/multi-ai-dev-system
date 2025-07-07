<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-2xl border border-white/10 space-y-6">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4">
      Human Review Required: System Design
    </h2>
    
    <div v-if="design" class="bg-slate-900/70 border border-slate-700 p-4 rounded-lg max-h-[60vh] overflow-y-auto space-y-6">
      <!-- Architecture Overview Section -->
      <div v-if="design.architecture_overview || design.architecture" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">Architecture Overview</h4>
        <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
          <p class="text-sm text-gray-300">{{ design.architecture_overview || design.architecture?.pattern || 'No architecture overview provided.' }}</p>
          <p v-if="design.architecture?.justification" class="text-sm text-gray-400 mt-2">{{ design.architecture.justification }}</p>
        </div>
      </div>

      <!-- Components Section -->
      <div v-if="design.components && design.components.length" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">System Components</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="component in design.components" :key="component.name" class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
            <p class="font-bold text-gray-200">{{ component.name }}</p>
            <p class="text-sm text-gray-400 mt-1">{{ component.description || component.purpose || 'No description provided.' }}</p>
            <div v-if="component.technologies" class="mt-2">
              <p class="text-xs text-blue-300"><strong>Technologies:</strong> {{ Array.isArray(component.technologies) ? component.technologies.join(', ') : component.technologies }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Data Flow Section -->
      <div v-if="design.data_flow" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">Data Flow</h4>
        <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
          <p class="text-sm text-gray-300">{{ design.data_flow }}</p>
        </div>
      </div>

      <!-- Security Considerations Section -->
      <div v-if="design.security_considerations && design.security_considerations.length" class="space-y-3">
        <h4 class="text-md font-semibold text-red-300 border-b border-slate-700 pb-2">Security Considerations</h4>
        <div class="grid grid-cols-1 gap-3">
          <div v-for="(security, index) in design.security_considerations" :key="index" class="bg-red-900/30 p-4 rounded-lg border border-red-700/50">
            <p class="text-sm text-red-100">{{ security }}</p>
          </div>
        </div>
      </div>

      <!-- Scalability Plan Section -->
      <div v-if="design.scalability_plan" class="space-y-3">
        <h4 class="text-md font-semibold text-green-300 border-b border-slate-700 pb-2">Scalability Plan</h4>
        <div class="bg-green-900/30 p-4 rounded-lg border border-green-700/50">
          <p class="text-sm text-green-100">{{ design.scalability_plan }}</p>
        </div>
      </div>

      <!-- Deployment Strategy Section -->
      <div v-if="design.deployment_strategy" class="space-y-3">
        <h4 class="text-md font-semibold text-purple-300 border-b border-slate-700 pb-2">Deployment Strategy</h4>
        <div class="bg-purple-900/30 p-4 rounded-lg border border-purple-700/50">
          <p class="text-sm text-purple-100">{{ design.deployment_strategy }}</p>
        </div>
      </div>

      <!-- Data Model Section -->
      <div v-if="design.data_model" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">Data Model</h4>
        <div class="bg-slate-800 p-3 rounded-lg border border-slate-600/50">
          <pre class="text-xs whitespace-pre-wrap font-mono text-gray-300 overflow-x-auto">{{ typeof design.data_model === 'string' ? design.data_model : JSON.stringify(design.data_model, null, 2) }}</pre>
        </div>
      </div>

      <!-- API Endpoints Section -->
      <div v-if="design.api_endpoints && design.api_endpoints.length" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">API Endpoints</h4>
        <div class="grid grid-cols-1 gap-3">
          <div v-for="endpoint in design.api_endpoints" :key="endpoint.path" class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
            <p class="font-bold text-gray-200">
              <span class="font-mono text-cyan-400 mr-2 rounded-md bg-slate-700 px-2 py-1 text-xs">{{ endpoint.method }}</span> 
              {{ endpoint.path }}
            </p>
            <p class="text-sm text-gray-400 mt-2">{{ endpoint.description }}</p>
            <div v-if="endpoint.parameters" class="mt-2">
              <p class="text-xs text-yellow-300"><strong>Parameters:</strong> {{ Array.isArray(endpoint.parameters) ? endpoint.parameters.join(', ') : endpoint.parameters }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Raw Design Debug (only show if other sections are empty) -->
      <div v-if="!hasDisplayableData" class="space-y-3">
        <h4 class="text-md font-semibold text-yellow-300 border-b border-slate-700 pb-2">Raw Design Data</h4>
        <div class="bg-slate-800 p-3 rounded-lg border border-slate-600/50">
          <pre class="text-xs whitespace-pre-wrap font-mono text-gray-300 overflow-x-auto">{{ JSON.stringify(design, null, 2) }}</pre>
        </div>
      </div>
    </div>
     <div v-else class="text-center text-gray-400 py-8">
      <p>Waiting for system design data...</p>
    </div>

    <!-- Action Buttons -->
    <div class="border-t border-white/10 pt-6 space-y-4">
      <div v-if="showFeedback" class="transition-all">
        <label for="feedback" class="block text-sm font-medium text-gray-300 mb-2">Please provide feedback for revision:</label>
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
import { ref, computed } from 'vue';

const props = defineProps<{
  data: any
}>();

const emit = defineEmits<{
  (e: 'proceed'): void;
  (e: 'revise', feedback: string): void;
  (e: 'end'): void;
}>();

const showFeedback = ref(false);
const feedbackText = ref('');

const design = computed(() => {
  // The comprehensive system design is now nested
  return props.data?.system_design || props.data;
});

const hasDisplayableData = computed(() => {
  if (!design.value) return false;
  return !!(
    design.value.architecture_overview || 
    design.value.architecture ||
    (design.value.components && design.value.components.length) ||
    design.value.data_flow ||
    (design.value.security_considerations && design.value.security_considerations.length) ||
    design.value.scalability_plan ||
    design.value.deployment_strategy ||
    design.value.data_model ||
    (design.value.api_endpoints && design.value.api_endpoints.length)
  );
});

function handleReject() {
  if (showFeedback.value && feedbackText.value.trim()) {
    emit('revise', feedbackText.value);
  } else {
    showFeedback.value = true;
  }
}

function handleTerminate() {
  emit('end');
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