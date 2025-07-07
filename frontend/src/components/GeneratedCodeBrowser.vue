<template>
  <div class="generated-code-browser bg-slate-900/70 border border-slate-700 rounded-lg overflow-hidden">
    <div class="flex justify-between items-center p-4 bg-slate-800 border-b border-slate-600">
      <h3 class="text-lg font-semibold text-gray-200">Generated Code</h3>
      <div class="flex items-center space-x-2">
        <button
          @click="refreshFiles"
          :disabled="refreshing"
          class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50"
        >
          {{ refreshing ? 'Refreshing...' : 'Refresh' }}
        </button>
        <button
          @click="toggleLayout"
          class="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition"
        >
          {{ layoutMode === 'horizontal' ? 'Vertical' : 'Horizontal' }}
        </button>
      </div>
    </div>

    <div v-if="!sessionId" class="flex items-center justify-center h-64 text-gray-400">
      <div class="text-center">
        <svg class="w-12 h-12 mx-auto mb-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C20.832 18.477 19.246 18 17.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
        <p class="text-sm">No session selected</p>
        <p class="text-xs text-gray-500 mt-1">Run a workflow to generate code files</p>
      </div>
    </div>

    <div v-else class="flex" :class="layoutClasses">
      <!-- File Tree Panel -->
      <div class="file-tree-panel" :class="filePanelClasses">
        <div class="h-full overflow-hidden flex flex-col">
          <div class="p-3 bg-slate-800 border-b border-slate-600">
            <h4 class="text-sm font-medium text-gray-300">Project Structure</h4>
            <div v-if="filesData?.files?.length" class="text-xs text-gray-500 mt-1">
              {{ totalFiles }} files in {{ totalDirectories }} directories
            </div>
          </div>
          
          <div class="flex-1 overflow-y-auto p-2">
            <div v-if="loading" class="text-center text-gray-400 py-8">
              <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto mb-2"></div>
              <span class="text-sm">Loading files...</span>
            </div>
            
            <div v-else-if="error" class="text-red-400 bg-red-900/20 p-3 rounded-md">
              <div class="text-sm">{{ error }}</div>
              <button
                @click="refreshFiles"
                class="mt-2 text-xs bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700"
              >
                Try Again
              </button>
            </div>
            
            <div v-else-if="!filesData?.files?.length" class="text-center text-gray-400 py-8">
              <svg class="w-8 h-8 mx-auto mb-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <p class="text-sm">No files generated yet</p>
              <p class="text-xs text-gray-500 mt-1">Files will appear here after code generation</p>
            </div>
            
            <ul v-else class="space-y-1">
              <FileTreeItem
                v-for="item in filesData.files"
                :key="item.path"
                :item="item"
                :selected-file="selectedFile"
                @select-file="handleSelectFile"
              />
            </ul>
          </div>
        </div>
      </div>

      <!-- Resizable Handle -->
      <div 
        v-if="layoutMode === 'horizontal'"
        class="resize-handle bg-slate-700 hover:bg-slate-600 cursor-col-resize flex items-center justify-center"
        @mousedown="startResize"
      >
        <div class="w-1 h-8 bg-slate-500 rounded"></div>
      </div>

      <!-- Code Viewer Panel -->
      <div class="code-viewer-panel flex-1 min-w-0">
        <MonacoCodeViewer
          :sessionId="sessionId"
          :filePath="selectedFile"
          :height="codeViewerHeight"
          @file-changed="handleFileChanged"
        />
      </div>
    </div>

    <!-- Status Bar -->
    <div v-if="sessionId" class="px-4 py-2 bg-slate-800 border-t border-slate-600 text-xs text-gray-400 flex justify-between">
      <div class="flex space-x-4">
        <span v-if="filesData">{{ totalFiles }} files</span>
        <span v-if="selectedFile">{{ selectedFile }}</span>
      </div>
      <div class="flex space-x-2">
        <span v-if="lastRefresh">Last updated: {{ formatTime(lastRefresh) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import FileTreeItem from './file_browser/FileTreeItem.vue'
import MonacoCodeViewer from './file_browser/MonacoCodeViewer.vue'

interface FileSystemItem {
  name: string
  type: 'file' | 'directory'
  path: string
  size?: number
  children?: FileSystemItem[]
}

interface FilesData {
  session_id: string
  files: FileSystemItem[]
}

interface Props {
  sessionId: string | null
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '600px'
})

const emit = defineEmits<{
  (e: 'file-selected', filePath: string | null): void
  (e: 'files-loaded', filesData: FilesData): void
}>()

// State
const filesData = ref<FilesData | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const refreshing = ref(false)
const selectedFile = ref<string | null>(null)
const layoutMode = ref<'horizontal' | 'vertical'>('horizontal')
const filePanelWidth = ref(300)
const lastRefresh = ref<Date | null>(null)

// Computed properties
const layoutClasses = computed(() => {
  return layoutMode.value === 'horizontal' 
    ? 'flex-row h-full' 
    : 'flex-col'
})

const filePanelClasses = computed(() => {
  if (layoutMode.value === 'horizontal') {
    return `w-${Math.max(200, filePanelWidth.value)}px flex-shrink-0 border-r border-slate-600`
  } else {
    return 'h-64 border-b border-slate-600'
  }
})

const codeViewerHeight = computed(() => {
  if (layoutMode.value === 'vertical') {
    return `calc(${props.height} - 256px)` // Subtract file panel height
  } else {
    return props.height
  }
})

const totalFiles = computed(() => {
  if (!filesData.value?.files) return 0
  
  const countFiles = (items: FileSystemItem[]): number => {
    return items.reduce((count, item) => {
      if (item.type === 'file') {
        return count + 1
      } else if (item.children) {
        return count + countFiles(item.children)
      }
      return count
    }, 0)
  }
  
  return countFiles(filesData.value.files)
})

const totalDirectories = computed(() => {
  if (!filesData.value?.files) return 0
  
  const countDirs = (items: FileSystemItem[]): number => {
    return items.reduce((count, item) => {
      if (item.type === 'directory') {
        const childDirs = item.children ? countDirs(item.children) : 0
        return count + 1 + childDirs
      }
      return count
    }, 0)
  }
  
  return countDirs(filesData.value.files)
})

// File operations
const fetchFiles = async (sessionId: string) => {
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch(`/api/session-files/${sessionId}`)
    
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('No generated files found for this session')
      } else {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
    }
    
    const data: FilesData = await response.json()
    filesData.value = data
    lastRefresh.value = new Date()
    emit('files-loaded', data)
    
  } catch (err: any) {
    error.value = err.message
    console.error('Error fetching files:', err)
  } finally {
    loading.value = false
  }
}

