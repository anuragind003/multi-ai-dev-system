<template>
  <div class="mermaid-container">
    <div v-if="loading" class="text-center text-gray-400 py-8">
      Generating diagram...
    </div>
    <div v-else-if="error" class="text-red-400 bg-red-900/20 p-4 rounded-lg">
      Error rendering diagram: {{ error }}
    </div>
    <div 
      v-else 
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
    securityLevel: 'loose',
    fontFamily: 'ui-sans-serif, system-ui, sans-serif',
    ...props.config
  }
  
  mermaid.initialize(defaultConfig)
}

// Render the diagram
const renderDiagram = async () => {
  if (!props.diagram || !mermaidRef.value) return
  
  try {
    loading.value = true
    error.value = null
    
    // Clear previous content
    mermaidRef.value.innerHTML = ''
    
    // Validate diagram syntax
    if (!props.diagram.trim()) {
      throw new Error('Empty diagram provided')
    }
    
    // Generate unique ID for this render
    const currentId = `${diagramId.value}-${Date.now()}`
    
    // Render the diagram
    const { svg } = await mermaid.render(currentId, props.diagram)
    
    // Insert the SVG
    mermaidRef.value.innerHTML = svg
    
    // Apply responsive styling to SVG
    const svgElement = mermaidRef.value.querySelector('svg')
    if (svgElement) {
      svgElement.style.maxWidth = '100%'
      svgElement.style.height = 'auto'
    }
    
  } catch (err) {
    console.error('Mermaid rendering error:', err)
    error.value = err instanceof Error ? err.message : 'Unknown rendering error'
  } finally {
    loading.value = false
  }
}

// Watch for changes in diagram content
watch(() => props.diagram, async () => {
  if (props.diagram) {
    await nextTick()
    await renderDiagram()
  }
}, { immediate: false })

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
  @apply w-full;
}

.mermaid-diagram {
  @apply border border-gray-300;
}

.mermaid-diagram :deep(svg) {
  @apply w-full h-auto;
}

/* Dark theme support */
.dark .mermaid-diagram {
  @apply bg-gray-800 border-gray-600;
}

/* Override Mermaid's default styles for better integration */
.mermaid-diagram :deep(.node rect),
.mermaid-diagram :deep(.node circle),
.mermaid-diagram :deep(.node ellipse),
.mermaid-diagram :deep(.node polygon) {
  @apply stroke-2;
}

.mermaid-diagram :deep(.edgePath .path) {
  @apply stroke-2;
}

.mermaid-diagram :deep(.edgeLabel) {
  @apply bg-white px-2 py-1 rounded text-sm;
}
</style> 