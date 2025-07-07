<!-- /src/layouts/AppLayout.vue (MINIMAL TEST) -->
<template>
  <div class="app-layout">
    <AppHeader @toggle-sidebar="toggleSidebar" :is-sidebar-open="isSidebarOpen" />
    <AppSidebar :is-open="isSidebarOpen" @close-sidebar="closeSidebar" />
    <main class="app-main bg-gray-50 p-4 sm:p-6 lg:p-8">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import AppHeader from '@/components/AppHeader.vue';
import AppSidebar from '@/components/AppSidebar.vue';

const isSidebarOpen = ref(false);

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

const closeSidebar = () => {
  isSidebarOpen.value = false;
};
</script>

<style scoped>
.app-layout {
  display: grid;
  grid-template-areas:
    'header header'
    'sidebar main';
  grid-template-columns: auto 1fr;
  grid-template-rows: auto 1fr;
  height: 100vh;
  background-color: #f9fafb; /* Corresponds to bg-gray-50 */
}

.app-main {
  grid-area: main;
  overflow-y: auto;
}

@media (max-width: 1024px) {
  .app-layout {
    grid-template-areas:
      'header'
      'main';
    grid-template-columns: 1fr;
  }
}
</style>
