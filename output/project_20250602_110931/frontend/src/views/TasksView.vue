<template>
  <div class="tasks-view">
    <h1>My Tasks</h1>

    <!-- Loading Indicator -->
    <div v-if="loading" class="loading-indicator">Loading tasks...</div>

    <!-- Global Error Message -->
    <div v-if="error" class="error-message">{{ error }}</div>

    <!-- Task Creation Form -->
    <div class="task-form-container">
      <h2>Add New Task</h2>
      <form @submit.prevent="handleCreateTask" class="task-form">
        <div class="form-group">
          <label for="new-task-title">Title:</label>
          <input type="text" id="new-task-title" v-model="newTask.title" required />
        </div>
        <div class="form-group">
          <label for="new-task-description">Description (Optional):</label>
          <textarea id="new-task-description" v-model="newTask.description"></textarea>
        </div>
        <div class="form-group">
          <label for="new-task-due-date">Due Date (Optional):</label>
          <input type="date" id="new-task-due-date" v-model="newTask.due_date" />
        </div>
        <button type="submit" :disabled="creatingTask">
          {{ creatingTask ? 'Adding...' : 'Add Task' }}
        </button>
        <div v-if="createError" class="error-message">{{ createError }}</div>
      </form>
    </div>

    <!-- Task List -->
    <div v-if="tasks.length > 0" class="task-list">
      <h2>Your Current Tasks</h2>
      <div v-for="task in tasks" :key="task.id" :class="['task-item', { 'completed': task.completed }]">
        <div class="task-header">
          <h3>{{ task.title }}</h3>
          <div class="task-actions">
            <button @click="toggleTaskCompletion(task)" class="complete-button">
              {{ task.completed ? 'Unmark' : 'Complete' }}
            </button>
            <button @click="startEditing(task)" class="edit-button">Edit</button>
            <button @click="handleDeleteTask(task.id)" class="delete-button">Delete</button>
          </div>
        </div>
        <p v-if="task.description">{{ task.description }}</p>
        <p v-if="task.due_date" class="due-date">Due: {{ formatDate(task.due_date) }}</p>

        <!-- Edit Form (Conditional) -->
        <div v-if="editingTask && editingTask.id === task.id" class="edit-form-container">
          <h4>Edit Task</h4>
          <form @submit.prevent="handleUpdateTask" class="task-form">
            <div class="form-group">
              <label :for="`edit-title-${task.id}`">Title:</label>
              <input type="text" :id="`edit-title-${task.id}`" v-model="editingTask.title" required />
            </div>
            <div class="form-group">
              <label :for="`edit-description-${task.id}`">Description:</label>
              <textarea :id="`edit-description-${task.id}`" v-model="editingTask.description"></textarea>
            </div>
            <div class="form-group">
              <label :for="`edit-due-date-${task.id}`">Due Date:</label>
              <input type="date" :id="`edit-due-date-${task.id}`" v-model="editingTask.due_date" />
            </div>
            <button type="submit" :disabled="updatingTask">
              {{ updatingTask ? 'Updating...' : 'Save Changes' }}
            </button>
            <button type="button" @click="cancelEditing">Cancel</button>
            <div v-if="updateError" class="error-message">{{ updateError }}</div>
          </form>
        </div>
      </div>
    </div>

    <div v-else-if="!loading && !error" class="no-tasks-message">
      You don't have any tasks yet. Add one above!
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios'; // Axios is used for making HTTP requests

// Base URL for the API, retrieved from environment variables (e.g., .env file for Vite)
// Defaults to http://localhost:5000/api if VITE_API_BASE_URL is not set.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

// Reactive state variables for managing tasks and UI state
const tasks = ref([]); // Array to store fetched tasks
const loading = ref(true); // Indicates if tasks are currently being loaded
const error = ref(null); // Stores general error messages

// State for new task creation form
const newTask = ref({
  title: '',
  description: '',
  due_date: '' // Will be in YYYY-MM-DD format for input[type="date"]
});
const creatingTask = ref(false); // Indicates if a new task is being created
const createError = ref(null); // Stores error messages specific to task creation

// State for task editing
const editingTask = ref(null); // Stores the task object currently being edited (a copy)
const updatingTask = ref(false); // Indicates if a task update is in progress
const updateError = ref(null); // Stores error messages specific to task updates

/**
 * Retrieves the authentication token from local storage.
 * This token is expected to be set upon successful user login.
 * @returns {string|null} The authentication token or null if not found.
 */
const getAuthToken = () => {
  return localStorage.getItem('authToken');
};

/**
 * Formats a date string into a more readable format (e.g., "Month Day, Year").
 * Handles cases where the date string might be null or invalid.
 * @param {string|null} dateString - The date string to format (e.g., "YYYY-MM-DD").
 * @returns {string} The formatted date or a default message.
 */
const formatDate = (dateString) => {
  if (!dateString) return 'No Due Date';
  try {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString(undefined, options);
  } catch (e) {
    console.error("Error formatting date:", e);
    return dateString; // Fallback to original string if parsing fails
  }
};

