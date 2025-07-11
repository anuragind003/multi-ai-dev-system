<template>
  <div class="mermaid-container">
    <div v-if="loading" class="text-center text-gray-400 py-8">
      Generating diagram...
    </div>
    <div v-else-if="error" class="text-red-400 bg-red-900/20 p-4 rounded-lg">
      Error rendering diagram: {{ error }}
    </div>
    <div 
      v-show="!loading && !error"
      ref="mermaidRef" 
      class="mermaid-diagram bg-white p-4 rounded-lg overflow-auto"
      :style="{ minHeight: height }"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import mermaid from 'mermaid'

interface Props {
  diagram: string
  theme?: 'default' | 'dark' | 'forest' | 'neutral'
  height?: string
  config?: object
}

const props = withDefaults(defineProps<Props>(), {
  theme: 'default',
  height: '400px',
  config: () => ({})
})

const mermaidRef = ref<HTMLElement>()
const loading = ref(true)
const error = ref<string | null>(null)
const diagramId = ref(`mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`)

// Initialize Mermaid
const initializeMermaid = () => {
  const defaultConfig = {
    startOnLoad: false,
    theme: props.theme,
    securityLevel: 'loose' as const,
    fontFamily: 'ui-sans-serif, system-ui, sans-serif',
    ...props.config
  }
  
  mermaid.initialize(defaultConfig)
}

// Render the diagram
const renderDiagram = async () => {
  if (!props.diagram || !mermaidRef.value) {
    console.log('MermaidDiagram: Cannot render - missing diagram or ref', { 
      diagram: !!props.diagram, 
      ref: !!mermaidRef.value 
    })
    return
  }
  
  try {
    loading.value = true
    error.value = null
    
    console.log('MermaidDiagram: Starting render process', { 
      diagramLength: props.diagram.length,
      diagramPreview: props.diagram.substring(0, 100) + '...'
    })
    
    // Clear previous content
    mermaidRef.value.innerHTML = ''
    
    // Validate diagram syntax
    if (!props.diagram.trim()) {
      throw new Error('Empty diagram provided')
    }
    
    // Generate unique ID for this render
    const currentId = `${diagramId.value}-${Date.now()}`
    
    console.log('MermaidDiagram: Calling mermaid.render with ID:', currentId)
    
    // Render the diagram
    const { svg } = await mermaid.render(currentId, props.diagram)
    
    console.log('MermaidDiagram: Render successful, inserting SVG')
    
    // Insert the SVG
    mermaidRef.value.innerHTML = svg
    
    // Apply responsive styling to SVG
    const svgElement = mermaidRef.value.querySelector('svg')
    if (svgElement) {
      svgElement.style.maxWidth = '100%'
      svgElement.style.height = 'auto'
    }
    
    console.log('MermaidDiagram: Diagram rendered successfully')
    
  } catch (err) {
    console.error('Mermaid rendering error:', err)
    console.error('Diagram content that failed:', props.diagram)
    error.value = err instanceof Error ? err.message : 'Unknown rendering error'
  } finally {
    loading.value = false
  }
}

// Watch for changes in diagram content
watch(() => props.diagram, async () => {
  console.log('MermaidDiagram: Diagram prop changed', { 
    newDiagram: !!props.diagram,
    diagramLength: props.diagram?.length || 0
  })
  if (props.diagram) {
    await nextTick()
    await renderDiagram()
  }
}, { immediate: true })

// Watch for theme changes
watch(() => props.theme, () => {
  initializeMermaid()
  renderDiagram()
})

onMounted(async () => {
  initializeMermaid()
  await nextTick()
  if (props.diagram) {
    await renderDiagram()
  } else {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  // Cleanup if needed
  if (mermaidRef.value) {
    mermaidRef.value.innerHTML = ''
  }
})

// Expose methods for parent components
defineExpose({
  refresh: renderDiagram,
  isLoading: () => loading.value,
  hasError: () => !!error.value
})
</script>

<style scoped>
.mermaid-container {
  width: 100%;
}

.mermaid-diagram {
  border: 1px solid #d1d5db;
}

.mermaid-diagram :deep(svg) {
  width: 100%;
  height: auto;
}

/* Dark theme support */
.dark .mermaid-diagram {
  background-color: #1f2937;
  border-color: #4b5563;
}

/* Override Mermaid's default styles for better integration */
.mermaid-diagram :deep(.node rect),
.mermaid-diagram :deep(.node circle),
.mermaid-diagram :deep(.node ellipse),
.mermaid-diagram :deep(.node polygon) {
  stroke-width: 2px;
}

.mermaid-diagram :deep(.edgePath .path) {
  stroke-width: 2px;
}

.mermaid-diagram :deep(.edgeLabel) {
  background-color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}
</style> 