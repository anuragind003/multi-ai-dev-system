<template>
  <div class="mb-6 p-4 bg-slate-800/50 rounded-2xl border border-white/10">
    <h3 class="text-lg font-medium mb-4 text-white">Workflow Progress</h3>
    <div class="flex flex-wrap gap-3">
      <div 
        v-for="(step, index) in workflowSteps" 
        :key="index"
        :class="[
          'px-3 py-1.5 rounded-full text-xs font-semibold flex items-center transition-all duration-300 shadow-md',
          currentStepIndex === index ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white ring-2 ring-indigo-400' : 
            completedSteps.includes(step.id) ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white' : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
        ]"
      >
        <CheckCircleIcon v-if="completedSteps.includes(step.id)" class="mr-1.5 h-4 w-4" />
        <span v-else-if="currentStepIndex === index" class="animate-pulse mr-1.5 text-lg">●</span>
        <span>{{ step.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { CheckCircleIcon } from '@heroicons/vue/24/solid';

const props = defineProps({
  currentStep: {
    type: String,
    required: true
  },
  completedSteps: {
    type: Array as () => string[],
    default: () => []
  }
});

const workflowSteps = [
  { id: 'brd_analysis_node', label: 'BRD Analysis' },
  { id: 'human_approval_brd_node', label: 'BRD Approval' },
  { id: 'tech_stack_recommendation_node', label: 'Tech Stack' },
  { id: 'system_design_node', label: 'System Design' },
  { id: 'planning_node', label: 'Planning' },
  { id: 'code_generation_node', label: 'Code Generation' }
];

const currentStepIndex = computed(() => {
  const index = workflowSteps.findIndex(step => step.id === props.currentStep);
  return index >= 0 ? index : -1;
});
</script>