<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-2xl border border-white/10 space-y-6">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4">
      Human Review Required: Tech Stack Recommendation
    </h2>

    <div v-if="processedOptions && Object.keys(processedOptions).length > 0" class="bg-slate-900/70 border border-slate-700 p-4 rounded-lg max-h-[50vh] overflow-y-auto space-y-6">
      <div v-for="(options, category_key) in processedOptions" :key="category_key" class="space-y-4">
        <h4 class="text-lg font-semibold text-indigo-300 capitalize border-b border-slate-700 pb-2">{{ formatCategory(String(category_key)) }}</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <label 
            v-for="option in options" 
            :key="option.name || option.pattern" 
            :for="`${String(category_key)}-${option.name || option.pattern}`"
            class="relative flex items-start p-4 rounded-lg cursor-pointer transition-all duration-200 ease-in-out group"
            :class="[isSelected(String(category_key), option.name || option.pattern) ? 'bg-indigo-700/40 border-indigo-500 shadow-lg' : 'bg-slate-800/60 border-slate-700 hover:border-indigo-500/50 hover:bg-slate-700/50']"
          >
            <input
              type="radio"
              :id="`${String(category_key)}-${option.name || option.pattern}`"
              :name="String(category_key)"
              :value="option.name || option.pattern"
              v-model="selectedOptions[String(category_key)]"
              class="mt-0.5 h-4 w-4 text-indigo-600 border-gray-300 focus:ring-indigo-500 cursor-pointer bg-slate-900"
            />
            <div class="ml-3 text-sm flex-grow">
              <p class="font-medium text-gray-100 group-hover:text-white">{{ option.name || option.pattern }} <span v-if="option.language">({{ option.language }})</span></p>
              <p class="text-gray-300 mt-1">{{ option.reasoning || option.description || 'No reasoning provided.' }}</p>
              <div v-if="option.pros && option.pros.length > 0" class="mt-2 text-green-300 text-xs">
                <strong>Pros:</strong> {{ option.pros.join(', ') }}
              </div>
              <div v-if="option.cons && option.cons.length > 0" class="mt-1 text-red-300 text-xs">
                <strong>Cons:</strong> {{ option.cons.join(', ') }}
              </div>
              <div v-if="option.key_libraries && option.key_libraries.length > 0" class="mt-1 text-blue-300 text-xs">
                <strong>Libraries:</strong> {{ option.key_libraries.join(', ') }}
              </div>
            </div>
            <span v-if="isSelected(String(category_key), option.name || option.pattern)" class="absolute top-2 right-2 text-indigo-200">
                <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>
            </span>
          </label>
        </div>
      </div>
      
      <!-- Risks Section -->
      <div v-if="processedRisks.length > 0" class="space-y-4">
        <h4 class="text-lg font-semibold text-red-300 capitalize border-b border-slate-700 pb-2">Identified Risks</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="risk in processedRisks" :key="risk.category" class="bg-red-900/30 p-4 rounded-lg border border-red-700/50">
            <p class="font-bold text-red-100">{{ risk.category }}</p>
            <p class="text-sm text-red-200 mt-1">{{ risk.description || 'No description provided.' }}</p>
            <p class="text-xs text-red-300 mt-1"><strong>Severity:</strong> {{ risk.severity || 'N/A' }}</p>
            <p class="text-xs text-red-300"><strong>Mitigation:</strong> {{ risk.mitigation || 'N/A' }}</p>
          </div>
        </div>
      </div>

      <!-- Synthesis Section -->
      <div v-if="processedSynthesis" class="space-y-4">
        <h4 class="text-lg font-semibold text-green-300 capitalize border-b border-slate-700 pb-2">Overall Synthesis</h4>
        <div class="bg-slate-800/60 p-4 rounded-lg border border-slate-700/50 text-gray-200 space-y-2">
          <p v-if="processedSynthesis.architecture_pattern"><strong>Architecture Pattern:</strong> {{ processedSynthesis.architecture_pattern }}</p>
          <p v-if="processedSynthesis.estimated_complexity"><strong>Estimated Complexity:</strong> {{ processedSynthesis.estimated_complexity }}</p>
          <p v-if="processedSynthesis.backend"><strong>Backend Summary:</strong> {{ formatSynthesis(processedSynthesis.backend) }}</p>
          <p v-if="processedSynthesis.frontend"><strong>Frontend Summary:</strong> {{ formatSynthesis(processedSynthesis.frontend) }}</p>
          <p v-if="processedSynthesis.database"><strong>Database Summary:</strong> {{ formatSynthesis(processedSynthesis.database) }}</p>
          <p v-if="processedSynthesis.key_libraries_tools && processedSynthesis.key_libraries_tools.length > 0">
            <strong>Key Libraries & Tools:</strong> {{ processedSynthesis.key_libraries_tools.map((lib: any) => lib.name).join(', ') }}
          </p>
        </div>
      </div>

    </div>
    <div v-else class="text-center text-gray-400 py-8">
      <p>Waiting for tech stack recommendation data...</p>
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
          placeholder="e.g., 'Let's use React instead of Vue for the frontend.'"
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
import { ref, computed, watch, reactive } from 'vue';

