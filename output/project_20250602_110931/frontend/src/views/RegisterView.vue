<template>
  <div class="register-container">
    <h2>Register for Task Tracker</h2>
    <form @submit.prevent="register" class="register-form">
      <div class="form-group">
        <label for="email">Email:</label>
        <input
          type="email"
          id="email"
          v-model="email"
          required
          placeholder="Enter your email"
          autocomplete="email"
        />
      </div>
      <div class="form-group">
        <label for="password">Password:</label>
        <input
          type="password"
          id="password"
          v-model="password"
          required
          placeholder="Enter your password"
          autocomplete="new-password"
        />
      </div>
      <button type="submit" :disabled="isLoading" class="register-button">
        {{ isLoading ? 'Registering...' : 'Register' }}
      </button>
    </form>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-message">{{ successMessage }}</p>

    <p class="login-link">
      Already have an account? <router-link to="/login">Login here</router-link>
    </p>
  </div>
</template>

<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios'; // Ensure axios is installed: npm install axios

export default {
  name: 'RegisterView',
  /**
   * The setup function is the entry point for Composition API in Vue 3.
   * It's where reactive state, computed properties, watchers, and methods are declared.
   */
  setup() {
    // Reactive references for form inputs and messages
    const email = ref('');
    const password = ref('');
    const errorMessage = ref('');
    const successMessage = ref('');
    const isLoading = ref(false); // To manage button state during API call

    // Vue Router instance for programmatic navigation
    const router = useRouter();

    // Base URL for the backend API.
    // It's recommended to use environment variables for API URLs in production.
    // For Vite, use import.meta.env.VITE_API_BASE_URL. For Vue CLI, use process.env.VUE_APP_API_BASE_URL.
    // A fallback is provided for local development.
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

    /**
     * Handles the user registration process.
     * Sends a POST request to the backend API with user credentials.
     * Manages loading state, error messages, and success messages.
     */
    const register = async () => {
      // Clear any previous messages
      errorMessage.value = '';
      successMessage.value = '';
      isLoading.value = true; // Set loading state to true

      // Basic client-side validation: ensure fields are not empty
      if (!email.value || !password.value) {
        errorMessage.value = 'Email and password are required.';
        isLoading.value = false;
        return;
      }

      try {
        // Make the POST request to the registration endpoint
        const response = await axios.post(`${API_BASE_URL}/register`, {
          email: email.value,
          password: password.value,
        });

        // Check for successful registration (HTTP 201 Created)
        if (response.status === 201) {
          successMessage.value = 'Registration successful! Redirecting to login...';
          // Clear form fields after successful registration
          email.value = '';
          password.value = '';
          // Redirect to the login page after a short delay to show the success message
          setTimeout(() => {
            router.push('/login');
          }, 2000);
        } else {
          // This block handles unexpected successful status codes (e.g., 200 OK but not 201 Created)
          // Axios typically throws an error for non-2xx responses, so this might be rarely hit.
          errorMessage.value = response.data.message || 'An unexpected error occurred during registration.';
        }
      } catch (error) {
        // Log the full error for debugging purposes
        console.error('Registration error:', error);

        // Handle different types of errors from the API call
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx (e.g., 400, 409, 500)
          if (error.response.status === 409) {
            // Conflict: e.g., email already exists
            errorMessage.value = error.response.data.message || 'An account with this email already exists.';
          } else if (error.response.status === 400) {
            // Bad Request: e.g., invalid input format, weak password
            errorMessage.value = error.response.data.message || 'Invalid email or password format. Please check requirements.';
          } else {
            // Other server-side errors
            errorMessage.value = error.response.data.message || 'Server error during registration. Please try again.';
          }
        } else if (error.request) {
          // The request was made but no response was received (e.g., network error, CORS issue)
          errorMessage.value = 'No response from server. Please check your internet connection or server status.';
        } else {
          // Something happened in setting up the request that triggered an Error
          errorMessage.value = 'Error setting up registration request. Please try again.';
        }
      } finally {
        isLoading.value = false; // Always reset loading state, regardless of success or failure
      }
    };

    // Return reactive properties and methods to be used in the template
    return {
      email,
      password,
      errorMessage,
      successMessage,
      isLoading,
      register,
    };
  },
};
</script>

<style scoped>
/* Scoped styles ensure these styles only apply to this component */
.register-container {
  max-width: 400px;
  margin: 50px auto;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background-color: #ffffff;
  text-align: center;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h2 {
  color: #333;
  margin-bottom: 25px;
  font-size: 1.8em;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 18px; /* Space between form groups */
}

.form-group {
  text-align: left;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 600;
}

.form-group input[type="email"],
.form-group input[type="password"] {
  width: calc(100% - 20px); /* Full width minus padding */
  padding: 12px 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1em;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.form-group input[type="email"]:focus,
.form-group input[type="password"]:focus {
  border-color: #007bff;
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
}

.register-button {
  background-color: #007bff;
  color: white;
  padding: 12px 20px;
  border: none;
  border-radius: 5px;
  font-size: 1.1em;
  cursor: pointer;
  transition: background-color 0.3s ease, transform 0.2s ease;
  margin-top: 10px;
  font-weight: 600;
}

.register-button:hover:not(:disabled) {
  background-color: #0056b3;
  transform: translateY(-1px);
}

.register-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
  opacity: 0.8;
}

.error-message {
  color: #dc3545; /* Red for errors */
  margin-top: 15px;
  font-size: 0.95em;
  font-weight: 500;
}

.success-message {
  color: #28a745; /* Green for success */
  margin-top: 15px;
  font-size: 0.95em;
  font-weight: 500;
}

.login-link {
  margin-top: 25px;
  font-size: 0.95em;
  color: #666;
}

.login-link a {
  color: #007bff;
  text-decoration: none;
  font-weight: 600;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>