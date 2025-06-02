<template>
  <div :class="['task-item', { 'task-completed': task.completed }]">
    <div class="task-header">
      <input
        type="checkbox"
        :checked="task.completed"
        @change="toggleCompletion"
        class="task-checkbox"
        :id="`task-checkbox-${task.id}`"
      />
      <label :for="`task-checkbox-${task.id}`" class="task-title-label">
        <h3 class="task-title">{{ task.title }}</h3>
      </label>
      <div class="task-actions">
        <button @click="startEditing" class="edit-button" title="Edit Task">
          <i class="fas fa-edit"></i>
        </button>
        <button @click="deleteTask" class="delete-button" title="Delete Task">
          <i class="fas fa-trash-alt"></i>
        </button>
      </div>
    </div>

    <p v-if="task.description" class="task-description">{{ task.description }}</p>
    <p v-if="task.due_date" class="task-due-date">Due: {{ formattedDueDate }}</p>

    <div v-if="isEditing" class="edit-form">
      <input
        type="text"
        v-model="editedTask.title"
        placeholder="Task Title"
        class="edit-input"
      />
      <textarea
        v-model="editedTask.description"
        placeholder="Task Description (optional)"
        class="edit-textarea"
      ></textarea>
      <input
        type="date"
        v-model="editedTask.due_date"
        class="edit-input"
      />
      <div class="edit-form-actions">
        <button @click="saveChanges" class="save-button">Save</button>
        <button @click="cancelEditing" class="cancel-button">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import axios from 'axios'; // For making API requests
import { format } from 'date-fns'; // For date formatting

