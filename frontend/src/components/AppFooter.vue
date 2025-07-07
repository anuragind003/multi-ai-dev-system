<!-- /src/components/AppFooter.vue -->
<template>
  <footer class="bg-slate-50 text-gray-600 border-t border-gray-200">
    <div class="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8 text-center md:text-left">
        <!-- Logo and Brand -->
        <div class="space-y-4">
          <div class="flex items-center justify-center md:justify-start space-x-3">
            <img src="@/assets/logo.svg" alt="Logo" class="relative h-10 w-auto rounded-lg" />
            <h3
              class="text-xl font-bold bg-gradient-to-r from-slate-800 to-purple-800 bg-clip-text text-transparent"
            >
              Multi-AI Dev
            </h3>
          </div>
          <p class="text-sm text-gray-500">
            Transforming business requirements into functional applications through AI-powered
            development.
          </p>
        </div>

        <!-- Quick Links -->
        <div class="space-y-4">
          <h4 class="text-sm font-semibold tracking-wider uppercase text-gray-500">Quick Links</h4>
          <nav class="flex flex-col space-y-2">
            <router-link
              v-for="item in navigation.filter((item) => !item.hidden)"
              :key="item.name"
              :to="item.to"
              class="hover:text-indigo-600 transition-colors"
            >
              {{ item.name }}
            </router-link>
          </nav>
        </div>

        <!-- Support -->
        <div class="space-y-4">
          <h4 class="text-sm font-semibold tracking-wider uppercase text-gray-500">Support</h4>
          <ul class="space-y-2">
            <li><a href="#" class="hover:text-indigo-600 transition-colors">Documentation</a></li>
            <li><a href="#" class="hover:text-indigo-600 transition-colors">API Reference</a></li>
            <li><a href="#" class="hover:text-indigo-600 transition-colors">Contact Support</a></li>
          </ul>
        </div>
      </div>
      <div class="mt-12 border-t border-gray-200 pt-8 text-center text-sm text-gray-500">
        <p>
          &copy; {{ new Date().getFullYear() }} Multi-AI Development System. All rights reserved.
        </p>
      </div>
    </div>
  </footer>
</template>
<script setup lang="ts">
import { navigation } from "@/navigation";
</script>
