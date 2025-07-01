import { createRouter, createWebHistory } from "vue-router";
import AppLayout from "@/components/AppLayout.vue";
import NewProjectView from "../views/NewProjectView.vue";
import WorkflowMonitorView from "../views/WorkflowMonitorView.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "",
          name: "new-project",
          component: NewProjectView,
        },
        {
          path: "/workflow",
          name: "workflow-monitor",
          component: WorkflowMonitorView,
        },
      ],
    },
  ],
});

export default router;
