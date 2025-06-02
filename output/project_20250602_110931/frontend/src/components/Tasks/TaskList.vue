<template>
  <div class="task-list-container">
    <h2>Your Tasks</h2>

    <!-- Loading indicator displayed while tasks are being fetched -->
    <div v-if="loading" class="loading-indicator">
      Loading tasks...
    </div>

    <!-- Error message displayed if fetching tasks fails -->
    <div v-if="error" class="error-message">
      Error: {{ error }}
    </div>

    <!-- Message displayed if no tasks are found after loading -->
    <div v-if="!loading && !error && tasks.length === 0" class="no-tasks-message">
      No tasks found. Time to create one!
    </div>

    <!-- List of tasks, rendered using TaskItem component -->
    <ul v-if="tasks.length > 0 && !loading" class="task-list">
      <!-- Iterate over the tasks array and render a TaskItem for each task -->
      <TaskItem
        v-for="task in tasks"
        :key="task.id"
        :task="task"
        @task-updated="handleTaskUpdated"
        @task-deleted="handleTaskDeleted"
      />
    </ul>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import axios from 'axios'; // Assuming axios is installed and configured for API calls
import TaskItem from './TaskItem.vue'; // Import the TaskItem component

export default {
  name: 'TaskList',
  components: {
    TaskItem, // Register TaskItem for use in this component's template
  },
  /**
   * Vue 3 Composition API setup function.
   * Manages reactive state and lifecycle hooks for the component.
   */
  setup() {
    // Reactive state variables
    const tasks = ref([]); // Array to store fetched tasks
    const loading = ref(true); // Boolean to indicate loading state
    const error = ref(null); // String to store any error messages

    /**
     * Fetches tasks from the backend API.
     * Sets loading state, handles successful data retrieval, and catches errors.
     */
    const fetchTasks = async () => {
      loading.value = true; // Set loading to true before API call
      error.value = null;   // Clear any previous errors
      try {
        // Make a GET request to the tasks API endpoint.
        // Assumes axios is configured with a base URL and handles authentication (e.g., via interceptors).
        const response = await axios.get('/api/tasks');
        tasks.value = response.data; // Update tasks with data from the response
      } catch (err) {
        console.error('Failed to fetch tasks:', err);
        // Set a user-friendly error message
        error.value = 'Failed to load tasks. Please try again later.';
        // If the error response contains a specific message, use it
        if (err.response && err.response.data && err.response.data.message) {
          error.value = err.response.data.message;
        }
      } finally {
        loading.value = false; // Set loading to false after API call completes (success or failure)
      }
    };

    /**
     * Handles the 'task-updated' event emitted by TaskItem.
     * This event signifies that a task's properties (e.g., completion status) have changed.
     * Updates the specific task in the local `tasks` array to reflect the change.
     * @param {Object} updatedTask - The updated task object received from TaskItem.
     */
    const handleTaskUpdated = (updatedTask) => {
      // Find the index of the updated task in the current tasks array
      const index = tasks.value.findIndex(t => t.id === updatedTask.id);
      if (index !== -1) {
        // Replace the old task object with the new, updated one
        tasks.value[index] = updatedTask;
      }
      // Alternative (simpler but less performant for large lists):
      // Re-fetch all tasks: fetchTasks();
    };

    /**
     * Handles the 'task-deleted' event emitted by TaskItem.
     * This event signifies that a task has been successfully deleted from the backend.
     * Removes the deleted task from the local `tasks` array.
     * @param {number} taskId - The ID of the task that was deleted.
     */
    const handleTaskDeleted = (taskId) => {
      // Filter out the task with the matching ID from the tasks array
      tasks.value = tasks.value.filter(task => task.id !== taskId);
    };

    // Lifecycle hook: Call fetchTasks when the component is mounted to the DOM
    onMounted(() => {
      fetchTasks();
    });

    // Return reactive properties and methods to be used in the template
    return {
      tasks,
      loading,
      error,
      handleTaskUpdated,
      handleTaskDeleted,
    };
  },
};
</script>

<style scoped>
/* Scoped styles ensure these styles only apply to this component */
.task-list-container {
  max-width: 800px;
  margin: 20px auto;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  font-family: 'Arial', sans-serif;
}

h2 {
  color: #333;
  text-align: center;
  margin-bottom: 25px;
  font-size: 2em;
}

/* Common styles for status messages */
.loading-indicator,
.error-message,
.no-tasks-message {
  text-align: center;
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 5px;
  font-weight: bold;
}

.loading-indicator {
  background-color: #e0f7fa; /* Light cyan */
  color: #00796b; /* Dark cyan */
  border: 1px solid #b2ebf2; /* Lighter cyan border */
}

.error-message {
  background-color: #ffebee; /* Light red */
  color: #c62828; /* Dark red */
  border: 1px solid #ef9a9a; /* Lighter red border */
}

.no-tasks-message {
  background-color: #fffde7; /* Light yellow */
  color: #fbc02d; /* Dark yellow */
  border: 1px solid #fff59d; /* Lighter yellow border */
}

.task-list {
  list-style: none; /* Remove default list bullets */
  padding: 0;
  margin: 0;
}

/* Styles for individual TaskItem are expected to be defined within TaskItem.vue */
</style>