import { createRouter, createWebHistory } from "vue-router";
import AppLayout from "../layouts/AppLayout.vue";
import HomeView from "../views/HomeView.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      component: AppLayout, // All child routes will be rendered inside AppLayout
      children: [
        {
          path: "",
          name: "home",
          component: HomeView,
        },
        {
          path: "new-project",
          name: "new-project",
          // Lazy-loaded route
          component: () => import("../views/NewProjectView.vue"),
        },
        {
          path: "workflow/:sessionId",
          name: "workflow",
          // Lazy-loaded route
          component: () => import("../views/WorkflowMonitorView.vue"),
          props: true,
        },
      ],
    },
    // You can add other routes outside the layout here (e.g., a login page)
    // { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') }
  ],
});

// Redirect users from incorrect paths to home
router.beforeEach((to, from, next) => {
  // If someone navigates to /workflow-monitor (invalid path), redirect to home
  if (to.path === "/workflow-monitor") {
    console.log("Redirecting from invalid path /workflow-monitor to home");
    next("/");
    return;
  }
  next();
});

export default router;
