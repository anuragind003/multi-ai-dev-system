import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import LoginView from '../views/LoginView.vue';
import RegisterView from '../views/RegisterView.vue';
import TasksView from '../views/TasksView.vue';
import NotFoundView from '../views/NotFoundView.vue';

/**
 * Defines constants for route names to prevent typos and improve maintainability.
 */
const ROUTE_NAMES = {
  HOME: 'home',
  LOGIN: 'login',
  REGISTER: 'register',
  TASKS: 'tasks',
  NOT_FOUND: 'NotFound',
};

/**
 * Defines the routes for the application.
 * Each route object specifies a path, a unique name, the component to render,
 * and optional metadata (`meta`) for navigation guards.
 */
const routes = [
  {
    path: '/',
    name: ROUTE_NAMES.HOME,
    component: HomeView,
    meta: { requiresAuth: false } // The home page does not require authentication.
  },
  {
    path: '/login',
    name: ROUTE_NAMES.LOGIN,
    component: LoginView,
    meta: { requiresAuth: false, redirectIfAuthenticated: true } // Login page does not require auth, but redirects if user is already logged in.
  },
  {
    path: '/register',
    name: ROUTE_NAMES.REGISTER,
    component: RegisterView,
    meta: { requiresAuth: false, redirectIfAuthenticated: true } // Register page does not require auth, but redirects if user is already logged in.
  },
  {
    path: '/tasks',
    name: ROUTE_NAMES.TASKS,
    component: TasksView,
    meta: { requiresAuth: true } // The tasks management page requires authentication.
  },
  // Catch-all route for any undefined paths (404 Not Found).
  // The `/:pathMatch(.*)*` syntax ensures it matches all paths.
  {
    path: '/:pathMatch(.*)*',
    name: ROUTE_NAMES.NOT_FOUND,
    component: NotFoundView,
    meta: { requiresAuth: false } // The 404 page does not require authentication.
  }
];

/**
 * Creates and configures the Vue Router instance.
 * - `history`: Uses `createWebHistory` for clean URLs (e.g., `yourdomain.com/tasks` instead of `yourdomain.com/#/tasks`).
 *   `process.env.BASE_URL` is used to handle potential base paths when deploying the application.
 * - `routes`: The array of defined route objects.
 */
const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
});

/**
 * Global Navigation Guard: `router.beforeEach`
 * This function is called before every route navigation. It's used to implement
 * authentication checks and redirection logic.
 *
 * @param {object} to - The target Route object being navigated to.
 * @param {object} from - The current Route object being navigated away from.
 * @param {function} next - A function that must be called to resolve the hook.
 *   - `next()`: Proceeds to the `to` route.
 *   - `next(false)`: Aborts the current navigation.
 *   - `next('/')` or `next({ name: 'login' })`: Redirects to a different route.
 */
router.beforeEach((to, from, next) => {
  // Determine if the target route requires authentication based on its meta field.
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  // Determine if the target route should redirect if the user is already authenticated.
  const redirectIfAuthenticated = to.matched.some(record => record.meta.redirectIfAuthenticated);

  // Check if the user is authenticated by looking for an 'authToken' in localStorage.
  // In a real-world application, this token would typically be a JWT and might be
  // validated for expiry or integrity on the client-side or by the backend on API calls.
  const isAuthenticated = localStorage.getItem('authToken') !== null;

  if (requiresAuth && !isAuthenticated) {
    // If the route requires authentication AND the user is NOT authenticated,
    // redirect them to the login page.
    console.log(`Navigation Guard: Access to '${to.name}' denied. Redirecting to login.`);
    next({ name: ROUTE_NAMES.LOGIN });
  } else if (redirectIfAuthenticated && isAuthenticated) {
    // If the route is meant for unauthenticated users (e.g., login, register)
    // AND the user IS authenticated, redirect them to the tasks page.
    console.log(`Navigation Guard: User already logged in. Redirecting from '${to.name}' to tasks.`);
    next({ name: ROUTE_NAMES.TASKS });
  } else {
    // In all other cases (e.g., public routes, authenticated user accessing authenticated routes),
    // allow the navigation to proceed as normal.
    next();
  }
});

export default router;