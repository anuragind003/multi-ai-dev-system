<template>
  <div class="login-container">
    <div class="login-card">
      <h2>Login</h2>
      <form @submit.prevent="handleLogin">
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
            autocomplete="current-password"
            placeholder="Enter your password"
          />
        </div>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      </form>
      <p class="register-link">
        Don't have an account? <router-link to="/register">Register here</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios'; // Assuming axios is installed and configured

// Reactive variables for form inputs and state
const email = ref('');
const password = ref('');
const errorMessage = ref('');
const loading = ref(false);

// Get the router instance for navigation
const router = useRouter();

/**
 * Handles the login form submission.
 * Sends a POST request to the backend login endpoint.
 */
const handleLogin = async () => {
  errorMessage.value = ''; // Clear previous error messages
  loading.value = true; // Set loading state to true

  try {
    // Make an API call to the backend login endpoint
    // Adjust the URL based on your Flask backend's actual endpoint
    const response = await axios.post('http://localhost:5000/api/login', {
      email: email.value,
      password: password.value,
    });

    // Assuming the backend returns a token upon successful login
    const token = response.data.token;
    if (token) {
      // Store the token securely (e.g., in localStorage or Vuex/Pinia store)
      // For simplicity, using localStorage here. In a real app, consider HttpOnly cookies or a more robust state management.
      localStorage.setItem('authToken', token);
      
      // Redirect to the dashboard or a protected route
      router.push('/dashboard');
    } else {
      errorMessage.value = 'Login successful, but no token received.';
    }
  } catch (error) {
    // Handle different types of errors
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      errorMessage.value = error.response.data.message || 'Login failed. Please check your credentials.';
    } else if (error.request) {
      // The request was made but no response was received
      errorMessage.value = 'No response from server. Please check your network connection.';
    } else {
      // Something happened in setting up the request that triggered an Error
      errorMessage.value = 'An unexpected error occurred during login.';
    }
    console.error('Login error:', error);
  } finally {
    loading.value = false; // Reset loading state
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f0f2f5;
  padding: 20px;
}

.login-card {
  background: #fff;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
  text-align: center;
}

h2 {
  margin-bottom: 30px;
  color: #333;
  font-size: 2em;
}

.form-group {
  margin-bottom: 20px;
  text-align: left;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: bold;
}

input[type="email"],
input[type="password"] {
  width: calc(100% - 20px); /* Account for padding */
  padding: 12px 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1em;
  box-sizing: border-box; /* Include padding and border in the element's total width and height */
}

input[type="email"]:focus,
input[type="password"]:focus {
  border-color: #007bff;
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
}

button {
  width: 100%;
  padding: 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 1.1em;
  cursor: pointer;
  transition: background-color 0.3s ease;
  margin-top: 10px;
}

button:hover {
  background-color: #0056b3;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.error-message {
  color: #dc3545;
  margin-top: 15px;
  font-size: 0.9em;
}

.register-link {
  margin-top: 25px;
  color: #666;
}

.register-link a {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>