import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // Configure the development server
    port: 8080, // Frontend development server will run on port 8080
    proxy: {
      // Proxy API requests to the Flask backend, which is assumed to run on port 5000
      // This is crucial for development to avoid CORS issues when frontend and backend are on different ports.
      '/api': {
        target: 'http://localhost:5000', // Flask backend URL
        changeOrigin: true, // Needed for virtual hosted sites
        // rewrite: (path) => path.replace(/^\/api/, ''), // Uncomment if Flask endpoints don't have /api prefix
      },
      '/admin': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/customers': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/campaigns': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/data': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      // Add any other top-level paths that Flask serves directly
      // For example, if Flask serves a /login page or static assets from root
      // '/': {
      //   target: 'http://localhost:5000',
      //   changeOrigin: true,
      //   // Ensure that requests for static assets (like index.html) are not proxied
      //   // This might require more specific proxy rules or a fallback for SPA routing
      //   bypass: (req, res, options) => {
      //     if (req.headers.accept.indexOf('html') !== -1) {
      //       return '/index.html';
      //     }
      //   },
      // },
    },
  },
  build: {
    // Output directory for the production build.
    // Assuming the Flask backend will serve static files from a 'dist' folder
    // located at the project root (one level up from 'frontend').
    outDir: '../dist',
    emptyOutDir: true, // Clear the output directory before building
  },
  resolve: {
    // Configure path aliases for easier imports
    alias: {
      '@': '/src', // Allows importing components/modules using @/components/MyComponent.vue
    },
  },
});