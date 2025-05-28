const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,

  // Configure output directory for production build
  // This tells Vue CLI to put compiled assets into the Flask static folder
  outputDir: '../backend/static',
  // This tells Vue CLI where to put the index.html file
  // It will be moved to Flask's templates folder
  indexPath: '../backend/templates/index.html',
  // Assets (JS, CSS, images) will be placed in a 'static' subfolder within outputDir
  // e.g., ../backend/static/static/js/app.js
  assetsDir: 'static',

  // Configure development server
  devServer: {
    // Proxy API requests to the Flask backend
    proxy: {
      // Proxy paths for data ingestion
      '^/ingest': {
        target: 'http://localhost:5000', // Flask backend URL
        ws: true, // Enable WebSocket proxying if needed
        changeOrigin: true // Changes the origin of the host header to the target URL
      },
      // Proxy paths for event tracking
      '^/events': {
        target: 'http://localhost:5000',
        ws: true,
        changeOrigin: true
      },
      // Proxy paths for customer data retrieval
      '^/customers': {
        target: 'http://localhost:5000',
        ws: true,
        changeOrigin: true
      },
      // Proxy paths for data exports and reporting
      '^/exports': {
        target: 'http://localhost:5000',
        ws: true,
        changeOrigin: true
      }
      // If the Flask backend were to use a common API prefix like '/api',
      // you could use a single proxy entry like this:
      // '/api': {
      //   target: 'http://localhost:5000',
      //   ws: true,
      //   changeOrigin: true,
      //   pathRewrite: { '^/api': '' } // Remove the /api prefix when forwarding to backend
      // }
    }
  }
})