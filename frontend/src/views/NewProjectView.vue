<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-3xl font-bold">Create New Project</h1>
      <p class="text-gray-500">
        Paste your Business Requirements Document (BRD) below to get started.
      </p>
    </div>
    <div class="bg-white p-6 rounded-lg shadow-md">
      <label for="brd" class="block text-lg font-medium text-gray-700"
        >Business Requirements Document</label
      >
      <textarea
        id="brd"
        v-model="brdContent"
        :disabled="workflow.status === 'running'"
        rows="15"
        class="mt-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
        placeholder="Provide a detailed description of your project requirements..."
      ></textarea>
    </div>
    <div class="flex justify-end">
      <button
        @click="handleStartWorkflow"
        :disabled="workflow.status === 'running'"
        class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-6 py-3 text-base font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span v-if="workflow.status === 'running'">Processing...</span>
        <span v-else>Start Build</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useWorkflowStore } from "@/stores/workflow";

const brdContent = ref("");
const router = useRouter();
const workflow = useWorkflowStore();

const handleStartWorkflow = async () => {
  if (!brdContent.value.trim()) {
    alert("Please provide the Business Requirements Document.");
    return;
  }

  await workflow.startWorkflow(brdContent.value);

  if (workflow.status === "success" || workflow.status === "running") {
    router.push("/workflow");
  } else if (workflow.status === "error") {
    alert(`Workflow failed: ${workflow.error}`);
  }
};
</script>
