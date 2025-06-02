const { defineConfig } = require('@vue/cli-service');

module.exports = defineConfig({
  // This option ensures that dependencies listed in `node_modules` are also
  // transpiled by Babel. This is useful for libraries that might not be
  // pre-transpiled to ES5, ensuring broader browser compatibility across browsers.
  transpileDependencies: true,

  // Specifies the directory where the production build artifacts will be placed.
  // The default is 'dist'. Explicitly setting it provides clarity and consistency.
  outputDir: 'dist',

  // Specifies the directory (relative to outputDir) where static assets
  // (like images, fonts, and compiled CSS/JS that are not part of the main bundle)
  // will be placed. The default is an empty string, meaning assets are directly
  // in the outputDir. Setting it to 'static' is a common convention for better
  // organization of the build output.
  assetsDir: 'static',

  // Configuration for the development server provided by Vue CLI.
  // This server is used during development to serve the Vue application
  // and proxy API requests to the backend.
  devServer: {
    // The port on which the development server will run.
    // Default is 8080. You can change this if it conflicts with other services.
    port: 8080,
    // Automatically open the browser to the application URL when the dev server starts.
    open: true,
    // Proxy configuration to forward API requests from the Vue development server
    // to the Flask backend. This is crucial to avoid Cross-Origin Resource Sharing (CORS)
    // issues during development, as the frontend (Vue dev server) and backend (Flask)
    // typically run on different ports or domains.
    proxy: {
      // Any request path starting with '/api' will be intercepted and proxied.
      // For example, a request from Vue to '/api/tasks' will be handled by this proxy.
      '/api': {
        // The target URL of the Flask backend.
        // Assuming the Flask backend is running locally on http://localhost:5000.
        target: 'http://localhost:5000',
        // Changes the origin of the host header to the target URL.
        // This is important for the backend to correctly process the request
        // as if it originated from the backend's own domain, preventing some
        // backend-side CORS issues.
        changeOrigin: true,
        // Enables proxying of WebSocket requests.
        // This is useful if your Flask backend uses WebSockets for real-time
        // communication (e.g., for live task updates).
        ws: true,
        // Path rewrite rule:
        // By default, if pathRewrite is not specified, a request to
        // 'http://localhost:8080/api/tasks' will be forwarded to
        // 'http://localhost:5000/api/tasks'.
        // This setup assumes that your Flask backend also exposes its API
        // endpoints under the '/api' prefix (e.g., Flask route for tasks is '/api/tasks').
        //
        // If your Flask backend's API endpoints *do not* have the '/api' prefix
        // (e.g., Flask route for tasks is just '/tasks'), you would need to
        // uncomment and use the following pathRewrite rule to remove the '/api'
        // prefix before forwarding the request to the backend:
        // pathRewrite: { '^/api': '' }
      }
    }
  },

  // Further Webpack configuration. This allows for deep customization of Webpack's
  // internal configuration. It's not strictly necessary for a basic setup but
  // is powerful for advanced scenarios like adding custom loaders, plugins,
  // or defining custom aliases for import paths.
  configureWebpack: {
    // Example of how to add a custom alias (though '@' is already default for 'src'):
    // resolve: {
    //   alias: {
    //     '@': require('path').resolve(__dirname, 'src')
    //   }
    // }
  },

  // Disables the generation of source maps for production builds.
  // Source maps map compiled code back to original source code, which is great
  // for debugging in development. However, in production, disabling them can
  // slightly improve build performance and prevent exposing your original
  // source code, which can be a minor security consideration.
  productionSourceMap: false,
});