<template>
  <div class="bg-slate-800/50 p-6 rounded-2xl shadow-2xl border border-white/10 space-y-6">
    <h2 class="text-xl font-bold text-white border-b border-white/10 pb-4">
      Human Review Required: Implementation Plan
    </h2>

    <div
      v-if="plan"
      class="bg-slate-900/70 border border-slate-700 p-4 rounded-lg max-h-[60vh] overflow-y-auto space-y-6"
    >
      <!-- Project Overview Section -->
      <div v-if="plan.project_summary" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">
          Project Overview
        </h4>
        <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
          <div v-if="plan.project_summary.title" class="mb-2">
            <p class="text-sm font-semibold text-gray-200">{{ plan.project_summary.title }}</p>
          </div>
          <p class="text-sm text-gray-300">
            {{ plan.project_summary.description || "No description provided." }}
          </p>
          <div v-if="plan.project_summary.overall_complexity" class="mt-2">
            <p class="text-xs text-indigo-300">
              <strong>Complexity:</strong> {{ plan.project_summary.overall_complexity }}
            </p>
          </div>
          <div v-if="plan.project_summary.estimated_duration" class="mt-2">
            <p class="text-xs text-indigo-300">
              <strong>Estimated Duration:</strong> {{ plan.project_summary.estimated_duration }}
            </p>
          </div>
        </div>
      </div>

      <!-- Timeline Section -->
      <div v-if="plan.timeline" class="space-y-3">
        <h4 class="text-md font-semibold text-blue-300 border-b border-slate-700 pb-2">Timeline</h4>
        <div class="bg-blue-900/30 p-4 rounded-lg border border-blue-700/50">
          <div v-if="plan.timeline.start_date" class="mb-2">
            <p class="text-sm text-blue-100">
              <strong>Start Date:</strong> {{ plan.timeline.start_date }}
            </p>
          </div>
          <div v-if="plan.timeline.end_date" class="mb-2">
            <p class="text-sm text-blue-100">
              <strong>End Date:</strong> {{ plan.timeline.end_date }}
            </p>
          </div>
          <div v-if="plan.timeline.overall_duration" class="mb-2">
            <p class="text-sm text-blue-100">
              <strong>Overall Duration:</strong> {{ plan.timeline.overall_duration }}
            </p>
          </div>
          <div v-if="plan.timeline.milestones && plan.timeline.milestones.length" class="mt-3">
            <p class="text-sm text-blue-100 mb-2"><strong>Milestones:</strong></p>
            <ul class="list-disc list-inside text-xs text-blue-200 space-y-1">
              <li v-for="milestone in plan.timeline.milestones" :key="milestone.name">
                {{ milestone.name }}: {{ milestone.date }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Development Phases Section -->
      <div v-if="plan.phases && plan.phases.length" class="space-y-3">
        <h4 class="text-md font-semibold text-indigo-300 border-b border-slate-700 pb-2">
          Development Phases
        </h4>
        <div class="space-y-4">
          <div
            v-for="(phase, index) in plan.phases"
            :key="phase.name || index"
            class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
          >
            <div class="flex items-center justify-between mb-2">
              <h5 class="text-md font-semibold text-white">
                Phase {{ index + 1 }}: {{ phase.name || `Phase ${index + 1}` }}
              </h5>
              <span
                v-if="phase.estimated_duration_hours"
                class="text-xs bg-indigo-600 text-white px-2 py-1 rounded-full"
                >{{ phase.estimated_duration_hours }}h</span
              >
            </div>
            <p class="text-sm text-gray-400 mb-3">
              {{ phase.description || "No description provided." }}
            </p>

            <!-- Phase Details Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Deliverables -->
              <div v-if="phase.deliverables && phase.deliverables.length > 0">
                <h6 class="text-sm font-semibold text-green-300 mb-2">Deliverables</h6>
                <ul class="list-disc list-inside text-sm text-gray-400 space-y-1">
                  <li v-for="deliverable in phase.deliverables" :key="deliverable">
                    {{ deliverable }}
                  </li>
                </ul>
              </div>

              <!-- Work Items (if available) -->
              <div v-if="phase.work_items && phase.work_items.length > 0">
                <h6 class="text-sm font-semibold text-yellow-300 mb-2">Work Items</h6>
                <ul class="list-disc list-inside text-sm text-gray-400 space-y-1">
                  <li v-for="workItem in phase.work_items.slice(0, 3)" :key="workItem.id">
                    {{ workItem.id }}: {{ workItem.description }}
                  </li>
                  <li v-if="phase.work_items.length > 3" class="text-xs text-gray-500">
                    ... and {{ phase.work_items.length - 3 }} more
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Risk Assessment Section -->
      <div v-if="plan.risks_and_mitigations && plan.risks_and_mitigations.length" class="space-y-3">
        <h4 class="text-md font-semibold text-red-300 border-b border-slate-700 pb-2">
          Risk Assessment
        </h4>
        <div class="grid grid-cols-1 gap-3">
          <div
            v-for="(risk, index) in plan.risks_and_mitigations"
            :key="index"
            class="bg-red-900/30 p-4 rounded-lg border border-red-700/50"
          >
            <div class="flex items-center justify-between mb-2">
              <p class="font-bold text-red-100">
                {{ risk.title || risk.name || risk.description || `Risk ${index + 1}` }}
              </p>
              <span
                v-if="risk.severity"
                class="text-xs px-2 py-1 rounded-full"
                :class="getSeverityClass(risk.severity)"
                >{{ risk.severity }}</span
              >
            </div>
            <p class="text-sm text-red-200 mb-2">
              {{ risk.description || risk.risk || "No description provided." }}
            </p>
            <div v-if="risk.mitigation" class="text-xs text-red-300">
              <strong>Mitigation:</strong> {{ risk.mitigation }}
            </div>
          </div>
        </div>
      </div>

      <!-- Resource Allocation Section -->
      <div v-if="plan.resource_allocation && plan.resource_allocation.length" class="space-y-3">
        <h4 class="text-md font-semibold text-purple-300 border-b border-slate-700 pb-2">
          Resource Allocation
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="(resource, index) in plan.resource_allocation"
            :key="index"
            class="bg-purple-900/30 p-4 rounded-lg border border-purple-700/50"
          >
            <p class="font-bold text-purple-100">{{ resource.role || `Resource ${index + 1}` }}</p>
            <div v-if="resource.count" class="text-sm text-purple-200 mt-1">
              <strong>Count:</strong> {{ resource.count }}
            </div>
            <div v-if="resource.estimated_time_allocation" class="text-xs text-purple-300 mt-2">
              <strong>Time Allocation:</strong> {{ resource.estimated_time_allocation }}
            </div>
            <div
              v-if="resource.phases && resource.phases.length"
              class="text-xs text-purple-300 mt-1"
            >
              <strong>Phases:</strong> {{ resource.phases.join(", ") }}
            </div>
          </div>
        </div>
      </div>

      <!-- Tech Stack Section -->
      <div v-if="plan.tech_stack && Object.keys(plan.tech_stack).length" class="space-y-3">
        <h4 class="text-md font-semibold text-green-300 border-b border-slate-700 pb-2">
          Technology Stack
        </h4>
        <div class="bg-green-900/30 p-4 rounded-lg border border-green-700/50 space-y-3">
          <div v-for="(category, key) in plan.tech_stack" :key="key">
            <h5 class="text-sm font-semibold text-green-100 capitalize">
              {{ String(key).replace(/_/g, " ") }}
            </h5>
            <div v-if="Array.isArray(category)" class="mt-1">
              <ul class="list-disc list-inside text-xs text-green-200">
                <li v-for="item in category" :key="item.name || item">
                  {{ item.name ? `${item.name}: ${item.reason}` : item }}
                </li>
              </ul>
            </div>
            <div v-else class="mt-1">
              <p class="text-xs text-green-200">
                {{ category.name || category }}: {{ category.reason }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Mermaid Diagram Section -->
      <div v-if="plan.timeline?.mermaid_diagram" class="space-y-3">
        <h4 class="text-md font-semibold text-cyan-300 border-b border-slate-700 pb-2">
          Timeline Gantt Chart
        </h4>
        <div
          ref="mermaidContainer"
          class="mermaid bg-slate-800 p-4 rounded-lg border border-slate-600/50 text-center"
        >
          {{ plan.timeline.mermaid_diagram }}
        </div>
      </div>

      <!-- Raw Plan Debug (only show if other sections are empty) -->
      <div v-if="!hasDisplayableData" class="space-y-3">
        <h4 class="text-md font-semibold text-yellow-300 border-b border-slate-700 pb-2">
          Raw Plan Data
        </h4>
        <div class="bg-slate-800 p-3 rounded-lg border border-slate-600/50">
          <pre class="text-xs whitespace-pre-wrap font-mono text-gray-300 overflow-x-auto">{{
            JSON.stringify(plan, null, 2)
          }}</pre>
        </div>
      </div>
    </div>
    <div v-else class="text-center text-gray-400 py-8">
      <p>Waiting for implementation plan data...</p>
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
import { ref, computed, onMounted, nextTick } from "vue";
import mermaid from "mermaid";

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
const mermaidContainer = ref<HTMLElement | null>(null);

const plan = computed(() => {
  // Get the implementation plan from the data structure
  const planData = props.data?.implementation_plan || props.data?.plan || props.data;

  console.log("PlanReview: Raw plan data:", planData);

  // Handle the simplified_workitem_backlog format from plan compiler
  if (planData && typeof planData === "object") {
    // Check if it's the simplified format
    if (planData.plan_type === "simplified_workitem_backlog") {
      console.log("PlanReview: Processing simplified_workitem_backlog format");
      return {
        project_summary: {
          title: planData.summary || "Implementation Plan",
          description: planData.summary || "Generated implementation plan",
          overall_complexity: planData.metadata?.project_complexity || "Medium",
          estimated_duration: planData.metadata?.estimated_total_time || "Unknown",
        },
        phases: planData.phases || [],
        timeline: planData.metadata?.timeline || null,
        risks_and_mitigations:
          planData.metadata?.risk_assessment?.risks?.map((risk: string) => ({
            risk: risk,
            severity: "Medium",
            mitigation: "To be addressed during implementation",
          })) || [],
        resource_allocation: [],
        tech_stack: planData.metadata?.tech_stack || {},
        total_work_items: planData.total_work_items || 0,
        plan_type: planData.plan_type,
      };
    }
    // Check if it's a direct work_items array (from raw data)
    else if (planData.work_items && Array.isArray(planData.work_items)) {
      console.log("PlanReview: Processing direct work_items format");

      // Group work items by agent role to create phases
      const phases: Record<string, any> = {};
      planData.work_items.forEach((item: any) => {
        const phaseName = item.agent_role || "General Development";
        if (!phases[phaseName]) {
          phases[phaseName] = {
            name: phaseName,
            work_items: [],
            description: `Tasks for ${phaseName}`,
          };
        }
        phases[phaseName].work_items.push(item);
      });

      return {
        project_summary: {
          title: planData.summary || "Implementation Plan",
          description: planData.summary || "Generated implementation plan",
          overall_complexity: planData.metadata?.project_complexity || "Medium",
          estimated_duration: planData.metadata?.estimated_total_time || "Unknown",
        },
        phases: Object.values(phases),
        timeline: planData.metadata?.timeline || null,
        risks_and_mitigations:
          planData.metadata?.risk_assessment?.risks?.map((risk: string) => ({
            risk: risk,
            severity: "Medium",
            mitigation: "To be addressed during implementation",
          })) || [],
        resource_allocation: [],
        tech_stack: planData.metadata?.tech_stack || {},
        total_work_items: planData.work_items.length || 0,
        plan_type: "work_items_direct",
      };
    }
    // Handle other plan formats
    else {
      console.log("PlanReview: Processing standard format");
      return planData;
    }
  }

  return null;
});

const hasDisplayableData = computed(() => {
  if (!plan.value) return false;
  return !!(
    plan.value.project_summary ||
    (plan.value.phases && plan.value.phases.length) ||
    plan.value.timeline ||
    (plan.value.risks_and_mitigations && plan.value.risks_and_mitigations.length) ||
    (plan.value.resource_allocation && plan.value.resource_allocation.length) ||
    plan.value.tech_stack
  );
});

onMounted(async () => {
  if (plan.value?.timeline?.mermaid_diagram && mermaidContainer.value) {
    await nextTick();
    try {
      mermaid.initialize({ startOnLoad: false, theme: "dark" });
      const { svg } = await mermaid.render("mermaid-graph", plan.value.timeline.mermaid_diagram);
      if (mermaidContainer.value) {
        mermaidContainer.value.innerHTML = svg;
      }
    } catch (error) {
      console.error("Mermaid rendering failed:", error);
      if (mermaidContainer.value) {
        mermaidContainer.value.innerText =
          "Error rendering diagram. Please check the Mermaid syntax.";
      }
    }
  }
});

function getSeverityClass(severity: string) {
  const severityLower = severity.toLowerCase();
  if (severityLower === "high") return "bg-red-600 text-white";
  if (severityLower === "medium") return "bg-yellow-600 text-white";
  if (severityLower === "low") return "bg-green-600 text-white";
  return "bg-gray-600 text-white";
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