const refreshFiles = async () => {
  if (!props.sessionId) return
  refreshing.value = true
  await fetchFiles(props.sessionId)
  refreshing.value = false
}

// UI handlers
const handleSelectFile = (filePath: string) => {
  selectedFile.value = filePath
  emit('file-selected', filePath)
}

const handleFileChanged = (filePath: string | null) => {
  // This could be used for additional handling when file changes
}

const toggleLayout = () => {
  layoutMode.value = layoutMode.value === 'horizontal' ? 'vertical' : 'horizontal'
}

// Resize functionality for horizontal layout
const startResize = (e: MouseEvent) => {
  if (layoutMode.value !== 'horizontal') return
  
  const startX = e.clientX
  const startWidth = filePanelWidth.value
  
  const handleMouseMove = (e: MouseEvent) => {
    const deltaX = e.clientX - startX
    const newWidth = Math.max(200, Math.min(600, startWidth + deltaX))
    filePanelWidth.value = newWidth
  }
  
  const handleMouseUp = () => {
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }
  
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

// Utility functions
const formatTime = (date: Date): string => {
  return date.toLocaleTimeString()
}

// Watchers
watch(() => props.sessionId, async (newSessionId) => {
  if (newSessionId) {
    selectedFile.value = null
    await fetchFiles(newSessionId)
  } else {
    filesData.value = null
    selectedFile.value = null
    error.value = null
  }
}, { immediate: true })

// Lifecycle
onMounted(() => {
  if (props.sessionId) {
    fetchFiles(props.sessionId)
  }
})
</script>

<style scoped>
.generated-code-browser {
  @apply w-full;
  height: v-bind(height);
}

.resize-handle {
  width: 4px;
  transition: background-color 0.2s;
}

.resize-handle:hover {
  background-color: rgb(71 85 105);
}

/* File panel dynamic width */
.file-tree-panel {
  width: v-bind('filePanelWidth + "px"');
}

/* Ensure proper scrolling */
.file-tree-panel,
.code-viewer-panel {
  @apply overflow-hidden;
}
</style> 