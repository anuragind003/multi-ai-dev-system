<template>
  <footer class="app-footer">
    <div class="footer-content">
      <p>&copy; {{ currentYear }} Simple Task Tracker. All rights reserved.</p>
      <p>Built with Vue.js and Flask.</p>
    </div>
  </footer>
</template>

<script>
export default {
  name: 'AppFooter',
  /**
   * Data properties for the component.
   * @returns {object} An object containing the component's data.
   */
  data() {
    return {
      /**
       * The current year, dynamically calculated to keep the copyright up-to-date.
       * @type {number}
       */
      currentYear: new Date().getFullYear(),
    };
  },
};
</script>

<style scoped>
/*
 * Scoped styles for the Footer component.
 * These styles will only apply to this component, preventing global style conflicts.
 */
.app-footer {
  background-color: #333; /* Dark background for the footer */
  color: #fff; /* White text color */
  padding: 20px 0; /* Vertical padding */
  text-align: center; /* Center-align text */
  font-size: 0.9em; /* Slightly smaller font size */
  width: 100%; /* Full width */
  box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.2); /* Subtle shadow at the top */
  margin-top: auto; /* Pushes the footer to the bottom if content is short */
  flex-shrink: 0; /* Prevents the footer from shrinking */
}

.footer-content {
  max-width: 960px; /* Max width for content alignment */
  margin: 0 auto; /* Center the content horizontally */
  padding: 0 20px; /* Horizontal padding for smaller screens */
}

.app-footer p {
  margin: 5px 0; /* Small margin between paragraphs */
  line-height: 1.5; /* Improve readability */
}

/*
 * Media queries for responsiveness.
 * Adjusts padding and font size for smaller screens.
 */
@media (max-width: 768px) {
  .app-footer {
    padding: 15px 0;
  }

  .app-footer p {
    font-size: 0.85em;
  }
}
</style>