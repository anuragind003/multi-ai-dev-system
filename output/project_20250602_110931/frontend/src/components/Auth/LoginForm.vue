<template>
  <div class="login-form-container">
    <h2>Login</h2>
    <form @submit.prevent="handleLogin" class="login-form">
      <div class="form-group">
        <label for="email">Email:</label>
        <input
          type="email"
          id="email"
          v-model="email"
          required
          autocomplete="username"
          aria-label="Email address"
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
          aria-label="Password"
        />
      </div>
      <button type="submit" :disabled="loading" class="btn-primary">
        {{ loading ? 'Logging in...' : 'Login' }}
      </button>
      <p v-if="error" class="error-message" role="alert">{{ error }}</p>
    </form>
    <p class="signup-link">
      Don't have an account? <router-link to="/register">Register here</router-link>
    </p>
  </div>
</template>

<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios'; // Assuming axios is installed for API calls

export default {
  name: 'LoginForm',
  setup() {
    const email = ref('');
    const password = ref('');
    const error = ref(null);
    const loading = ref(false);
    const router = useRouter();

    /**
     * Handles the user login process.
     * Sends a POST request to the backend API with user credentials.
     * On successful login, stores the authentication token and redirects to the tasks page.
     * On failure, displays an error message.
     */
    const handleLogin = async () => {
      error.value = null; // Clear previous errors
      loading.value = true; // Set loading state

      try {
        // Make an API call to the backend login endpoint
        const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/login`, {
          email: email.value,
          password: password.value,
        });

        // Assuming the backend returns a token upon successful login
        const token = response.data.access_token;
        if (token) {
          // Store the token securely (e.g., in localStorage or a more secure cookie)
          // For simplicity, using localStorage here. In a production app, consider HttpOnly cookies.
          localStorage.setItem('access_token', token);
          // Redirect to the tasks page or dashboard after successful login
          router.push('/tasks');
        } else {
          error.value = 'Login failed: No token received.';
        }
      } catch (err) {
        // Handle different types of errors
        if (err.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          if (err.response.status === 401) {
            error.value = 'Invalid email or password.';
          } else if (err.response.data && err.response.data.message) {
            error.value = `Login failed: ${err.response.data.message}`;
          } else {
            error.value = `An unexpected error occurred: ${err.response.status}`;
          }
        } else if (err.request) {
          // The request was made but no response was received
          error.value = 'No response from server. Please check your network connection.';
        } else {
          // Something happened in setting up the request that triggered an Error
          error.value = `Error: ${err.message}`;
        }
        console.error('Login error:', err);
      } finally {
        loading.value = false; // Reset loading state
      }
    };

    return {
      email,
      password,
      error,
      loading,
      handleLogin,
    };
  },
};
</script>

<style scoped>
/* Basic styling for the login form */
.login-form-container {
  max-width: 400px;
  margin: 50px auto;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background-color: #ffffff;
  text-align: center;
}

h2 {
  color: #333;
  margin-bottom: 25px;
  font-size: 2em;
}

.login-form .form-group {
  margin-bottom: 20px;
  text-align: left;
}

.login-form label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #555;
}

.login-form input[type="email"],
.login-form input[type="password"] {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1em;
  box-sizing: border-box; /* Ensures padding doesn't increase width */
}

.login-form input[type="email"]:focus,
.login-form input[type="password"]:focus {
  border-color: #007bff;
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
}

.btn-primary {
  width: 100%;
  padding: 12px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 1.1em;
  cursor: pointer;
  transition: background-color 0.3s ease, transform 0.2s ease;
  margin-top: 10px;
}

.btn-primary:hover {
  background-color: #0056b3;
  transform: translateY(-1px);
}

.btn-primary:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.error-message {
  color: #dc3545;
  margin-top: 15px;
  font-size: 0.95em;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  padding: 10px;
  border-radius: 5px;
}

.signup-link {
  margin-top: 25px;
  font-size: 0.95em;
  color: #666;
}

.signup-link a {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
}

.signup-link a:hover {
  text-decoration: underline;
}
</style>