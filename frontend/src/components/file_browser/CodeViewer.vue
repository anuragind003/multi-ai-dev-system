<template>
  <div class="code-viewer bg-slate-900/70 border border-slate-700 rounded-lg p-4 max-h-[70vh] overflow-y-auto font-mono text-sm">
    <div v-if="loading" class="text-center text-gray-400">Loading code...</div>
    <div v-else-if="error" class="text-red-400 bg-red-900/20 p-3 rounded-md">Error: {{ error }}</div>
    <pre v-else class="language-{{ fileExtensionClass }}"><code :class="'language-' + fileExtensionClass" v-html="highlightedCode"></code></pre>
    <div v-if="!loading && !error && !fileContent" class="text-center text-gray-400">Select a file to view its content.</div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import hljs from 'highlight.js';
// Import specific languages if needed, e.g., import 'highlight.js/lib/languages/python';
import 'highlight.js/styles/github-dark.css'; // Or your preferred theme

const props = defineProps<{
  sessionId: string;
  filePath: string | null;
}>();

const fileContent = ref<string | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const fileExtension = computed(() => {
  if (!props.filePath) return '';
  const parts = props.filePath.split('.');
  return parts.length > 1 ? parts.pop()?.toLowerCase() : '';
});

const fileExtensionClass = computed(() => {
  // Map common extensions to highlight.js language classes
  switch (fileExtension.value) {
    case 'py': return 'python';
    case 'js': return 'javascript';
    case 'ts': return 'typescript';
    case 'vue': return 'html'; // Vue SFCs often contain HTML, JS, CSS
    case 'html': return 'xml';
    case 'css': return 'css';
    case 'json': return 'json';
    case 'md': return 'markdown';
    case 'yaml':
    case 'yml': return 'yaml';
    case 'sql': return 'sql';
    case 'sh':
    case 'bash': return 'bash';
    // Add more cases for other common languages
    default: return '';
  }
});

const highlightedCode = computed(() => {
  if (!fileContent.value) return '';
  const language = fileExtensionClass.value;
  if (language && hljs.getLanguage(language)) {
    return hljs.highlight(fileContent.value, { language }).value;
  } else {
    return hljs.highlightAuto(fileContent.value).value;
  }
});

const fetchFileContent = async (sessionId: string, filePath: string) => {
  loading.value = true;
  error.value = null;
  fileContent.value = null;
  try {
    const response = await fetch(`/api/session-file-content/${sessionId}/${filePath}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    fileContent.value = data.content;
  } catch (e: any) {
    error.value = e.message;
    console.error('Error fetching file content:', e);
  } finally {
    loading.value = false;
  }
};

watch(() => props.filePath, (newFilePath) => {
  if (props.sessionId && newFilePath) {
    fetchFileContent(props.sessionId, newFilePath);
  } else {
    fileContent.value = null;
  }
}, { immediate: true });
</script>

<style scoped>
.code-viewer pre {
  margin: 0;
  padding: 0;
  white-space: pre-wrap; /* Preserve whitespace and wrap long lines */
  word-break: break-all; /* Break words to prevent overflow */
}

/* Override highlight.js background to match our theme if needed */
.code-viewer :deep(pre code.hljs) {
  background-color: transparent !important;
}
</style> 