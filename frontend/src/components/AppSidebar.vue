<!-- /src/components/AppSidebar.vue -->
<template>
  <!-- Overlay backdrop -->
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
    @click="$emit('close-sidebar')"
  ></div>

  <aside
    :class="[
      'bg-slate-800 text-gray-300 w-64 flex-shrink-0 transform transition-transform duration-300 ease-in-out z-40',
      'lg:translate-x-0 lg:h-full lg:relative',
      isOpen ? 'translate-x-0 fixed h-full' : '-translate-x-full absolute',
    ]"
    style="grid-area: sidebar"
  >
    <div class="flex items-center justify-between h-16 px-4 border-b border-white/10 lg:hidden">
      <h1 class="text-lg font-bold text-white tracking-wider">Navigation</h1>
      <button
        @click="$emit('close-sidebar')"
        class="p-2 rounded-md text-gray-400 hover:bg-white/10 hover:text-white lg:hidden transition-colors"
      >
        <svg class="h-6 w-6" stroke="currentColor" fill="none" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>

    <!-- Navigation links -->
    <div class="p-4 overflow-y-auto h-full">
      <nav class="space-y-2">
        <router-link
          v-for="item in navigation.filter((item) => !item.hidden)"
          :key="item.name"
          :to="item.to"
          @click="$emit('close-sidebar')"
          class="group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg hover:bg-white/5 hover:text-white transition-all duration-200"
          active-class="bg-indigo-600 !text-white !font-semibold shadow-lg"
        >
          <component
            :is="item.icon"
            class="mr-3 h-6 w-6 text-indigo-400 group-hover:text-indigo-300 transition-colors"
            aria-hidden="true"
          />
          <span>{{ item.name }}</span>
        </router-link>
      </nav>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { navigation } from "@/navigation";
defineProps<{ isOpen: boolean }>();
defineEmits(["close-sidebar"]);
</script>
