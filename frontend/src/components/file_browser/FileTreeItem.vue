<template>
  <li>
    <div
      :class="{
        'cursor-pointer': item.type === 'file', 
        'font-semibold': item.type === 'directory',
        'bg-blue-600 text-white': item.type === 'file' && selectedFile === item.path,
        'hover:bg-slate-700': item.type === 'file' && selectedFile !== item.path
      }"
      @click="handleClick"
      class="flex items-center space-x-2 py-1 text-gray-300 rounded-md px-2"
    >
      <template v-if="item.type === 'directory'">
        <span @click.stop="toggleExpand" class="text-blue-400 text-lg">
          <i :class="expanded ? 'i-mdi-folder-open' : 'i-mdi-folder'" />
        </span>
      </template>
      <template v-else>
        <span class="text-gray-500 text-lg"><i :class="getFileIcon(item.name)" /></span>
      </template>
      <span>{{ item.name }}</span>
    </div>
    <ul v-if="item.children && expanded" class="ml-4 space-y-1">
      <FileTreeItem
        v-for="child in item.children"
        :key="child.path"
        :item="child"
        :selected-file="selectedFile"
        @select-file="handleSelectFileFromChild"
      />
    </ul>
  </li>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface FileSystemItem {
  name: string;
  type: 'file' | 'directory';
  path: string;
  size?: number;
  children?: FileSystemItem[];
}

const props = defineProps<{
  item: FileSystemItem;
  selectedFile?: string | null;
}>();

const emit = defineEmits<{
  (e: 'select-file', filePath: string): void;
}>();

const expanded = ref(false);

const toggleExpand = () => {
  if (props.item.type === 'directory') {
    expanded.value = !expanded.value;
  }
};

const handleClick = () => {
  if (props.item.type === 'file') {
    emit('select-file', props.item.path);
  } else {
    toggleExpand();
  }
};

const handleSelectFileFromChild = (filePath: string) => {
  emit('select-file', filePath);
};

const getFileIcon = (fileName: string) => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  switch (extension) {
    case 'py': return 'i-mdi-language-python';
    case 'js':
    case 'ts': return 'i-mdi-language-javascript';
    case 'vue': return 'i-mdi-vuejs';
    case 'html': return 'i-mdi-language-html5';
    case 'css': return 'i-mdi-language-css3';
    case 'json': return 'i-mdi-json';
    case 'md': return 'i-mdi-language-markdown';
    case 'txt': return 'i-mdi-text-box';
    case 'pdf': return 'i-mdi-file-pdf';
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif': return 'i-mdi-file-image';
    default: return 'i-mdi-file';
  }
};
</script>

<style scoped>
/* No specific styles needed here, using utility classes */
</style> 