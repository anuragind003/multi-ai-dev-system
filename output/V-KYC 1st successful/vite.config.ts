import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/// <reference types="vitest" />

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
  },
  resolve: {
    alias: {
      '@': '/src', // Alias for src directory
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts', // Setup file for Vitest
    css: true, // Enable CSS processing for tests
    coverage: {
      provider: 'v8', // or 'istanbul'
      reporter: ['text', 'json', 'html'],
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/coverage/**',
        '**/vite.config.ts',
        '**/tailwind.config.js',
        '**/postcss.config.js',
        '**/src/main.tsx', // Entry point usually not tested directly
        '**/src/App.tsx', // Main app component often tested via routing
        '**/src/setupTests.ts',
        '**/src/types/**',
        '**/src/context/**', // Contexts are tested via components that consume them
        '**/src/services/**', // Services are usually mocked
      ],
    },
  },
});