export default {
  name: 'TaskItem',
  props: {
    task: {
      type: Object,
      required: true,
      validator: (task) => {
        // Basic validation for task object structure
        return (
          typeof task.id === 'number' &&
          typeof task.title === 'string' &&
          typeof task.completed === 'boolean'
        );
      },
    },
  },
  emits: ['task-updated', 'task-deleted'], // Declare events emitted by this component
  setup(props, { emit }) {
    const isEditing = ref(false);
    // Create a deep copy of the task prop for editing to avoid direct mutation
    const editedTask = ref({ ...props.task });

    /**
     * Computed property to format the due date for display.
     * Returns an empty string if due_date is null or invalid.
     */
    const formattedDueDate = computed(() => {
      if (props.task.due_date) {
        try {
          // Ensure the date is parsed correctly before formatting
          return format(new Date(props.task.due_date), 'MMM dd, yyyy');
        } catch (error) {
          console.error('Error formatting due date:', error);
          return '';
        }
      }
      return '';
    });

    /**
     * Toggles the completion status of the task.
     * Makes an API call to update the task on the backend.
     */
    const toggleCompletion = async () => {
      const updatedStatus = !props.task.completed;
      try {
        // Optimistic update for better UX
        emit('task-updated', { ...props.task, completed: updatedStatus });

        const response = await axios.put(
          `/api/tasks/${props.task.id}`,
          { completed: updatedStatus },
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`, // Include auth token
            },
          }
        );
        // If the backend response indicates a different state, update again
        if (response.data.completed !== updatedStatus) {
          emit('task-updated', response.data);
        }
      } catch (error) {
        console.error('Error toggling task completion:', error);
        // Revert optimistic update if API call fails
        emit('task-updated', { ...props.task, completed: !updatedStatus });
        // Optionally, show a user-friendly error message
        alert('Failed to update task status. Please try again.');
      }
    };

    /**
     * Initiates the editing mode for the task.
     * Copies the current task data into the editable form.
     */
    const startEditing = () => {
      editedTask.value = { ...props.task }; // Ensure fresh copy when starting edit
      // Format due_date for input[type="date"] if it exists
      if (editedTask.value.due_date) {
        try {
          editedTask.value.due_date = format(new Date(editedTask.value.due_date), 'yyyy-MM-dd');
        } catch (e) {
          console.error("Error formatting due date for edit input:", e);
          editedTask.value.due_date = null; // Clear if invalid
        }
      } else {
        editedTask.value.due_date = null; // Ensure it's null if not set
      }
      isEditing.value = true;
    };

    /**
     * Saves the changes made to the task.
     * Makes an API call to update the task on the backend.
     */
    const saveChanges = async () => {
      try {
        // Prepare data for API call, removing any undefined or null values for optional fields
        const payload = {
          title: editedTask.value.title,
          description: editedTask.value.description || null, // Send null if empty
          due_date: editedTask.value.due_date || null, // Send null if empty
        };

        const response = await axios.put(
          `/api/tasks/${props.task.id}`,
          payload,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            },
          }
        );
        emit('task-updated', response.data); // Emit event with updated task data
        isEditing.value = false; // Exit editing mode
      } catch (error) {
        console.error('Error saving task changes:', error);
        // Handle specific error messages from backend if available
        const errorMessage = error.response?.data?.message || 'Failed to save changes. Please try again.';
        alert(errorMessage);
      }
    };

    /**
     * Cancels the editing mode and discards any unsaved changes.
     */
    const cancelEditing = () => {
      isEditing.value = false;
      // Reset editedTask to original prop value if needed, though not strictly necessary as it's re-copied on startEditing
    };

    /**
     * Deletes the task.
     * Makes an API call to delete the task from the backend.
     */
    const deleteTask = async () => {
      if (confirm('Are you sure you want to delete this task?')) {
        try {
          await axios.delete(`/api/tasks/${props.task.id}`, {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            },
          });
          emit('task-deleted', props.task.id); // Emit event with the ID of the deleted task
        } catch (error) {
          console.error('Error deleting task:', error);
          alert('Failed to delete task. Please try again.');
        }
      }
    };

    return {
      isEditing,
      editedTask,
      formattedDueDate,
      toggleCompletion,
      startEditing,
      saveChanges,
      cancelEditing,
      deleteTask,
    };
  },
};
</script>

<style scoped>
.task-item {
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 15px 20px;
  margin-bottom: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease-in-out;
  display: flex;
  flex-direction: column;
}

.task-item:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.task-completed {
  background-color: #f0f0f0;
  border-left: 5px solid #4CAF50; /* Green border for completed tasks */
  opacity: 0.7;
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.task-checkbox {
  margin-right: 15px;
  min-width: 20px; /* Ensure checkbox has a consistent size */
  min-height: 20px;
  cursor: pointer;
  accent-color: #007bff; /* Blue accent for checkbox */
}

.task-title-label {
  flex-grow: 1;
  cursor: pointer;
  display: flex; /* To align h3 properly */
  align-items: center;
}

.task-title {
  margin: 0;
  font-size: 1.2em;
  color: #333;
  word-break: break-word; /* Allow long titles to wrap */
}

.task-completed .task-title {
  text-decoration: line-through;
  color: #777;
}

.task-description {
  font-size: 0.9em;
  color: #555;
  margin-top: 0;
  margin-bottom: 8px;
  white-space: pre-wrap; /* Preserve whitespace and line breaks */
  word-break: break-word;
}

.task-due-date {
  font-size: 0.85em;
  color: #888;
  margin-top: 0;
  margin-bottom: 10px;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.edit-button,
.delete-button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1em;
  padding: 5px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.edit-button {
  color: #007bff; /* Blue for edit */
}

.edit-button:hover {
  background-color: #e7f3ff;
}

.delete-button {
  color: #dc3545; /* Red for delete */
}

.delete-button:hover {
  background-color: #ffebeb;
}

/* Font Awesome icons (assuming it's linked in index.html or main.js) */
.fas {
  vertical-align: middle;
}

/* Edit Form Styles */
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #eee;
}

.edit-input,
.edit-textarea {
  width: calc(100% - 20px); /* Account for padding */
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  font-size: 1em;
  box-sizing: border-box; /* Include padding in width */
}

.edit-textarea {
  resize: vertical; /* Allow vertical resizing */
  min-height: 80px;
}

.edit-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 5px;
}

.save-button,
.cancel-button {
  padding: 8px 15px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background-color 0.2s ease;
}

.save-button {
  background-color: #28a745; /* Green for save */
  color: white;
}

.save-button:hover {
  background-color: #218838;
}

.cancel-button {
  background-color: #6c757d; /* Gray for cancel */
  color: white;
}

.cancel-button:hover {
  background-color: #5a6268;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .task-item {
    padding: 10px 15px;
  }

  .task-header {
    flex-wrap: wrap;
  }

  .task-checkbox {
    margin-right: 10px;
  }

  .task-title {
    font-size: 1.1em;
  }

  .task-actions {
    width: 100%;
    justify-content: flex-end;
    margin-top: 10px;
  }

  .edit-button,
  .delete-button {
    font-size: 1em;
    padding: 3px;
  }
}
</style>