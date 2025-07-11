<template>
  <div class="system-design-visualization">
    <div class="flex justify-between items-center mb-4">
      <h4 class="text-lg font-semibold text-purple-300">System Architecture</h4>
      <div class="flex space-x-2">
        <select
          v-model="viewType"
          class="px-3 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700 transition"
        >
          <option value="diagram">Architecture Diagram</option>
          <option value="flow">Data Flow</option>
          <option value="details">Component Details</option>
        </select>
        <button
          v-if="viewType === 'diagram' || viewType === 'flow'"
          @click="refreshDiagram"
          class="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition"
        >
          Refresh
        </button>
      </div>
    </div>

    <!-- Architecture Diagram View -->
    <div v-if="viewType === 'diagram'">
      <MermaidDiagram
        ref="mermaidRef"
        :diagram="diagramCode"
        theme="default"
        height="500px"
        :config="mermaidConfig"
      />

      <!-- Legend -->
      <div class="mt-4 p-3 bg-slate-800 rounded-lg border border-slate-600">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Legend</h5>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-2 text-xs text-gray-400">
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-blue-500 rounded"></div>
            <span>Frontend Components</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-green-500 rounded"></div>
            <span>Backend Services</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-orange-500 rounded"></div>
            <span>Databases</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-purple-500 rounded"></div>
            <span>Infrastructure</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Data Flow View -->
    <div v-else-if="viewType === 'flow'">
      <MermaidDiagram
        ref="flowRef"
        :diagram="dataFlowCode"
        theme="default"
        height="400px"
        :config="mermaidConfig"
      />

      <!-- Data Flow Summary -->
      <div class="mt-4 p-3 bg-slate-800 rounded-lg border border-slate-600">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Data Flow Summary</h5>
        <div class="text-xs text-gray-400 space-y-1">
          <div v-if="systemDesign?.data_flow">{{ systemDesign.data_flow }}</div>
          <div v-else>Data flows through the system components in a structured manner.</div>
        </div>
      </div>
    </div>

    <!-- Fallback to traditional display -->
    <div v-else class="space-y-4">
      <!-- Architecture Overview -->
      <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Architecture Overview</h5>
        <p class="text-sm text-gray-400">
          {{ systemDesign?.architecture_overview || systemDesign?.architecture?.pattern || "N/A" }}
        </p>
        <div v-if="systemDesign?.architecture?.justification" class="mt-2">
          <p class="text-xs text-gray-500">{{ systemDesign.architecture.justification }}</p>
        </div>
      </div>

      <!-- Components -->
      <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Components</h5>
        <div v-if="systemDesign?.components?.length" class="space-y-3">
          <div
            v-for="component in systemDesign.components"
            :key="component.name"
            class="p-3 bg-slate-700 rounded border-l-4"
            :class="{
              'border-blue-500': component.type?.toLowerCase().includes('frontend'),
              'border-green-500': component.type?.toLowerCase().includes('backend'),
              'border-orange-500': component.type?.toLowerCase().includes('database'),
              'border-purple-500': component.type?.toLowerCase().includes('infrastructure'),
              'border-gray-500': true,
            }"
          >
            <div class="flex justify-between items-start mb-2">
              <div class="font-medium text-gray-200">{{ component.name }}</div>
              <div class="text-xs text-gray-500 capitalize">{{ component.type }}</div>
            </div>
            <div class="text-gray-400 text-sm mb-2">{{ component.description }}</div>
            <div v-if="component.technologies?.length" class="mb-2">
              <span class="text-blue-300 text-xs">Technologies:</span>
              <div class="flex flex-wrap gap-1 mt-1">
                <span
                  v-for="tech in component.technologies"
                  :key="tech"
                  class="px-2 py-1 bg-blue-900/30 text-blue-200 text-xs rounded"
                >
                  {{ tech }}
                </span>
              </div>
            </div>
            <div v-if="component.responsibilities?.length" class="mb-2">
              <span class="text-green-300 text-xs">Responsibilities:</span>
              <ul class="list-disc list-inside text-xs text-gray-400 mt-1 space-y-1">
                <li v-for="resp in component.responsibilities" :key="resp">{{ resp }}</li>
              </ul>
            </div>
          </div>
        </div>
        <div v-else class="text-gray-500 text-sm">No components defined</div>
      </div>

      <!-- Security -->
      <div
        v-if="systemDesign?.security"
        class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
      >
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Security</h5>
        <div class="space-y-2 text-sm">
          <div v-if="systemDesign.security.authentication_method">
            <span class="text-red-300">Authentication:</span>
            <span class="text-gray-400 ml-2">{{
              systemDesign.security.authentication_method
            }}</span>
          </div>
          <div v-if="systemDesign.security.authorization_strategy">
            <span class="text-red-300">Authorization:</span>
            <span class="text-gray-400 ml-2">{{
              systemDesign.security.authorization_strategy
            }}</span>
          </div>
        </div>
      </div>

      <!-- API Endpoints -->
      <div
        v-if="systemDesign?.api_endpoints?.endpoints?.length"
        class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
      >
        <h5 class="text-sm font-semibold text-gray-300 mb-2">API Endpoints</h5>
        <div class="space-y-2">
          <div
            v-for="endpoint in systemDesign.api_endpoints.endpoints.slice(0, 5)"
            :key="endpoint.path"
            class="p-2 bg-slate-700 rounded text-xs flex justify-between items-center"
          >
            <div>
              <span class="font-mono text-yellow-300">{{ endpoint.method }}</span>
              <span class="text-gray-300 ml-2">{{ endpoint.path }}</span>
            </div>
            <div class="text-gray-500">{{ endpoint.purpose || endpoint.description }}</div>
          </div>
          <div v-if="systemDesign.api_endpoints.endpoints.length > 5" class="text-xs text-gray-500">
            ... and {{ systemDesign.api_endpoints.endpoints.length - 5 }} more endpoints
          </div>
        </div>
      </div>

      <!-- Data Flow -->
      <div
        v-if="systemDesign?.data_flow"
        class="bg-slate-800 p-4 rounded-lg border border-slate-600/50"
      >
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Data Flow</h5>
        <div class="text-sm text-gray-400">
          <div v-if="typeof systemDesign.data_flow === 'string'">
            {{ systemDesign.data_flow }}
          </div>
          <div v-else-if="Array.isArray(systemDesign.data_flow)" class="space-y-1">
            <div v-for="(flow, index) in systemDesign.data_flow" :key="index">
              {{ flow }}
            </div>
          </div>
          <div v-else>
            {{ JSON.stringify(systemDesign.data_flow) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import MermaidDiagram from "./MermaidDiagram.vue";

interface SystemDesignComponent {
  name: string;
  description: string;
  type: string;
  technologies?: string[];
  connections?: string[];
  responsibilities?: string[];
}

interface SystemDesignData {
  architecture_overview?: string;
  components: SystemDesignComponent[];
  data_flow?: string | string[];
  relationships?: Array<{
    from: string;
    to: string;
    type: string;
    description?: string;
  }>;
  architecture?: {
    pattern?: string;
    justification?: string;
  };
  security?: {
    authentication_method?: string;
    authorization_strategy?: string;
  };
  api_endpoints?: {
    endpoints: Array<{
      path: string;
      method: string;
      purpose?: string;
      description?: string;
    }>;
  };
}

interface Props {
  systemDesign: SystemDesignData | null;
}

const props = defineProps<Props>();

const mermaidRef = ref();
const flowRef = ref();
const viewType = ref<"diagram" | "flow" | "details">("diagram");

const mermaidConfig = {
  theme: "default",
  themeVariables: {
    primaryColor: "#3b82f6",
    primaryTextColor: "#1f2937",
    primaryBorderColor: "#2563eb",
    lineColor: "#6b7280",
    secondaryColor: "#10b981",
    tertiaryColor: "#f59e0b",
  },
};

const diagramCode = computed(() => {
  console.log("SystemDesignVisualization: Computing diagram code", {
    hasSystemDesign: !!props.systemDesign,
    componentCount: props.systemDesign?.components?.length || 0,
  });

  if (!props.systemDesign?.components?.length) {
    console.log("SystemDesignVisualization: No components data, returning fallback diagram");
    return `
graph TD
    A["🚧 No System Design Data"] --> B["Please complete system design first"]
    style A fill:#ef4444,stroke:#dc2626,color:#fff
    style B fill:#6b7280,stroke:#4b5563,color:#fff
`;
  }

  const getComponentType = (component: SystemDesignComponent): string => {
    const type = (component.type || "").toLowerCase();
    const name = component.name.toLowerCase();

    if (
      type.includes("frontend") ||
      type.includes("ui") ||
      name.includes("frontend") ||
      name.includes("ui")
    )
      return "frontend";
    if (
      type.includes("backend") ||
      type.includes("service") ||
      type.includes("api") ||
      name.includes("backend") ||
      name.includes("api")
    )
      return "backend";
    if (
      type.includes("database") ||
      type.includes("storage") ||
      name.includes("db") ||
      name.includes("database")
    )
      return "database";
    if (
      type.includes("deployment") ||
      type.includes("infrastructure") ||
      name.includes("deployment") ||
      name.includes("infra")
    )
      return "infrastructure";

    return "other";
  };

  const componentsWithMeta = props.systemDesign.components.map((c, i) => ({
    ...c,
    id: `C${i}`,
    inferredType: getComponentType(c),
  }));

  const groupedComponents: { [key: string]: any[] } = {
    frontend: [],
    backend: [],
    database: [],
    infrastructure: [],
    other: [],
  };

  componentsWithMeta.forEach((comp) => {
    if (groupedComponents[comp.inferredType]) {
      groupedComponents[comp.inferredType].push(comp);
    } else {
      groupedComponents.other.push(comp);
    }
  });

  let diagram = "graph TD\n";

  // Create subgraphs and nodes
  Object.entries(groupedComponents).forEach(([groupName, groupComps]) => {
    if (groupComps.length > 0) {
      const title = groupName.charAt(0).toUpperCase() + groupName.slice(1);
      let groupIcon = "🧩";
      switch (groupName) {
        case "frontend":
          groupIcon = "🌐";
          break;
        case "backend":
          groupIcon = "⚙️";
          break;
        case "database":
          groupIcon = "🗄️";
          break;
        case "infrastructure":
          groupIcon = "☁️";
          break;
      }
      diagram += `    subgraph "${groupIcon} ${title}"\n`;
      groupComps.forEach((comp) => {
        const tech = comp.technologies?.join(", ") || comp.type || "Component";
        diagram += `        ${comp.id}["<b>${comp.name}</b><br/><small>${tech}</small>"]\n`;
      });
      diagram += `    end\n`;
    }
  });

  // Add relationships
  if (props.systemDesign.relationships?.length) {
    props.systemDesign.relationships.forEach((rel) => {
      const fromComp = componentsWithMeta.find((c) => c.name === rel.from);
      const toComp = componentsWithMeta.find((c) => c.name === rel.to);

      if (fromComp && toComp) {
        const arrow = rel.type === "bidirectional" ? "<-->" : "-->";
        const label = rel.description ? `|"${rel.description}"|` : "";
        diagram += `    ${fromComp.id} ${arrow}${label} ${toComp.id}\n`;
      }
    });
  } else {
    // Create logical connections
    groupedComponents.frontend.forEach((fe) => {
      groupedComponents.backend.forEach((be) => {
        diagram += `    ${fe.id} -->|"HTTP/S API"| ${be.id}\n`;
      });
    });

    groupedComponents.backend.forEach((be) => {
      groupedComponents.database.forEach((db) => {
        diagram += `    ${be.id} -->|"DB Query"| ${db.id}\n`;
      });
    });

    if (groupedComponents.infrastructure.length > 0) {
      const allComps = [
        ...groupedComponents.frontend,
        ...groupedComponents.backend,
        ...groupedComponents.database,
        ...groupedComponents.other,
      ];
      groupedComponents.infrastructure.forEach((infra) => {
        allComps.forEach((comp) => {
          diagram += `    ${infra.id} -.->|Deploys & Manages| ${comp.id}\n`;
        });
      });
    }
  }

  // Add styling
  componentsWithMeta.forEach((comp) => {
    let style = "";
    switch (comp.inferredType) {
      case "frontend":
        style = "fill:#3b82f6,stroke:#2563eb,color:#fff";
        break;
      case "backend":
        style = "fill:#10b981,stroke:#059669,color:#fff";
        break;
      case "database":
        style = "fill:#f59e0b,stroke:#d97706,color:#fff";
        break;
      case "infrastructure":
        style = "fill:#8b5cf6,stroke:#7c3aed,color:#fff";
        break;
      default:
        style = "fill:#6b7280,stroke:#4b5563,color:#fff";
        break;
    }
    diagram += `    style ${comp.id} ${style}\n`;
  });

  console.log("SystemDesignVisualization: Generated diagram code:", diagram);
  return diagram;
});

const dataFlowCode = computed(() => {
  if (!props.systemDesign?.components?.length) {
    return `
flowchart TD
    A["No Data Flow Available"] --> B["Complete system design first"]
    style A fill:#ef4444,stroke:#dc2626,color:#fff
    style B fill:#6b7280,stroke:#4b5563,color:#fff
`;
  }

  let flowChart = "flowchart TD\n";

  // Create a simplified data flow
  const components = props.systemDesign.components;
  const frontend = components.filter(
    (c) => c.type?.toLowerCase().includes("frontend") || c.name.toLowerCase().includes("frontend")
  );
  const backend = components.filter(
    (c) => c.type?.toLowerCase().includes("backend") || c.name.toLowerCase().includes("backend")
  );
  const database = components.filter(
    (c) => c.type?.toLowerCase().includes("database") || c.name.toLowerCase().includes("database")
  );

  // User interaction flow
  flowChart += `    User[👤 User] --> UI[🖥️ ${frontend[0]?.name || "Frontend"}]\n`;
  flowChart += `    UI --> API[🔗 ${backend[0]?.name || "Backend API"}]\n`;
  flowChart += `    API --> DB[🗄️ ${database[0]?.name || "Database"}]\n`;
  flowChart += `    DB --> API\n`;
  flowChart += `    API --> UI\n`;
  flowChart += `    UI --> User\n`;

  // Add styling
  flowChart += `    style User fill:#3b82f6,stroke:#2563eb,color:#fff\n`;
  flowChart += `    style UI fill:#10b981,stroke:#059669,color:#fff\n`;
  flowChart += `    style API fill:#f59e0b,stroke:#d97706,color:#fff\n`;
  flowChart += `    style DB fill:#8b5cf6,stroke:#7c3aed,color:#fff\n`;

  return flowChart;
});

const refreshDiagram = () => {
  if (viewType.value === "diagram" && mermaidRef.value) {
    mermaidRef.value.refresh();
  } else if (viewType.value === "flow" && flowRef.value) {
    flowRef.value.refresh();
  }
};

// Watch for changes in system design data
watch(
  () => props.systemDesign,
  () => {
    if (
      (viewType.value === "diagram" || viewType.value === "flow") &&
      (mermaidRef.value || flowRef.value)
    ) {
      // Small delay to ensure the diagram updates after data changes
      setTimeout(() => {
        refreshDiagram();
      }, 100);
    }
  },
  { deep: true }
);
</script>

<style scoped>
.system-design-visualization {
  width: 100%;
}
</style>