// --- API Interaction Functions ---

/**
 * Fetches all tasks for the authenticated user from the backend.
 * Updates `tasks` array, `loading` and `error` states.
 */
const fetchTasks = async () => {
  loading.value = true;
  error.value = null; // Clear previous errors
  const token = getAuthToken();

  if (!token) {
    error.value = 'Authentication required. Please log in.';
    loading.value = false;
    // In a real application, you might redirect to the login page here
    // import { useRouter } from 'vue-router';
    // const router = useRouter();
    // router.push('/login');
    return;
  }

  try {
    const response = await axios.get(`${API_BASE_URL}/tasks`, {
      headers: {
        Authorization: `Bearer ${token}` // Send authentication token
      }
    });
    tasks.value = response.data; // Assign fetched tasks to reactive variable
  } catch (err) {
    console.error('Error fetching tasks:', err);
    if (err.response && err.response.status === 401) {
      error.value = 'Session expired or unauthorized. Please log in again.';
      localStorage.removeItem('authToken'); // Clear invalid token
      // router.push('/login'); // Redirect to login
    } else {
      error.value = 'Failed to load tasks. Please try again later.';
    }
  } finally {
    loading.value = false; // End loading state
  }
};

/**
 * Handles the submission of the new task form.
 * Sends a POST request to create a new task.
 */
