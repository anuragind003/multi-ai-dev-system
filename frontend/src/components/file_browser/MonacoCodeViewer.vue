<template>
  <div class="monaco-code-viewer bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
    <div class="flex justify-between items-center p-3 bg-slate-800 border-b border-slate-600">
      <div class="flex items-center space-x-3">
        <span class="text-sm font-medium text-gray-200">
          {{ fileName || 'Select a file' }}
        </span>
        <span v-if="fileExtension" class="px-2 py-1 text-xs bg-blue-600 text-white rounded">
          {{ fileExtension.toUpperCase() }}
        </span>
      </div>
      <div class="flex items-center space-x-2">
        <button
          v-if="fileContent && !loading"
          @click="toggleMinimap"
          class="px-2 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition"
        >
          {{ showMinimap ? 'Hide' : 'Show' }} Minimap
        </button>
        <button
          v-if="fileContent && !loading"
          @click="toggleWordWrap"
          class="px-2 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition"
        >
          {{ wordWrap ? 'No Wrap' : 'Word Wrap' }}
        </button>
        <button
          v-if="fileContent && !loading"
          @click="copyToClipboard"
          class="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition"
        >
          Copy
        </button>
      </div>
    </div>

    <div class="relative">
      <div v-if="loading" class="flex items-center justify-center h-64 text-gray-400">
        <div class="text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <span>Loading code...</span>
        </div>
      </div>
      
      <div v-else-if="error" class="p-4 text-red-400 bg-red-900/20">
        <div class="flex items-center space-x-2">
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <span>{{ error }}</span>
        </div>
      </div>
      
      <div v-else-if="!fileContent" class="flex items-center justify-center h-64 text-gray-400">
        <div class="text-center">
          <svg class="w-12 h-12 mx-auto mb-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p class="text-sm">Select a file from the tree to view its content</p>
        </div>
      </div>
      
      <div 
        v-else 
        ref="editorContainer" 
        class="w-full"
        :style="{ height: editorHeight }"
      ></div>
    </div>

    <!-- File Info Footer -->
    <div v-if="fileContent && !loading" class="px-3 py-2 bg-slate-800 border-t border-slate-600 text-xs text-gray-400 flex justify-between">
      <div class="flex space-x-4">
        <span>{{ lineCount }} lines</span>
        <span>{{ fileSize }} characters</span>
        <span v-if="lastModified">Modified: {{ formatDate(lastModified) }}</span>
      </div>
      <div v-if="cursorPosition" class="flex space-x-2">
        <span>Line {{ cursorPosition.line }}</span>
        <span>Col {{ cursorPosition.column }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, computed, nextTick } from 'vue'
import * as monaco from 'monaco-editor'

interface Props {
  sessionId: string
  filePath: string | null
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '600px'
})

const emit = defineEmits<{
  (e: 'file-changed', filePath: string | null): void
}>()

// Template refs
const editorContainer = ref<HTMLElement>()

// State
const fileContent = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const editor = ref<monaco.editor.IStandaloneCodeEditor | null>(null)
const showMinimap = ref(true)
const wordWrap = ref(false)
const cursorPosition = ref<{ line: number; column: number } | null>(null)
const lastModified = ref<string | null>(null)

// Computed properties
const fileName = computed(() => {
  if (!props.filePath) return null
  return props.filePath.split('/').pop() || null
})

const fileExtension = computed(() => {
  if (!fileName.value) return null
  const parts = fileName.value.split('.')
  return parts.length > 1 ? parts.pop() : null
})

const editorHeight = computed(() => props.height)

const lineCount = computed(() => {
  return fileContent.value ? fileContent.value.split('\n').length : 0
})

const fileSize = computed(() => {
  return fileContent.value ? fileContent.value.length : 0
})

// Language mapping for Monaco Editor
const getLanguageFromExtension = (extension: string | null | undefined): string => {
  if (!extension) return 'plaintext'
  
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'ts': 'typescript',
    'jsx': 'javascript',
    'tsx': 'typescript',
    'vue': 'html', // Vue SFC treated as HTML for better highlighting
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'sass': 'scss',
    'json': 'json',
    'md': 'markdown',
    'py': 'python',
    'java': 'java',
    'c': 'c',
    'cpp': 'cpp',
    'cs': 'csharp',
    'php': 'php',
    'rb': 'ruby',
    'go': 'go',
    'rs': 'rust',
    'yaml': 'yaml',
    'yml': 'yaml',
    'xml': 'xml',
    'sql': 'sql',
    'sh': 'shell',
    'bash': 'shell',
    'ps1': 'powershell',
    'dockerfile': 'dockerfile'
  }
  
  return languageMap[extension.toLowerCase()] || 'plaintext'
}

