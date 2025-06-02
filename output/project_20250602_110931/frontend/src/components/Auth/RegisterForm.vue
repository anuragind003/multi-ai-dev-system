<template>
  <div class="register-form-container">
    <h2>Register</h2>
    <form @submit.prevent="register" class="register-form">
      <div class="form-group">
        <label for="email">Email:</label>
        <input
          type="email"
          id="email"
          v-model="email"
          required
          autocomplete="email"
          placeholder="Enter your email"
        />
      </div>
      <div class="form-group">
        <label for="password">Password:</label>
        <input
          type="password"
          id="password"
          v-model="password"
          required
          autocomplete="new-password"
          placeholder="Enter your password"
        />
      </div>
      <div class="form-group">
        <label for="confirmPassword">Confirm Password:</label>
        <input
          type="password"
          id="confirmPassword"
          v-model="confirmPassword"
          required
          autocomplete="new-password"
          placeholder="Confirm your password"
        />
      </div>

      <button type="submit" :disabled="isLoading" class="submit-button">
        {{ isLoading ? 'Registering...' : 'Register' }}
      </button>

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <p v-if="successMessage" class="success-message">{{ successMessage }}</p>
    </form>
    <p class="login-link">
      Already have an account? <router-link to="/login">Login here</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';
import { useRouter } from 'vue-router'; // Import useRouter for navigation

// Reactive variables for form inputs and state
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const errorMessage = ref('');
const successMessage = ref('');
const isLoading = ref(false);

// Initialize Vue Router for programmatic navigation
const router = useRouter();

/**
 * Handles the user registration process.
 * Performs client-side validation, makes an API call to the backend,
 * and handles success or error responses.
 */
const register = async () => {
  // Clear previous messages
  errorMessage.value = '';
  successMessage.value = '';

  // Client-side validation
  if (password.value !== confirmPassword.value) {
    errorMessage.value = 'Passwords do not match.';
    return;
  }

  if (password.value.length < 6) { // Example: minimum password length
    errorMessage.value = 'Password must be at least 6 characters long.';
    return;
  }

  isLoading.value = true; // Set loading state to true

  try {
    // Make a POST request to the backend registration endpoint
    // Assuming the backend is running on http://localhost:5000
    const response = await axios.post('http://localhost:5000/api/register', {
      email: email.value,
      password: password.value,
    });

    // Handle successful registration
    if (response.status === 201) { // 201 Created is a common status for successful creation
      successMessage.value = response.data.message || 'Registration successful! Redirecting to login...';
      // Clear form fields
      email.value = '';
      password.value = '';
      confirmPassword.value = '';

      // Redirect to login page after a short delay
      setTimeout(() => {
        router.push('/login');
      }, 2000); // Redirect after 2 seconds
    }
  } catch (error) {
    // Handle errors from the API call
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      errorMessage.value = error.response.data.message || 'Registration failed. Please try again.';
    } else if (error.request) {
      // The request was made but no response was received
      errorMessage.value = 'No response from server. Please check your network connection.';
    } else {
      // Something happened in setting up the request that triggered an Error
      errorMessage.value = 'An unexpected error occurred: ' + error.message;
    }
  } finally {
    isLoading.value = false; // Reset loading state
  }
};
</script>

<style scoped>
/* Basic styling for the registration form */
.register-form-container {
  max-width: 400px;
  margin: 50px auto;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background-color: #ffffff;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 25px;
  font-size: 2em;
}

.register-form .form-group {
  margin-bottom: 20px;
}

.register-form label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: bold;
}

.register-form input[type="email"],
.register-form input[type="password"] {
  width: calc(100% - 20px); /* Account for padding */
  padding: 12px 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1em;
  box-sizing: border-box; /* Include padding and border in the element's total width and height */
}

.register-form input[type="email"]:focus,
.register-form input[type="password"]:focus {
  border-color: #007bff;
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
}

.submit-button {
  width: 100%;
  padding: 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 1.1em;
  cursor: pointer;
  transition: background-color 0.3s ease, transform 0.2s ease;
  margin-top: 10px;
}

.submit-button:hover {
  background-color: #0056b3;
  transform: translateY(-1px);
}

.submit-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
  transform: none;
}

.error-message {
  color: #dc3545;
  text-align: center;
  margin-top: 15px;
  font-size: 0.95em;
}

.success-message {
  color: #28a745;
  text-align: center;
  margin-top: 15px;
  font-size: 0.95em;
}

.login-link {
  text-align: center;
  margin-top: 25px;
  color: #666;
}

.login-link a {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>