const handleCreateTask = async () => {
  creatingTask.value = true;
  createError.value = null; // Clear previous creation errors
  const token = getAuthToken();

  if (!token) {
    createError.value = 'Authentication required. Please log in.';
    creatingTask.value = false;
    return;
  }

  // Prepare task data, ensuring description and due_date are null if empty strings
  const taskData = {
    title: newTask.value.title,
    description: newTask.value.description || null,
    due_date: newTask.value.due_date || null // Send null if empty string
  };

  try {
    const response = await axios.post(`${API_BASE_URL}/tasks`, taskData, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    tasks.value.push(response.data); // Add the newly created task to the list
    // Reset the form fields after successful creation
    newTask.value = { title: '', description: '', due_date: '' };
  } catch (err) {
    console.error('Error creating task:', err);
    createError.value = 'Failed to create task. ' + (err.response?.data?.message || 'Please try again.');
  } finally {
    creatingTask.value = false; // End creating state
  }
};

/**
 * Toggles the completion status of a given task.
 * Performs an optimistic update on the UI, then sends a PUT request to the backend.
 * @param {Object} task - The task object to update.
 */
const toggleTaskCompletion = async (task) => {
  const originalCompletedStatus = task.completed; // Store original status for rollback
  task.completed = !task.completed; // Optimistic UI update

  const token = getAuthToken();
  if (!token) {
    error.value = 'Authentication required. Please log in.';
    task.completed = originalCompletedStatus; // Revert optimistic update on auth error
    return;
  }

  try {
    await axios.put(`${API_BASE_URL}/tasks/${task.id}`, { completed: task.completed }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    // If successful, no further action needed as UI is already updated
  } catch (err) {
    console.error('Error updating task completion:', err);
    error.value = 'Failed to update task status. Please try again.';
    task.completed = originalCompletedStatus; // Revert UI on API error
  }
};

/**
 * Initiates the editing process for a task.
 * Creates a deep copy of the task to allow isolated editing.
 * @param {Object} task - The task object to be edited.
 */
const startEditing = (task) => {
  // Create a shallow copy of the task object to avoid direct mutation of the original
  // in the `tasks` array. This allows for a "cancel" feature.
  editingTask.value = { ...task };
  // Format due_date for the HTML date input (YYYY-MM-DD)
  if (editingTask.value.due_date) {
    editingTask.value.due_date = new Date(editingTask.value.due_date).toISOString().split('T')[0];
  }
};

/**
 * Cancels the current task editing process, discarding any changes.
 */
const cancelEditing = () => {
  editingTask.value = null; // Clear the editing task
  updateError.value = null; // Clear any update-specific errors
};

/**
 * Handles the submission of the task edit form.
 * Sends a PUT request to update the task details.
 */
const handleUpdateTask = async () => {
  if (!editingTask.value) return; // Should not happen if edit form is visible

  updatingTask.value = true;
  updateError.value = null; // Clear previous update errors
  const token = getAuthToken();

  if (!token) {
    updateError.value = 'Authentication required. Please log in.';
    updatingTask.value = false;
    return;
  }

  const taskId = editingTask.value.id;
  // Prepare updated task data, ensuring description and due_date are null if empty
  const updatedData = {
    title: editingTask.value.title,
    description: editingTask.value.description || null,
    due_date: editingTask.value.due_date || null, // Send null if empty string
    completed: editingTask.value.completed // Maintain current completion status
  };

  try {
    const response = await axios.put(`${API_BASE_URL}/tasks/${taskId}`, updatedData, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    // Find the task in the main `tasks` array and update it with the fresh data from the server
    const index = tasks.value.findIndex(t => t.id === taskId);
    if (index !== -1) {
      tasks.value[index] = response.data;
    }
    cancelEditing(); // Exit edit mode after successful update
  } catch (err) {
    console.error('Error updating task:', err);
    updateError.value = 'Failed to update task. ' + (err.response?.data?.message || 'Please try again.');
  } finally {
    updatingTask.value = false; // End updating state
  }
};

/**
 * Handles the deletion of a task.
 * Prompts for confirmation before sending a DELETE request.
 * @param {number} taskId - The ID of the task to delete.
 */
const handleDeleteTask = async (taskId) => {
  if (!confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
    return; // User cancelled deletion
  }

  const token = getAuthToken();
  if (!token) {
    error.value = 'Authentication required. Please log in.';
    return;
  }

  try {
    await axios.delete(`${API_BASE_URL}/tasks/${taskId}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    // Remove the task from the local `tasks` array to update UI
    tasks.value = tasks.value.filter(task => task.id !== taskId);
  } catch (err) {
    console.error('Error deleting task:', err);
    error.value = 'Failed to delete task. ' + (err.response?.data?.message || 'Please try again.');
  }
};

// --- Lifecycle Hook ---
// When the component is mounted, fetch the tasks.
onMounted(() => {
  fetchTasks();
});
</script>

<style scoped>
/* Base container for the tasks view */
.tasks-view {
  max-width: 800px;
  margin: 40px auto;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  font-family: 'Arial', sans-serif;
}

/* Headings */
h1, h2 {
  color: #333;
  text-align: center;
  margin-bottom: 20px;
}

/* General message styles (loading, error, no tasks) */
.loading-indicator, .error-message, .no-tasks-message {
  text-align: center;
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 5px;
  font-weight: bold;
}

.loading-indicator {
  background-color: #e0f7fa; /* Light cyan */
  color: #00796b; /* Dark cyan */
  border: 1px solid #b2ebf2;
}

.error-message {
  background-color: #ffebee; /* Light red */
  color: #c62828; /* Dark red */
  border: 1px solid #ef9a9a;
}

.no-tasks-message {
  background-color: #fffde7; /* Light yellow */
  color: #fbc02d; /* Dark yellow */
  border: 1px solid #fff59d;
}

/* Task Form Container (for both new task and edit task) */
.task-form-container, .edit-form-container {
  background-color: #ffffff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
  margin-bottom: 30px;
}

.task-form .form-group {
  margin-bottom: 15px;
}

.task-form label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #555;
}

.task-form input[type="text"],
.task-form input[type="date"],
.task-form textarea {
  width: calc(100% - 22px); /* Account for padding and border */
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  box-sizing: border-box; /* Include padding and border in the element's total width and height */
}

.task-form textarea {
  resize: vertical; /* Allow vertical resizing */
  min-height: 60px;
}

.task-form button {
  background-color: #4CAF50; /* Green */
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s ease;
  margin-right: 10px; /* Space between buttons */
}

.task-form button:hover:not(:disabled) {
  background-color: #45a049; /* Darker green on hover */
}

.task-form button:disabled {
  background-color: #a5d6a7; /* Lighter green when disabled */
  cursor: not-allowed;
}

/* Task List Styling */
.task-list {
  margin-top: 30px;
}

.task-item {
  background-color: #ffffff;
  padding: 15px 20px;
  margin-bottom: 15px;
  border-radius: 8px;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
  border-left: 5px solid #2196F3; /* Default blue border */
  transition: border-color 0.3s ease, opacity 0.3s ease;
}

.task-item.completed {
  border-left-color: #8BC34A; /* Green for completed tasks */
  opacity: 0.8; /* Slightly fade completed tasks */
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.task-header h3 {
  margin: 0;
  color: #333;
  font-size: 1.2em;
}

.task-item.completed h3 {
  text-decoration: line-through; /* Strikethrough for completed task titles */
  color: #777;
}

.task-item p {
  color: #666;
  margin-bottom: 5px;
}

.task-item .due-date {
  font-size: 0.9em;
  color: #888;
  font-style: italic;
}

.task-actions button {
  background-color: #007bff; /* Blue */
  color: white;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  margin-left: 8px; /* Space between action buttons */
  transition: background-color 0.3s ease;
}

.task-actions button.complete-button {
  background-color: #28a745; /* Green for complete button */
}

.task-actions button.complete-button:hover {
  background-color: #218838;
}

.task-actions button.edit-button {
  background-color: #ffc107; /* Yellow for edit button */
  color: #333; /* Dark text for contrast on yellow */
}

.task-actions button.edit-button:hover {
  background-color: #e0a800;
}

.task-actions button.delete-button {
  background-color: #dc3545; /* Red for delete button */
}

.task-actions button.delete-button:hover {
  background-color: #c82333;
}

.task-actions button:hover {
  opacity: 0.9;
}

/* Specific styles for the edit form within a task item */
.edit-form-container {
  margin-top: 15px;
  border-top: 1px solid #eee;
  padding-top: 15px;
  box-shadow: none; /* Remove extra shadow for nested form */
  background-color: #fcfcfc; /* Slightly different background for nested form */
}

.edit-form-container h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #555;
}
</style>