<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-2xl border border-white/10">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4 mb-6">
      Workflow Progress
    </h2>
    <ul class="space-y-4">
      <li v-for="(step, index) in steps" :key="step.id" class="flex items-center">
        <span
          :class="[
            'flex items-center justify-center w-8 h-8 rounded-full text-white font-bold transition-colors shadow-lg',
            getStepStatus(step.id) === 'completed'
              ? 'bg-green-500'
              : getStepStatus(step.id) === 'active'
              ? 'bg-indigo-500 animate-pulse'
              : 'bg-slate-600',
          ]"
        >
          <CheckIcon v-if="getStepStatus(step.id) === 'completed'" class="w-5 h-5" />
          <span v-else>{{ index + 1 }}</span>
        </span>
        <span
          class="ml-4 text-base font-medium"
          :class="[getStepStatus(step.id) === 'active' ? 'text-indigo-300' : 'text-gray-300']"
        >
          {{ step.label }}
        </span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useWorkflowStore } from '@/stores/workflow';
import { storeToRefs } from 'pinia';
import { CheckIcon } from '@heroicons/vue/24/solid';

const workflowStore = useWorkflowStore();
const { completedStages, status } = storeToRefs(workflowStore);

const steps = [
  { id: 'brd_analysis', label: 'Requirements Analysis' },
  { id: 'tech_stack_recommendation', label: 'Tech Stack Recommendation' },
  { id: 'system_design', label: 'System Design' },
  { id: 'implementation_plan', label: 'Implementation Planning' },
  { id: 'code_generation', label: 'Code Generation' },
];

const getStepStatus = (stepId: string): 'completed' | 'active' | 'pending' => {
  // Check if this stage is completed
  if (completedStages.value[stepId]) {
    return 'completed';
  }
  
  // Map step IDs to their expected completion order
  const stepOrder = ['brd_analysis', 'tech_stack_recommendation', 'system_design', 'implementation_plan', 'code_generation'];
  const currentStepIndex = stepOrder.indexOf(stepId);
  
  // Count how many previous steps are completed
  let previousStepsCompleted = 0;
  for (let i = 0; i < currentStepIndex; i++) {
    if (completedStages.value[stepOrder[i]]) {
      previousStepsCompleted++;
    }
  }
  
  // A step is active if:
  // 1. All previous steps are completed
  // 2. This step is not completed
  // 3. Workflow is running or paused (not idle or error)
  if (previousStepsCompleted === currentStepIndex && 
      !completedStages.value[stepId] && 
      (status.value === 'running' || status.value === 'paused')) {
    return 'active';
  }

  return 'pending';
};
</script> 