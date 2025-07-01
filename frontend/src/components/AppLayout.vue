<template>
  <div class="min-h-screen bg-gray-100 text-gray-800">
    <header class="bg-white shadow-md">
      <nav class="container mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="text-2xl font-bold text-gray-800">
            <router-link to="/">Multi-AI Dev System</router-link>
          </div>
          <div class="flex space-x-4">
            <router-link to="/" class="text-gray-600 hover:text-gray-800">New Project</router-link>
            <router-link to="/workflow" class="text-gray-600 hover:text-gray-800"
              >Workflow Monitor</router-link
            >
          </div>
        </div>
      </nav>
    </header>
    <main class="container mx-auto p-6">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
// This component provides the main layout structure for the application.
</script>
