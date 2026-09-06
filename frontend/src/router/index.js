import { createRouter, createWebHistory } from "vue-router";

// Django trả index.html cho mọi route non-API, nên history mode chạy được
// mà không cần cấu hình rewrite riêng.
const routes = [
  {
    path: "/",
    name: "dashboard",
    meta: { title: "Tổng quan" },
    component: () => import("../views/DashboardView.vue"),
  },
  {
    path: "/students",
    name: "students",
    meta: { title: "Học sinh" },
    component: () => import("../views/PlaceholderView.vue"),
  },
  {
    path: "/invoices",
    name: "invoices",
    meta: { title: "Hóa đơn" },
    component: () => import("../views/PlaceholderView.vue"),
  },
  {
    path: "/transactions",
    name: "transactions",
    meta: { title: "Đối soát tiền vào" },
    component: () => import("../views/PlaceholderView.vue"),
  },
  {
    path: "/notifications",
    name: "notifications",
    meta: { title: "Thông báo" },
    component: () => import("../views/PlaceholderView.vue"),
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    meta: { title: "Không tìm thấy" },
    component: () => import("../views/NotFoundView.vue"),
  },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
