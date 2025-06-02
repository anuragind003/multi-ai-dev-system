<template>
  <div class="task-form-container">
    <h2>{{ isEditing ? 'Edit Task' : 'Create New Task' }}</h2>
    <form @submit.prevent="handleSubmit" class="task-form">
      <div class="form-group">
        <label for="title">Title:</label>
        <input
          type="text"
          id="title"
          v-model="task.title"
          required
          placeholder="e.g., Buy groceries"
        />
      </div>

      <div class="form-group">
        <label for="description">Description (Optional):</label>
        <textarea
          id="description"
          v-model="task.description"
          rows="4"
          placeholder="e.g., Milk, eggs, bread, vegetables"
        ></textarea>
      </div>

      <div class="form-group">
        <label for="dueDate">Due Date (Optional):</label>
        <input
          type="date"
          id="dueDate"
          v-model="task.due_date"
        />
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary">
          {{ isEditing ? 'Update Task' : 'Create Task' }}
        </button>
        <button type="button" @click="cancelForm" class="btn btn-secondary">
          Cancel
        </button>
      </div>

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    </form>
  </div>
</template>

<script>
import { ref, reactive, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import api from '@/services/api'; // Assuming you have an API service configured

export default {
  name: 'TaskForm',
  props: {
    // Optional prop to pass an existing task object for editing
    initialTask: {
      type: Object,
      default: null,
    },
  },
  emits: ['task-created', 'task-updated', 'form-cancelled'],
  setup(props, { emit }) {
    const router = useRouter();
    const route = useRoute();

    // Reactive task object to hold form data
    const task = reactive({
      title: '',
      description: '',
      due_date: '', // Format YYYY-MM-DD
    });

    const isEditing = ref(false);
    const errorMessage = ref('');

    /**
     * Initializes the form with existing task data if provided (for editing).
     * This can happen either via a prop or a route parameter (e.g., /tasks/edit/:id).
     */
    const initializeForm = async () => {
      const taskId = route.params.id;

      if (props.initialTask) {
        // If initialTask prop is provided, use it directly
        isEditing.value = true;
        Object.assign(task, {
          title: props.initialTask.title,
          description: props.initialTask.description,
          due_date: props.initialTask.due_date ? new Date(props.initialTask.due_date).toISOString().split('T')[0] : '',
        });
      } else if (taskId) {
        // If a task ID is present in the route, fetch the task for editing
        isEditing.value = true;
        try {
          const response = await api.get(`/tasks/${taskId}`);
          const fetchedTask = response.data;
          Object.assign(task, {
            title: fetchedTask.title,
            description: fetchedTask.description,
            // Format due_date to YYYY-MM-DD for input type="date"
            due_date: fetchedTask.due_date ? new Date(fetchedTask.due_date).toISOString().split('T')[0] : '',
          });
        } catch (error) {
          console.error('Error fetching task for editing:', error);
          errorMessage.value = 'Failed to load task for editing. Please try again.';
          // Optionally redirect or handle error more gracefully
          router.push('/tasks'); // Redirect to task list if task not found
        }
      } else {
        // Not editing, reset form for new task creation
        isEditing.value = false;
        resetForm();
      }
    };

    /**
     * Handles form submission for both creating and updating tasks.
     */
    const handleSubmit = async () => {
      errorMessage.value = ''; // Clear previous errors

      // Basic validation
      if (!task.title.trim()) {
        errorMessage.value = 'Task title is required.';
        return;
      }

      try {
        let response;
        const payload = {
          title: task.title,
          description: task.description || null, // Send null if empty
          due_date: task.due_date || null, // Send null if empty
        };

        if (isEditing.value) {
          // Update existing task
          const taskId = props.initialTask ? props.initialTask.id : route.params.id;
          response = await api.put(`/tasks/${taskId}`, payload);
          emit('task-updated', response.data);
          alert('Task updated successfully!');
        } else {
          // Create new task
          response = await api.post('/tasks', payload);
          emit('task-created', response.data);
          alert('Task created successfully!');
        }
        router.push('/tasks'); // Navigate back to the task list after success
      } catch (error) {
        console.error('Error submitting task:', error);
        if (error.response && error.response.data && error.response.data.message) {
          errorMessage.value = error.response.data.message;
        } else {
          errorMessage.value = 'An unexpected error occurred. Please try again.';
        }
      }
    };

    /**
     * Resets the form fields to their initial empty state.
     */
    const resetForm = () => {
      task.title = '';
      task.description = '';
      task.due_date = '';
      errorMessage.value = '';
    };

    /**
     * Handles the cancellation of the form, typically by navigating back or emitting an event.
     */
    const cancelForm = () => {
      emit('form-cancelled');
      router.push('/tasks'); // Navigate back to the task list
    };

    // Lifecycle hook: Initialize form when component is mounted
    onMounted(initializeForm);

    // Watch for changes in route params (e.g., navigating from /tasks/new to /tasks/edit/1)
    // or changes in initialTask prop (if component is reused without unmounting)
    watch(() => route.params.id, initializeForm);
    watch(() => props.initialTask, initializeForm, { deep: true });


    return {
      task,
      isEditing,
      errorMessage,
      handleSubmit,
      cancelForm,
    };
  },
};
</script>

<style scoped>
.task-form-container {
  max-width: 600px;
  margin: 40px auto;
  padding: 30px;
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 1.8em;
}

.task-form .form-group {
  margin-bottom: 20px;
}

.task-form label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #555;
}

.task-form input[type="text"],
.task-form input[type="date"],
.task-form textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1em;
  box-sizing: border-box; /* Include padding and border in the element's total width and height */
}

.task-form input[type="text"]:focus,
.task-form input[type="date"]:focus,
.task-form textarea:focus {
  border-color: #007bff;
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
}

.task-form textarea {
  resize: vertical; /* Allow vertical resizing */
  min-height: 80px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  margin-top: 30px;
}

.btn {
  padding: 12px 25px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.3s ease, transform 0.2s ease;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
  transform: translateY(-2px);
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #5a6268;
  transform: translateY(-2px);
}

.error-message {
  color: #dc3545;
  margin-top: 15px;
  text-align: center;
  font-weight: bold;
}
</style>