const props = defineProps<{
  data: any
}>();

const emit = defineEmits<{
  (e: 'proceed', selectedStack: { [key: string]: string }): void;
  (e: 'revise', feedback: string, selectedStack: { [key: string]: string }): void;
  (e: 'end'): void;
}>();

const showFeedback = ref(false);
const feedbackText = ref('');

const selectedOptions = reactive<{ [key: string]: string }>({});

const processedOptions = computed(() => {
  const data = props.data || {};
  const categories = [
    "frontend_options", "backend_options", "database_options", 
    "cloud_options", "architecture_options", "tool_options"
  ];
  
  const options: { [key: string]: any[] } = {};
  categories.forEach(category => {
    const categoryData = data[category] || [];
    options[category] = categoryData.map((item: any) => {
      // Initialize selectedOptions if not already set
      if (item.selected && !selectedOptions[category]) {
        selectedOptions[category] = item.name || item.pattern; // 'pattern' for architecture
      }
      return item;
    });
  });
  return options;
});

const processedRisks = computed(() => {
  return props.data?.risks || [];
});

const processedSynthesis = computed(() => {
  return props.data?.synthesis || {};
});

const formatCategory = (category: string) => {
  return category.replace(/_options$/, '').replace(/_/g, ' ');
};

const formatSynthesis = (synthesis: { [key: string]: string }) => {
  if (!synthesis || Object.keys(synthesis).length === 0) {
    return 'No summary provided.';
  }
  return Object.entries(synthesis)
    .map(([key, value]) => `${key.charAt(0).toUpperCase() + key.slice(1)}: ${value}`)
    .join('; ');
};

const isSelected = (category: string, optionValue: string) => {
  return selectedOptions[category] === optionValue;
};

watch(() => props.data, (newData) => {
  if (newData) {
    const categories = [
      "frontend_options", "backend_options", "database_options", 
      "cloud_options", "architecture_options", "tool_options"
    ];
    categories.forEach(category => {
      const selectedItem = newData[category]?.find((item: any) => item.selected);
      if (selectedItem) {
        selectedOptions[category] = selectedItem.name || selectedItem.pattern; // 'pattern' for architecture
      } else if (newData[category] && newData[category].length > 0) {
        // If no explicit selection, default to the first option
        selectedOptions[category] = newData[category][0].name || newData[category][0].pattern;
      }
    });
  }
}, { immediate: true });

function getSelectedStackForEmit() {
  const finalSelection: { [key: string]: string } = {};
  for (const category in selectedOptions) {
    if (selectedOptions[category]) {
      // Map internal category_key to the expected backend field name
      // e.g., 'frontend_options' -> 'frontend_selection'
      const backendKey = category.replace('_options', '_selection');
      finalSelection[backendKey] = selectedOptions[category];
    }
  }
  return finalSelection;
}

function handleApprove() {
  emit('proceed', getSelectedStackForEmit());
}

function handleReject() {
  if (showFeedback.value && feedbackText.value.trim()) {
    emit('revise', feedbackText.value, getSelectedStackForEmit());
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