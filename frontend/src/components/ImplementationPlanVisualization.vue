<template>
  <div class="implementation-plan-visualization">
    <div class="flex justify-between items-center mb-4">
      <h4 class="text-lg font-semibold text-indigo-300">Implementation Timeline</h4>
      <div class="flex space-x-2">
        <button
          @click="toggleViewType"
          class="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 transition"
        >
          {{
            viewType === "gantt"
              ? "Show Dependencies"
              : viewType === "graph"
              ? "Show Details"
              : "Show Gantt"
          }}
        </button>
        <button
          v-if="viewType !== 'details'"
          @click="refreshDiagram"
          class="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition"
        >
          Refresh
        </button>
      </div>
    </div>

    <!-- Gantt Chart View -->
    <div v-if="viewType === 'gantt'" class="mb-6">
      <MermaidDiagram
        ref="ganttRef"
        :diagram="ganttCode"
        theme="default"
        height="400px"
        :config="ganttConfig"
      />
      <div class="mt-2 text-xs text-gray-400 text-center">
        Interactive Gantt Chart - Click and drag to explore timeline
      </div>
    </div>

    <!-- Dependency Graph View -->
    <div v-else-if="viewType === 'graph'" class="mb-6">
      <MermaidDiagram
        ref="graphRef"
        :diagram="dependencyGraphCode"
        theme="default"
        height="500px"
        :config="graphConfig"
      />

      <!-- Legend for dependency graph -->
      <div class="mt-4 p-3 bg-slate-800 rounded-lg border border-slate-600">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Legend</h5>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-2 text-xs text-gray-400">
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-blue-500 rounded"></div>
            <span>Architecture</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-green-500 rounded"></div>
            <span>Backend</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-purple-500 rounded"></div>
            <span>Frontend</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-orange-500 rounded"></div>
            <span>Database</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Detailed View (Fallback) -->
    <div v-else class="space-y-4">
      <!-- Project Overview -->
      <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Project Overview</h5>
        <p class="text-sm text-gray-400">{{ implementationPlan?.project_overview || "N/A" }}</p>
      </div>

      <!-- Development Phases -->
      <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Development Phases</h5>
        <div v-if="implementationPlan?.phases?.length" class="space-y-3">
          <div
            v-for="(phase, index) in implementationPlan.phases"
            :key="index"
            class="p-3 bg-slate-700 rounded border-l-4"
            :class="{
              'border-blue-500': phase.name?.toLowerCase().includes('architecture'),
              'border-green-500': phase.name?.toLowerCase().includes('backend'),
              'border-purple-500': phase.name?.toLowerCase().includes('frontend'),
              'border-orange-500': phase.name?.toLowerCase().includes('database'),
              'border-gray-500': true,
            }"
          >
            <div class="flex justify-between items-start mb-2">
              <h6 class="font-medium text-gray-200">{{ phase.name || `Phase ${index + 1}` }}</h6>
              <span class="text-xs text-gray-400">{{ phase.duration || "TBD" }}</span>
            </div>
            <p class="text-xs text-gray-400 mb-2">{{ phase.description }}</p>

            <!-- Work Items -->
            <div v-if="phase.work_items?.length" class="mt-2">
              <h6 class="text-xs font-medium text-gray-300">Work Items:</h6>
              <div class="mt-1 space-y-1">
                <div
                  v-for="item in phase.work_items"
                  :key="item.id"
                  class="text-xs bg-slate-600 p-2 rounded flex justify-between items-center"
                >
                  <div>
                    <span class="text-gray-200">{{ item.title || item.description }}</span>
                    <span v-if="item.agent_role" class="ml-2 text-blue-300"
                      >({{ item.agent_role }})</span
                    >
                  </div>
                  <span
                    class="px-2 py-1 rounded text-xs"
                    :class="{
                      'bg-green-600 text-white': item.status === 'completed',
                      'bg-yellow-600 text-white': item.status === 'in_progress',
                      'bg-gray-600 text-white': item.status === 'pending',
                    }"
                  >
                    {{ item.status || "pending" }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Dependencies -->
            <div v-if="phase.dependencies?.length" class="mt-2">
              <h6 class="text-xs font-medium text-gray-300">Dependencies:</h6>
              <div class="mt-1 text-xs text-gray-400">
                {{ phase.dependencies.join(", ") }}
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-gray-500 text-sm">No development phases defined</div>
      </div>

      <!-- Timeline Summary -->
      <div v-if="timelineSummary" class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Timeline Summary</h5>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <span class="text-gray-400">Total Phases:</span>
            <span class="text-gray-200 ml-2">{{ timelineSummary.totalPhases }}</span>
          </div>
          <div>
            <span class="text-gray-400">Total Work Items:</span>
            <span class="text-gray-200 ml-2">{{ timelineSummary.totalWorkItems }}</span>
          </div>
          <div>
            <span class="text-gray-400">Estimated Duration:</span>
            <span class="text-gray-200 ml-2">{{ timelineSummary.estimatedDuration }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import MermaidDiagram from "./MermaidDiagram.vue";

interface WorkItem {
  id: string;
  title?: string;
  description: string;
  agent_role?: string;
  status?: "pending" | "in_progress" | "completed";
  dependencies?: string[];
  estimated_hours?: number;
}

interface DevelopmentPhase {
  name: string;
  description: string;
  duration?: string;
  work_items?: WorkItem[];
  dependencies?: string[];
}

interface ImplementationPlanData {
  project_overview?: string;
  phases?: DevelopmentPhase[];
  work_items?: WorkItem[];
  estimated_timeline?: string;
  total_work_items?: number;
  plan_type?: string;
  summary?: string;
  metadata?: any;
}

interface Props {
  implementationPlan: ImplementationPlanData | null;
}

const props = defineProps<Props>();

const ganttRef = ref();
const graphRef = ref();
const viewType = ref<"gantt" | "graph" | "details">("gantt");

const ganttConfig = {
  theme: "default",
  gantt: {
    dateFormat: "YYYY-MM-DD",
    axisFormat: "%m/%d",
    tickInterval: "1day",
    gridLineStartPadding: 350,
  },
};

const graphConfig = {
  theme: "default",
  themeVariables: {
    primaryColor: "#3b82f6",
    primaryTextColor: "#1f2937",
    primaryBorderColor: "#2563eb",
    lineColor: "#6b7280",
    secondaryColor: "#10b981",
    tertiaryColor: "#8b5cf6",
  },
};

const ganttCode = computed(() => {
  // Check if we have implementation plan data
  if (!props.implementationPlan) {
    return `
gantt
    title Implementation Plan
    dateFormat YYYY-MM-DD
    section Planning
    No plan data available :2024-01-01, 1d
`;
  }

  // Handle simplified_workitem_backlog format from plan compiler
  let phases = props.implementationPlan.phases;

  // If no phases but we have work_items directly, create phases from work_items
  if ((!phases || phases.length === 0) && props.implementationPlan.work_items) {
    console.log("ImplementationPlanVisualization: Creating phases from work_items");
    const phasesMap: Record<string, any> = {};
    props.implementationPlan.work_items.forEach((item: any) => {
      const phaseName = item.agent_role || "General Development";
      if (!phasesMap[phaseName]) {
        phasesMap[phaseName] = {
          name: phaseName,
          work_items: [],
        };
      }
      phasesMap[phaseName].work_items.push(item);
    });
    phases = Object.values(phasesMap);
  }

  // If still no phases, show error
  if (!phases || phases.length === 0) {
    console.log("ImplementationPlanVisualization: No phases found, showing error");
    return `
gantt
    title Implementation Plan
    dateFormat YYYY-MM-DD
    section Default
    No phases defined :2024-01-01, 1d
`;
  }

  let gantt = "gantt\n";
  gantt += "    title Implementation Timeline\n";
  gantt += "    dateFormat YYYY-MM-DD\n";
  gantt += "    axisFormat %m/%d\n\n";

  const today = new Date();
  let currentDate = new Date(today);

  phases.forEach((phase: any, phaseIndex: number) => {
    const sectionName = (phase.name || `Phase ${phaseIndex + 1}`).replace(/[^a-zA-Z0-9\s]/g, "");
    gantt += `    section ${sectionName}\n`;

    if (phase.work_items?.length) {
      phase.work_items.forEach((item: any, itemIndex: number) => {
        const taskName = (item.title || item.description || "Unnamed Task")
          .substring(0, 50)
          .replace(/[^a-zA-Z0-9\s]/g, "");
        const startDate = new Date(currentDate);

        // Handle different time formats (e.g., "4 hours", "2 days")
        let duration = 2; // default 2 days
        if (item.estimated_time) {
          const timeMatch = item.estimated_time.match(/(\d+)\s*(hour|day)/i);
          if (timeMatch) {
            const value = parseInt(timeMatch[1]);
            const unit = timeMatch[2].toLowerCase();
            duration = unit === "hour" ? Math.max(1, Math.ceil(value / 8)) : value;
          }
        } else if (item.estimated_hours) {
          duration = Math.max(1, Math.ceil(item.estimated_hours / 8));
        }

        const endDate = new Date(startDate);
        endDate.setDate(endDate.getDate() + duration);

        const status =
          item.status === "completed" ? "done" : item.status === "in_progress" ? "active" : "task";

        gantt += `    ${taskName} :${status}, ${
          startDate.toISOString().split("T")[0]
        }, ${duration}d\n`;

        currentDate = new Date(endDate);
        currentDate.setDate(currentDate.getDate() + 1); // Add buffer day
      });
    } else {
      // If no work items, add a phase-level task
      const phaseName = (phase.name || `Phase ${phaseIndex + 1}`).replace(/[^a-zA-Z0-9\s]/g, "");
      const phaseDuration = phase.duration ? parseInt(phase.duration.match(/\d+/)?.[0] || "5") : 5;

      gantt += `    ${phaseName} :task, ${
        currentDate.toISOString().split("T")[0]
      }, ${phaseDuration}d\n`;
      currentDate.setDate(currentDate.getDate() + phaseDuration + 1);
    }

    gantt += "\n";
  });

  return gantt;
});

const dependencyGraphCode = computed(() => {
  if (!props.implementationPlan?.phases?.length) {
    return `
graph TD
    A[No Implementation Plan] --> B[Please complete planning first]
    style A fill:#ef4444,stroke:#dc2626,color:#fff
    style B fill:#6b7280,stroke:#4b5563,color:#fff
`;
  }

  let graph = "graph TD\n";
  const workItems: WorkItem[] = [];

  // Collect all work items from all phases
  props.implementationPlan.phases.forEach((phase) => {
    if (phase.work_items) {
      workItems.push(...phase.work_items);
    }
  });

  // If no work items but have phases, use phases
  if (workItems.length === 0) {
    props.implementationPlan.phases.forEach((phase, index) => {
      const nodeId = `P${index}`;
      const phaseName = phase.name || `Phase ${index + 1}`;
      const safeName = phaseName.replace(/[^a-zA-Z0-9]/g, "_");
      graph += `    ${nodeId}["${phaseName}"]\n`;
    });

    // Connect phases sequentially
    for (let i = 0; i < props.implementationPlan.phases.length - 1; i++) {
      graph += `    P${i} --> P${i + 1}\n`;
    }

    // Style phases
    props.implementationPlan.phases.forEach((phase, index) => {
      const nodeId = `P${index}`;
      const color = getPhaseColor(phase.name || "default");
      graph += `    style ${nodeId} fill:${color},stroke:#2563eb,color:#fff\n`;
    });
  } else {
    // Create nodes for work items
    workItems.forEach((item, index) => {
      const nodeId = `W${index}`;
      const itemName = (item.title || item.description).substring(0, 30);
      const agentRole = item.agent_role ? `<br/><small>${item.agent_role}</small>` : "";
      graph += `    ${nodeId}["${itemName}${agentRole}"]\n`;
    });

    // Add dependencies
    workItems.forEach((item, index) => {
      if (item.dependencies?.length) {
        item.dependencies.forEach((depId) => {
          const depIndex = workItems.findIndex((w) => w.id === depId);
          if (depIndex >= 0) {
            graph += `    W${depIndex} --> W${index}\n`;
          }
        });
      }
    });

    // If no explicit dependencies, create logical flow based on agent roles
    if (!workItems.some((item) => item.dependencies?.length)) {
      const architecture = workItems.filter((item) =>
        item.agent_role?.toLowerCase().includes("architecture")
      );
      const database = workItems.filter((item) =>
        item.agent_role?.toLowerCase().includes("database")
      );
      const backend = workItems.filter((item) =>
        item.agent_role?.toLowerCase().includes("backend")
      );
      const frontend = workItems.filter((item) =>
        item.agent_role?.toLowerCase().includes("frontend")
      );

      // Create logical dependencies: Architecture -> Database -> Backend -> Frontend
      const createDependencies = (from: WorkItem[], to: WorkItem[]) => {
        from.forEach((fromItem) => {
          to.forEach((toItem) => {
            const fromIndex = workItems.indexOf(fromItem);
            const toIndex = workItems.indexOf(toItem);
            graph += `    W${fromIndex} --> W${toIndex}\n`;
          });
        });
      };

      if (architecture.length && database.length) createDependencies(architecture, database);
      if (database.length && backend.length) createDependencies(database, backend);
      if (backend.length && frontend.length) createDependencies(backend, frontend);
    }

    // Style work items based on agent role
    workItems.forEach((item, index) => {
      const nodeId = `W${index}`;
      const color = getAgentRoleColor(item.agent_role || "");
      graph += `    style ${nodeId} fill:${color},stroke:#2563eb,color:#fff\n`;
    });
  }

  return graph;
});

const getPhaseColor = (phaseName: string): string => {
  const phase = phaseName.toLowerCase();
  if (phase.includes("architecture")) return "#3b82f6";
  if (phase.includes("database")) return "#f59e0b";
  if (phase.includes("backend")) return "#10b981";
  if (phase.includes("frontend")) return "#8b5cf6";
  return "#6b7280";
};

const getAgentRoleColor = (agentRole: string): string => {
  const role = agentRole.toLowerCase();
  if (role.includes("architecture")) return "#3b82f6";
  if (role.includes("database")) return "#f59e0b";
  if (role.includes("backend")) return "#10b981";
  if (role.includes("frontend")) return "#8b5cf6";
  return "#6b7280";
};

const timelineSummary = computed(() => {
  if (!props.implementationPlan) return null;

  // Handle simplified_workitem_backlog format or direct work_items
  let phases = props.implementationPlan.phases || [];
  let totalWorkItems = props.implementationPlan.total_work_items || 0;

  // If no phases but we have work_items, create phases and count
  if (phases.length === 0 && props.implementationPlan.work_items) {
    const phasesMap: Record<string, any> = {};
    props.implementationPlan.work_items.forEach((item: any) => {
      const phaseName = item.agent_role || "General Development";
      if (!phasesMap[phaseName]) {
        phasesMap[phaseName] = {
          name: phaseName,
          work_items: [],
        };
      }
      phasesMap[phaseName].work_items.push(item);
    });
    phases = Object.values(phasesMap);
    totalWorkItems = props.implementationPlan.work_items.length;
  }

  if (phases.length === 0) return null;

  const totalPhases = phases.length;

  // If we still don't have work items count, calculate from phases
  if (!totalWorkItems) {
    totalWorkItems = phases.reduce(
      (sum: number, phase: any) => sum + (phase.work_items?.length || 0),
      0
    );
  }

  // Calculate estimated duration
  let totalHours = 0;
  if (props.implementationPlan.work_items) {
    // Calculate directly from work_items
    props.implementationPlan.work_items.forEach((item: any) => {
      if (item.estimated_time) {
        const timeMatch = item.estimated_time.match(/(\d+)\s*(hour|day)/i);
        if (timeMatch) {
          const value = parseInt(timeMatch[1]);
          const unit = timeMatch[2].toLowerCase();
          totalHours += unit === "hour" ? value : value * 8;
        }
      } else {
        totalHours += 16; // default 2 days
      }
    });
  } else {
    // Calculate from phases
    phases.forEach((phase: any) => {
      if (phase.work_items) {
        totalHours += phase.work_items.reduce(
          (sum: number, item: any) => sum + (item.estimated_hours || 16),
          0
        );
      } else {
        totalHours += phase.duration ? parseInt(phase.duration.match(/\d+/)?.[0] || "40") * 8 : 40;
      }
    });
  }

  const estimatedDays = Math.ceil(totalHours / 8);
  const estimatedWeeks = Math.ceil(estimatedDays / 5);

  return {
    totalPhases,
    totalWorkItems,
    estimatedDuration: `${estimatedWeeks} weeks (${estimatedDays} days)`,
  };
});

const toggleViewType = () => {
  const types: Array<"gantt" | "graph" | "details"> = ["gantt", "graph", "details"];
  const currentIndex = types.indexOf(viewType.value);
  viewType.value = types[(currentIndex + 1) % types.length];
};

const refreshDiagram = () => {
  if (viewType.value === "gantt" && ganttRef.value) {
    ganttRef.value.refresh();
  } else if (viewType.value === "graph" && graphRef.value) {
    graphRef.value.refresh();
  }
};

// Watch for changes in implementation plan data
watch(
  () => props.implementationPlan,
  () => {
    setTimeout(() => {
      refreshDiagram();
    }, 100);
  },
  { deep: true }
);
</script>

<style scoped>
.implementation-plan-visualization {
  @apply w-full;
}
</style>
