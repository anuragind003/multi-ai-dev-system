<template>
  <div class="system-design-visualization">
    <div class="flex justify-between items-center mb-4">
      <h4 class="text-lg font-semibold text-purple-300">System Architecture</h4>
      <div class="flex space-x-2">
        <button
          @click="toggleView"
          class="px-3 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700 transition"
        >
          {{ showDiagram ? 'Show Details' : 'Show Diagram' }}
        </button>
        <button
          v-if="showDiagram"
          @click="refreshDiagram"
          class="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition"
        >
          Refresh
        </button>
      </div>
    </div>

    <div v-if="showDiagram">
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
        <div class="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-gray-400">
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
        </div>
      </div>
    </div>

    <!-- Fallback to traditional display -->
    <div v-else class="space-y-4">
      <!-- Architecture Overview -->
      <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Architecture Overview</h5>
        <p class="text-sm text-gray-400">{{ systemDesign?.architecture_overview || 'N/A' }}</p>
      </div>

      <!-- Components -->
      <div class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Components</h5>
        <div v-if="systemDesign?.components?.length" class="space-y-2">
          <div
            v-for="component in systemDesign.components"
            :key="component.name"
            class="p-2 bg-slate-700 rounded text-xs"
          >
            <div class="font-medium text-gray-200">{{ component.name }}</div>
            <div class="text-gray-400 mt-1">{{ component.description }}</div>
            <div v-if="component.technologies" class="mt-1">
              <span class="text-blue-300">Tech:</span>
              <span class="text-gray-300 ml-1">{{ component.technologies.join(', ') }}</span>
            </div>
          </div>
        </div>
        <div v-else class="text-gray-500 text-sm">No components defined</div>
      </div>

      <!-- Data Flow -->
      <div v-if="systemDesign?.data_flow" class="bg-slate-800 p-4 rounded-lg border border-slate-600/50">
        <h5 class="text-sm font-semibold text-gray-300 mb-2">Data Flow</h5>
        <div class="space-y-1 text-xs text-gray-400">
          <div v-for="(flow, index) in systemDesign.data_flow" :key="index">
            {{ flow }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import MermaidDiagram from './MermaidDiagram.vue'

interface SystemDesignComponent {
  name: string
  description: string
  type: string
  technologies?: string[]
  connections?: string[]
}

interface SystemDesignData {
  architecture_overview: string
  components: SystemDesignComponent[]
  data_flow?: string[]
  relationships?: Array<{
    from: string
    to: string
    type: string
    description?: string
  }>
}

interface Props {
  systemDesign: SystemDesignData | null
}

const props = defineProps<Props>()

const mermaidRef = ref()
const showDiagram = ref(true)

const mermaidConfig = {
  theme: 'default',
  themeVariables: {
    primaryColor: '#3b82f6',
    primaryTextColor: '#1f2937',
    primaryBorderColor: '#2563eb',
    lineColor: '#6b7280',
    secondaryColor: '#10b981',
    tertiaryColor: '#f59e0b'
  }
}

const diagramCode = computed(() => {
  if (!props.systemDesign?.components?.length) {
    return `
graph TD
    A[No System Design Data] --> B[Please complete system design first]
    style A fill:#ef4444,stroke:#dc2626,color:#fff
    style B fill:#6b7280,stroke:#4b5563,color:#fff
`
  }

  const components = props.systemDesign.components
  let diagram = 'graph TD\n'
  
  // Group components by type for better visualization
  const frontend = components.filter(c => c.type?.toLowerCase().includes('frontend') || c.type?.toLowerCase().includes('ui'))
  const backend = components.filter(c => c.type?.toLowerCase().includes('backend') || c.type?.toLowerCase().includes('service') || c.type?.toLowerCase().includes('api'))
  const database = components.filter(c => c.type?.toLowerCase().includes('database') || c.type?.toLowerCase().includes('storage'))
  const others = components.filter(c => !frontend.includes(c) && !backend.includes(c) && !database.includes(c))

  // Create nodes for each component
  components.forEach((component, index) => {
    const nodeId = `C${index}`
    const safeName = component.name.replace(/[^a-zA-Z0-9]/g, '_')
    diagram += `    ${nodeId}["${component.name}<br/><small>${component.type || 'Component'}</small>"]\n`
  })

  // Add relationships based on connections or create logical flow
  if (props.systemDesign.relationships?.length) {
    props.systemDesign.relationships.forEach(rel => {
      const fromIndex = components.findIndex(c => c.name === rel.from)
      const toIndex = components.findIndex(c => c.name === rel.to)
      if (fromIndex >= 0 && toIndex >= 0) {
        const arrow = rel.type === 'bidirectional' ? '---' : '-->'
        diagram += `    C${fromIndex} ${arrow} C${toIndex}\n`
      }
    })
  } else {
    // Create logical connections: Frontend -> Backend -> Database
    frontend.forEach((fe, feIndex) => {
      backend.forEach((be, beIndex) => {
        const feIdx = components.indexOf(fe)
        const beIdx = components.indexOf(be)
        diagram += `    C${feIdx} --> C${beIdx}\n`
      })
    })
    
    backend.forEach((be, beIndex) => {
      database.forEach((db, dbIndex) => {
        const beIdx = components.indexOf(be)
        const dbIdx = components.indexOf(db)
        diagram += `    C${beIdx} --> C${dbIdx}\n`
      })
    })
  }

  // Add styling based on component types
  components.forEach((component, index) => {
    const nodeId = `C${index}`
    if (component.type?.toLowerCase().includes('frontend') || component.type?.toLowerCase().includes('ui')) {
      diagram += `    style ${nodeId} fill:#3b82f6,stroke:#2563eb,color:#fff\n`
    } else if (component.type?.toLowerCase().includes('backend') || component.type?.toLowerCase().includes('service')) {
      diagram += `    style ${nodeId} fill:#10b981,stroke:#059669,color:#fff\n`
    } else if (component.type?.toLowerCase().includes('database') || component.type?.toLowerCase().includes('storage')) {
      diagram += `    style ${nodeId} fill:#f59e0b,stroke:#d97706,color:#fff\n`
    } else {
      diagram += `    style ${nodeId} fill:#6b7280,stroke:#4b5563,color:#fff\n`
    }
  })

  return diagram
})

const toggleView = () => {
  showDiagram.value = !showDiagram.value
}

const refreshDiagram = () => {
  if (mermaidRef.value) {
    mermaidRef.value.refresh()
  }
}

// Watch for changes in system design data
watch(() => props.systemDesign, () => {
  if (showDiagram.value && mermaidRef.value) {
    // Small delay to ensure the diagram updates after data changes
    setTimeout(() => {
      refreshDiagram()
    }, 100)
  }
}, { deep: true })
</script>

<style scoped>
.system-design-visualization {
  @apply w-full;
}
</style> 