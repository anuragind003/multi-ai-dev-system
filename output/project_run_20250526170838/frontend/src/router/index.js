import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue')
  },
  {
    path: '/admin/upload',
    name: 'admin-upload',
    component: () => import('../views/AdminUpload.vue')
  },
  {
    path: '/downloads/moengage',
    name: 'moengage-export',
    component: () => import('../views/MoengageExport.vue')
  },
  {
    path: '/downloads/duplicates',
    name: 'duplicate-data',
    component: () => import('../views/DuplicateData.vue')
  },
  {
    path: '/downloads/unique',
    name: 'unique-data',
    component: () => import('../views/UniqueData.vue')
  },
  {
    path: '/downloads/errors',
    name: 'error-data',
    component: () => import('../views/ErrorData.vue')
  },
  {
    path: '/reports/daily',
    name: 'daily-reports',
    component: () => import('../views/DailyReports.vue')
  },
  {
    path: '/customers',
    name: 'customer-list',
    component: () => import('../views/CustomerList.vue')
  },
  {
    path: '/customers/:id',
    name: 'customer-detail',
    component: () => import('../views/CustomerDetail.vue'),
    props: true
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

export default router;