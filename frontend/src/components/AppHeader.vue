<!-- /src/components/AppHeader.vue -->
<template>
  <header
    class="bg-white shadow-sm sticky top-0 z-30 flex-shrink-0 border-b border-gray-200"
    style="grid-area: header"
  >
    <div class="w-full mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo and Title -->
        <div class="flex items-center space-x-4">
          <!-- Mobile Menu Button -->
          <button
            @click="$emit('toggle-sidebar')"
            class="p-2 rounded-md text-gray-500 hover:bg-gray-100 focus:ring-2 focus:ring-indigo-500 lg:hidden transition-colors"
          >
            <svg class="h-6 w-6" stroke="currentColor" fill="none" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          <!-- Logo -->
          <router-link to="/" class="flex items-center space-x-3">
            <img src="@/assets/logo.svg" alt="Logo" class="relative h-10 w-auto rounded-lg" />

            <!-- Title -->
            <span
              class="text-xl font-bold bg-gradient-to-r from-slate-800 to-purple-800 bg-clip-text text-transparent tracking-tight whitespace-nowrap sm:text-2xl"
            >
              Multi-AI Dev
            </span>
          </router-link>
        </div>

        <!-- Navigation Links -->
        <nav class="hidden md:flex items-center space-x-1">
          <router-link
            v-for="item in navigation.filter((item) => !item.hidden)"
            :key="item.name"
            :to="item.to"
            class="text-gray-600 hover:text-indigo-600 hover:bg-gray-100 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 relative"
            active-class="text-indigo-600 bg-indigo-50 font-semibold"
          >
            {{ item.name }}
          </router-link>
        </nav>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { navigation } from "@/navigation";

defineProps<{ isSidebarOpen: boolean }>();
defineEmits(["toggle-sidebar"]);
</script>