// Monaco Editor setup
const createEditor = async () => {
  if (!editorContainer.value || !fileContent.value) return
  
  try {
    const language = getLanguageFromExtension(fileExtension.value)
    
    editor.value = monaco.editor.create(editorContainer.value, {
      value: fileContent.value,
      language: language,
      theme: 'vs-dark',
      readOnly: true,
      automaticLayout: true,
      minimap: { enabled: showMinimap.value },
      wordWrap: wordWrap.value ? 'on' : 'off',
      lineNumbers: 'on',
      glyphMargin: false,
      folding: true,
      lineDecorationsWidth: 0,
      lineNumbersMinChars: 3,
      renderWhitespace: 'selection',
      scrollBeyondLastLine: false,
      contextmenu: true,
      selectOnLineNumbers: true,
      roundedSelection: false,
      scrollbar: {
        vertical: 'visible',
        horizontal: 'visible',
        useShadows: false,
        verticalHasArrows: false,
        horizontalHasArrows: false,
        verticalScrollbarSize: 10,
        horizontalScrollbarSize: 10
      }
    })

    // Track cursor position
    editor.value.onDidChangeCursorPosition((e) => {
      cursorPosition.value = {
        line: e.position.lineNumber,
        column: e.position.column
      }
    })

    // Focus editor for better UX
    editor.value.focus()
    
  } catch (err) {
    console.error('Failed to create Monaco editor:', err)
    error.value = 'Failed to initialize code editor'
  }
}

const destroyEditor = () => {
  if (editor.value) {
    editor.value.dispose()
    editor.value = null
  }
}

const updateEditorContent = () => {
  if (editor.value && fileContent.value !== null) {
    const language = getLanguageFromExtension(fileExtension.value)
    monaco.editor.setModelLanguage(editor.value.getModel()!, language)
    editor.value.setValue(fileContent.value)
  }
}

// File operations
const fetchFileContent = async (sessionId: string, filePath: string) => {
  loading.value = true
  error.value = null
  fileContent.value = null
  
  try {
    const response = await fetch(`/api/session-file-content/${sessionId}/${encodeURIComponent(filePath)}`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    fileContent.value = data.content
    lastModified.value = data.lastModified || null
    
    // Create or update editor after content is loaded
    await nextTick()
    if (editor.value) {
      updateEditorContent()
    } else {
      await createEditor()
    }
    
  } catch (err: any) {
    error.value = err.message
    console.error('Error fetching file content:', err)
  } finally {
    loading.value = false
  }
}

// UI Actions
const toggleMinimap = () => {
  showMinimap.value = !showMinimap.value
  if (editor.value) {
    editor.value.updateOptions({ minimap: { enabled: showMinimap.value } })
  }
}

const toggleWordWrap = () => {
  wordWrap.value = !wordWrap.value
  if (editor.value) {
    editor.value.updateOptions({ wordWrap: wordWrap.value ? 'on' : 'off' })
  }
}

const copyToClipboard = async () => {
  if (fileContent.value) {
    try {
      await navigator.clipboard.writeText(fileContent.value)
      // You could add a toast notification here
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString()
}

// Watchers
watch(() => props.filePath, (newFilePath) => {
  if (props.sessionId && newFilePath) {
    fetchFileContent(props.sessionId, newFilePath)
    emit('file-changed', newFilePath)
  } else {
    fileContent.value = null
    destroyEditor()
    emit('file-changed', null)
  }
}, { immediate: true })

watch(() => props.sessionId, () => {
  if (props.sessionId && props.filePath) {
    fetchFileContent(props.sessionId, props.filePath)
  }
})

// Lifecycle
onMounted(() => {
  // Monaco Editor is already bundled, no need for additional setup
})

onBeforeUnmount(() => {
  destroyEditor()
})
</script>

<style scoped>
.monaco-code-viewer {
  @apply w-full;
}

/* Ensure Monaco Editor container takes full space */
.monaco-code-viewer :deep(.monaco-editor) {
  @apply w-full h-full;
}

/* Dark theme integration */
.monaco-code-viewer :deep(.monaco-editor .margin),
.monaco-code-viewer :deep(.monaco-editor .monaco-editor-background) {
  background-color: #0f172a !important;
}
</style> 