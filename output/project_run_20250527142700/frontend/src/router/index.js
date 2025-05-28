import { createRouter, createWebHistory } from 'vue-router';

// Import components that will be rendered for each route
// These components are assumed to exist in the `frontend/src/views` directory.
// For an MVP, these views will primarily contain buttons/links to trigger API calls for file downloads.
import HomeView from '../views/HomeView.vue';
import MoengageExportView from '../views/MoengageExportView.vue';
import DuplicateExportView from '../views/DuplicateExportView.vue';
import UniqueExportView from '../views/UniqueExportView.vue';
import ErrorExportView from '../views/ErrorExportView.vue';

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { title: 'CDP Dashboard' }
  },
  {
    path: '/exports/moengage',
    name: 'moengage-export',
    component: MoengageExportView,
    meta: { title: 'Moengage Campaign File Export' }
  },
  {
    path: '/exports/duplicates',
    name: 'duplicate-export',
    component: DuplicateExportView,
    meta: { title: 'Duplicate Customer Data Export' }
  },
  {
    path: '/exports/unique',
    name: 'unique-export',
    component: UniqueExportView,
    meta: { title: 'Unique Customer Data Export' }
  },
  {
    path: '/exports/errors',
    name: 'error-export',
    component: ErrorExportView,
    meta: { title: 'Data Error File Export' }
  },
  // Add a catch-all route for 404 Not Found, if desired
  // {
  //   path: '/:catchAll(.*)',
  //   name: 'NotFound',
  //   component: NotFoundView // Assuming you have a NotFoundView component
  // }
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

// Optional: Global navigation guard to update document title
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} | LTFS CDP` : 'LTFS CDP';
  next();
});

export default router;