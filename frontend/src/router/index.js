import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "@/stores/auth";

// Django trả index.html cho mọi route non-API, nên history mode chạy được
// mà không cần cấu hình rewrite riêng.
//
// `meta.public`: route xem được khi chưa đăng nhập (chỉ /login).
// `meta.requiresEdit`: route chỉ dành cho teacher — guardian bị đẩy về /.
const routes = [
  {
    path: "/login",
    name: "login",
    meta: { title: "Đăng nhập", public: true, blank: true },
    component: () => import("../views/LoginView.vue"),
  },
  {
    path: "/",
    name: "dashboard",
    meta: { title: "Tổng quan" },
    component: () => import("../views/DashboardView.vue"),
  },
  {
    path: "/profile",
    name: "profile",
    // Không có route /profile/:id — hồ sơ luôn là của chính người đang đăng nhập.
    meta: { title: "Hồ sơ cá nhân" },
    component: () => import("../views/ProfileView.vue"),
  },
  {
    path: "/students",
    name: "students",
    meta: { title: "Học sinh" },
    component: () => import("../views/StudentsView.vue"),
  },
  {
    path: "/invoices",
    name: "invoices",
    meta: { title: "Hóa đơn" },
    component: () => import("../views/InvoicesView.vue"),
  },
  {
    path: "/payments",
    name: "payments",
    // Guardian không bao giờ được thấy dữ liệu ngân hàng (xem README § Phân quyền).
    meta: { title: "Thanh toán", requiresBankData: true },
    component: () => import("../views/PaymentsView.vue"),
  },
  {
    path: "/transactions",
    name: "transactions",
    // Guardian không bao giờ được thấy dữ liệu ngân hàng (xem README § Phân quyền).
    meta: { title: "Đối soát tiền vào", requiresBankData: true },
    component: () => import("../views/TransactionsView.vue"),
  },
  {
    path: "/refunds",
    name: "refunds",
    // Guardian không bao giờ được thấy dữ liệu ngân hàng (xem README § Phân quyền).
    meta: { title: "Hoàn tiền", requiresBankData: true },
    component: () => import("../views/RefundsView.vue"),
  },
  {
    path: "/notifications",
    name: "notifications",
    meta: { title: "Thông báo" },
    component: () => import("../views/PlaceholderView.vue"),
  },
  {
    path: "/admin",
    name: "admin",
    // Chỉ superuser — CRUD Cơ sở & Tài khoản (xem accounts.permissions.CanManageUsers/CanManageHouses).
    meta: { title: "Quản trị", requiresSuperuser: true },
    component: () => import("../views/AdminView.vue"),
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    meta: { title: "Không tìm thấy" },
    component: () => import("../views/NotFoundView.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  // Guard chỉ là trải nghiệm người dùng — quyền thật do backend quyết định.
  // Vẫn phải chờ /me để tránh chớp màn hình login khi F5 lúc đang đăng nhập.
  await auth.ensureResolved();

  if (to.meta.public) {
    return auth.isAuthenticated ? { path: "/" } : true;
  }

  if (!auth.isAuthenticated) {
    return { path: "/login", query: to.fullPath === "/" ? {} : { redirect: to.fullPath } };
  }

  if (to.meta.requiresBankData && !auth.role.can_see_bank_data) {
    return { path: "/" };
  }

  if (to.meta.requiresSuperuser && !auth.role.is_superuser) {
    return { path: "/" };
  }

  return true;
});

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · Quản lý học phí` : "Quản lý học phí";
});

export default router;
