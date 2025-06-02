<template>
  <div class="home-container">
    <h1>Welcome to Task Tracker!</h1>
    <p class="tagline">Your simple solution for managing daily tasks.</p>

    <!-- Conditional rendering based on authentication status -->
    <div v-if="isLoggedIn" class="auth-actions">
      <p>You are currently logged in.</p>
      <button @click="goToTasks" class="btn primary-btn">Go to My Tasks</button>
      <button @click="logout" class="btn secondary-btn">Logout</button>
    </div>

    <div v-else class="guest-actions">
      <p>Manage your tasks efficiently. Get started now!</p>
      <button @click="goToLogin" class="btn primary-btn">Login</button>
      <button @click="goToRegister" class="btn secondary-btn">Register</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const isLoggedIn = ref(false); // Reactive variable to track authentication status

/**
 * Checks if the user is authenticated by looking for an 'authToken' in localStorage.
 * Updates the `isLoggedIn` reactive variable accordingly.
 * If authenticated, it immediately redirects the user to the '/tasks' page
 * to provide a seamless experience, assuming they want to manage tasks.
 */
const checkAuthStatus = () => {
  const token = localStorage.getItem('authToken');
  isLoggedIn.value = !!token; // Set to true if token exists and is not empty, false otherwise

  // If already logged in, redirect to tasks page immediately for better UX
  if (isLoggedIn.value) {
    router.push('/tasks');
  }
};

/**
 * Navigates the user to the login page.
 */
const goToLogin = () => {
  router.push('/login');
};

/**
 * Navigates the user to the registration page.
 */
const goToRegister = () => {
  router.push('/register');
};

/**
 * Navigates the user to their tasks page. This button is only visible
 * when the user is authenticated.
 */
const goToTasks = () => {
  router.push('/tasks');
};

/**
 * Logs out the user by removing the authentication token from localStorage.
 * After removing the token, it updates the `isLoggedIn` state and redirects
 * the user to the login page.
 */
const logout = () => {
  localStorage.removeItem('authToken'); // Remove the authentication token
  isLoggedIn.value = false; // Update the reactive state to reflect logout
  router.push('/login'); // Redirect to the login page
  // Optionally, provide user feedback (e.g., a toast notification)
  alert('You have been successfully logged out.');
};

// On component mount, check the authentication status to determine
// what content to display and whether to redirect.
onMounted(() => {
  checkAuthStatus();
});
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh; /* Occupy most of the viewport height */
  text-align: center;
  padding: 20px;
  background-color: #f8f9fa; /* Light background */
  border-radius: 10px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
  max-width: 700px;
  margin: 50px auto; /* Center the container */
  font-family: 'Arial', sans-serif;
}

h1 {
  color: #2c3e50; /* Darker text for heading */
  margin-bottom: 20px;
  font-size: 2.8em;
  font-weight: bold;
}

.tagline {
  color: #34495e; /* Slightly lighter text for tagline */
  font-size: 1.4em;
  margin-bottom: 40px;
  max-width: 500px;
  line-height: 1.5;
}

p {
  color: #555;
  font-size: 1.1em;
  margin-bottom: 25px;
}

.auth-actions, .guest-actions {
  display: flex;
  flex-direction: column;
  gap: 18px; /* Space between buttons */
  width: 100%;
  max-width: 320px; /* Max width for button group */
}

.btn {
  padding: 14px 30px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.2em;
  font-weight: 600;
  transition: background-color 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease;
  width: 100%;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.primary-btn {
  background-color: #4CAF50; /* Vibrant green */
  color: white;
}

.primary-btn:hover {
  background-color: #45a049;
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}

.secondary-btn {
  background-color: #007bff; /* Bright blue */
  color: white;
}

.secondary-btn:hover {
  background-color: #0056b3;
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}

/* Responsive adjustments for smaller screens */
@media (max-width: 768px) {
  .home-container {
    margin: 30px auto;
    padding: 15px;
  }

  h1 {
    font-size: 2.2em;
  }

  .tagline {
    font-size: 1.1em;
    margin-bottom: 30px;
  }

  .btn {
    padding: 12px 25px;
    font-size: 1.1em;
  }
}

@media (max-width: 480px) {
  h1 {
    font-size: 1.8em;
  }

  .tagline {
    font-size: 1em;
    margin-bottom: 25px;
  }

  .btn {
    padding: 10px 20px;
    font-size: 1em;
  }

  .auth-actions, .guest-actions {
    max-width: 280px;
  }
}
</style>