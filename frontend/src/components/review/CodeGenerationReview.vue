<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-lg border border-white/10">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4 mb-6">Code Generation Review</h2>
    <p class="text-gray-300 mb-4">
      The following code artifacts have been generated. Please review them.
    </p>
    
    <!-- A simple representation of generated files -->
    <div v-if="data && data.generated_files" class="space-y-2">
      <div v-for="(content, filename) in data.generated_files" :key="filename" class="bg-slate-900/70 p-4 rounded-lg">
        <p class="font-mono text-indigo-300">{{ filename }}</p>
      </div>
    </div>
    <div v-else class="text-gray-400">
      No code generation data available.
    </div>

    <!-- Action Buttons -->
    <div class="mt-6 flex justify-end space-x-4">
      <button @click="$emit('end')" class="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold transition">
        End Workflow
      </button>
      <button @click="$emit('revise')" class="px-4 py-2 rounded-lg bg-yellow-500 hover:bg-yellow-600 text-white font-semibold transition">
        Request Revision
      </button>
      <button @click="$emit('proceed')" class="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold transition">
        Approve & Finalize
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  data: any;
}>();

defineEmits(['proceed', 'revise', 'end']);
</script> 