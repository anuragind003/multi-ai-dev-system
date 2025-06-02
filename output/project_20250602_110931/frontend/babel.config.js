module.exports = {
  // Presets are ordered from last to first (bottom to top) in terms of execution.
  // However, for Babel, the order of presets in the array matters for how they are applied.
  // Generally, `@babel/preset-env` should come first to handle general JS features,
  // followed by framework-specific presets like `@babel/preset-react`.
  presets: [
    /**
     * @babel/preset-env
     * Transpiles modern JavaScript into a compatible version for target environments.
     * It intelligently determines the Babel plugins and core-js polyfills needed
     * based on your target browsers or Node.js versions, optimizing bundle size.
     */
    [
      '@babel/preset-env',
      {
        // `targets` specifies the environments you want to support.
        // This configuration targets browsers with more than 0.25% market share
        // and excludes browsers that are considered "dead" (no longer supported).
        // This provides a good balance between modern features and broad compatibility.
        targets: {
          browsers: '> 0.25%, not dead',
        },
        // `useBuiltIns: 'usage'` automatically injects polyfills when they are used in your code.
        // This helps to reduce bundle size by only including necessary polyfills,
        // rather than polyfilling the entire environment.
        // Requires `core-js` to be installed as a dependency.
        useBuiltIns: 'usage',
        // Specifies the version of `core-js` to use for polyfills.
        // `proposals: true` includes polyfills for ECMAScript proposals that are stage 3 or higher.
        corejs: { version: 3, proposals: true },
      },
    ],
    /**
     * @babel/preset-react
     * Transpiles JSX and other React-specific syntax into standard JavaScript.
     * It includes transformations for JSX, React's Fragment syntax, and more.
     */
    [
      '@babel/preset-react',
      {
        // `runtime: 'automatic'` allows you to use JSX without explicitly importing React
        // in every file. This is the recommended approach for React 17 and later,
        // as it automatically imports the necessary JSX runtime functions.
        runtime: 'automatic',
      },
    ],
  ],
  /**
   * Plugins are used for specific transformations that are not covered by presets,
   * or for fine-grained control over the transpilation process.
   * They are executed before presets.
   * For a basic modern React application, presets often suffice, but plugins
   * can be added here for features like class properties, decorators, etc.
   */
  plugins: [],
};