<template>
  <div class="file-tree bg-slate-900/70 border border-slate-700 rounded-lg p-4 max-h-[70vh] overflow-y-auto">
    <h3 class="text-lg font-semibold text-gray-200 mb-4">Project Files</h3>
    <div v-if="loading" class="text-center text-gray-400">Loading files...</div>
    <div v-else-if="error" class="text-red-400 bg-red-900/20 p-3 rounded-md">Error: {{ error }}</div>
    <ul v-else class="space-y-1">
      <FileTreeItem
        v-for="item in files"
        :key="item.path"
        :item="item"
        @select-file="handleSelectFile"
      />
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import FileTreeItem from './FileTreeItem.vue'; // Will create this nested component next

interface FileSystemItem {
  name: string;
  type: 'file' | 'directory';
  path: string;
  size?: number;
  children?: FileSystemItem[];
}

const props = defineProps<{
  sessionId: string;
}>();

const emit = defineEmits<{
  (e: 'file-selected', filePath: string): void;
}>();

const files = ref<FileSystemItem[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const fetchFileTree = async (sessionId: string) => {
  loading.value = true;
  error.value = null;
  try {
    const response = await fetch(`/api/session-files/${sessionId}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    files.value = data.files || [];
  } catch (e: any) {
    error.value = e.message;
    console.error('Error fetching file tree:', e);
  } finally {
    loading.value = false;
  }
};

const handleSelectFile = (filePath: string) => {
  emit('file-selected', filePath);
};

onMounted(() => {
  if (props.sessionId) {
    fetchFileTree(props.sessionId);
  }
});

watch(() => props.sessionId, (newSessionId) => {
  if (newSessionId) {
    fetchFileTree(newSessionId);
  } else {
    files.value = [];
  }
}, { immediate: true });
</script>

<style scoped>
.file-tree ul {
  list-style: none;
  padding-left: 1rem;
}
</style> 