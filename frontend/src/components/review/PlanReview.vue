<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-2xl border border-white/10 space-y-6">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4">
      Human Review Required: Implementation Plan
    </h2>
    
    <div v-if="plan" class="bg-slate-900/70 border border-slate-700 p-4 rounded-lg max-h-[60vh] overflow-y-auto space-y-6">
      <!-- Project Overview Section -->
      <div v-if="plan.project_overview" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">Project Overview</h4>
        <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
          <p class="text-sm text-gray-300">{{ plan.project_overview }}</p>
        </div>
      </div>

      <!-- Timeline Estimation Section -->
      <div v-if="plan.timeline_estimation" class="space-y-3">
        <h4 class="text-md font-semibold text-blue-300 border-b border-slate-700 pb-2">Timeline Estimation</h4>
        <div class="bg-blue-900/30 p-4 rounded-lg border border-blue-700/50">
          <div v-if="plan.timeline_estimation.total_duration" class="mb-2">
            <p class="text-sm text-blue-100"><strong>Total Duration:</strong> {{ plan.timeline_estimation.total_duration }}</p>
          </div>
          <div v-if="plan.timeline_estimation.total_hours" class="mb-2">
            <p class="text-sm text-blue-100"><strong>Total Effort:</strong> {{ plan.timeline_estimation.total_hours }} hours</p>
          </div>
          <div v-if="plan.timeline_estimation.start_date" class="mb-2">
            <p class="text-sm text-blue-100"><strong>Start Date:</strong> {{ plan.timeline_estimation.start_date }}</p>
          </div>
          <div v-if="plan.timeline_estimation.end_date">
            <p class="text-sm text-blue-100"><strong>End Date:</strong> {{ plan.timeline_estimation.end_date }}</p>
          </div>
        </div>
      </div>

      <!-- Development Phases Section -->
      <div v-if="plan.development_phases && plan.development_phases.length" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">Development Phases</h4>
        <div class="space-y-4">
          <div v-for="(phase, index) in plan.development_phases" :key="phase.name || index" class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
            <div class="flex items-center justify-between mb-2">
              <h5 class="text-md font-semibold text-white">Phase {{ index + 1 }}: {{ phase.name || `Phase ${index + 1}` }}</h5>
              <span v-if="phase.estimated_duration_hours" class="text-xs bg-indigo-600 text-white px-2 py-1 rounded-full">{{ phase.estimated_duration_hours }}h</span>
            </div>
            <p class="text-sm text-gray-400 mb-3">{{ phase.description || 'No description provided.' }}</p>
            
            <!-- Phase Details Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Deliverables -->
              <div v-if="phase.deliverables && phase.deliverables.length > 0">
                <h6 class="text-sm font-semibold text-green-300 mb-2">Deliverables</h6>
                <ul class="list-disc list-inside text-sm text-gray-400 space-y-1">
                  <li v-for="deliverable in phase.deliverables" :key="deliverable">{{ deliverable }}</li>
                </ul>
              </div>
              
              <!-- Dependencies -->
              <div v-if="phase.dependencies && phase.dependencies.length > 0">
                <h6 class="text-sm font-semibold text-yellow-300 mb-2">Dependencies</h6>
                <ul class="list-disc list-inside text-sm text-gray-400 space-y-1">
                  <li v-for="dependency in phase.dependencies" :key="dependency">{{ dependency }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Risk Assessment Section -->
      <div v-if="plan.risk_assessment && plan.risk_assessment.length" class="space-y-3">
        <h4 class="text-md font-semibold text-red-300 border-b border-slate-700 pb-2">Risk Assessment</h4>
        <div class="grid grid-cols-1 gap-3">
          <div v-for="(risk, index) in plan.risk_assessment" :key="index" class="bg-red-900/30 p-4 rounded-lg border border-red-700/50">
            <div class="flex items-center justify-between mb-2">
              <p class="font-bold text-red-100">{{ risk.title || risk.name || `Risk ${index + 1}` }}</p>
              <span v-if="risk.severity" class="text-xs px-2 py-1 rounded-full" :class="getSeverityClass(risk.severity)">{{ risk.severity }}</span>
            </div>
            <p class="text-sm text-red-200 mb-2">{{ risk.description || risk.risk || 'No description provided.' }}</p>
            <div v-if="risk.mitigation" class="text-xs text-red-300">
              <strong>Mitigation:</strong> {{ risk.mitigation }}
            </div>
          </div>
        </div>
      </div>

      <!-- Resource Requirements Section -->
      <div v-if="plan.resource_requirements && plan.resource_requirements.length" class="space-y-3">
        <h4 class="text-md font-semibold text-purple-300 border-b border-slate-700 pb-2">Resource Requirements</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="(resource, index) in plan.resource_requirements" :key="index" class="bg-purple-900/30 p-4 rounded-lg border border-purple-700/50">
            <p class="font-bold text-purple-100">{{ resource.role || resource.type || `Resource ${index + 1}` }}</p>
            <p class="text-sm text-purple-200 mt-1">{{ resource.description || resource.responsibility || 'No description provided.' }}</p>
            <div v-if="resource.allocation" class="text-xs text-purple-300 mt-2">
              <strong>Allocation:</strong> {{ resource.allocation }}
            </div>
          </div>
        </div>
      </div>

      <!-- Deliverables Summary Section -->
      <div v-if="plan.deliverables && plan.deliverables.length" class="space-y-3">
        <h4 class="text-md font-semibold text-green-300 border-b border-slate-700 pb-2">Project Deliverables</h4>
        <div class="bg-green-900/30 p-4 rounded-lg border border-green-700/50">
          <ul class="list-disc list-inside text-sm text-green-100 space-y-1">
            <li v-for="deliverable in plan.deliverables" :key="deliverable">{{ deliverable }}</li>
          </ul>
        </div>
      </div>

      <!-- Raw Plan Debug (only show if other sections are empty) -->
      <div v-if="!hasDisplayableData" class="space-y-3">
        <h4 class="text-md font-semibold text-yellow-300 border-b border-slate-700 pb-2">Raw Plan Data</h4>
        <div class="bg-slate-800 p-3 rounded-lg border border-slate-600/50">
          <pre class="text-xs whitespace-pre-wrap font-mono text-gray-300 overflow-x-auto">{{ JSON.stringify(plan, null, 2) }}</pre>
        </div>
      </div>
    </div>
    <div v-else class="text-center text-gray-400 py-8">
      <p>Waiting for implementation plan data...</p>
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
          placeholder="e.g., 'Combine the first two phases into a single setup phase.'"
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

const plan = computed(() => {
  return props.data?.implementation_plan || props.data?.plan || props.data;
});

const hasDisplayableData = computed(() => {
  if (!plan.value) return false;
  return !!(
    plan.value.project_overview ||
    (plan.value.development_phases && plan.value.development_phases.length) ||
    plan.value.timeline_estimation ||
    (plan.value.risk_assessment && plan.value.risk_assessment.length) ||
    (plan.value.resource_requirements && plan.value.resource_requirements.length) ||
    (plan.value.deliverables && plan.value.deliverables.length)
  );
});

function getSeverityClass(severity: string) {
  const severityLower = severity.toLowerCase();
  if (severityLower === 'high') return 'bg-red-600 text-white';
  if (severityLower === 'medium') return 'bg-yellow-600 text-white';
  if (severityLower === 'low') return 'bg-green-600 text-white';
  return 'bg-gray-600 text-white';
}

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