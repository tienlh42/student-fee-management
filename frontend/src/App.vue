<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Avatar from "primevue/avatar";
import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import Menu from "primevue/menu";
import Tag from "primevue/tag";
import Toast from "primevue/toast";

import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const sidebarOpen = ref(true);
const userMenu = ref();

// Route /login tự dựng layout riêng — không bọc sidebar/header quanh nó.
const bare = computed(() => route.meta.blank === true || !auth.isAuthenticated);

const nav = computed(() =>
  [
    { label: "Tổng quan", icon: "pi pi-home", to: "/" },
    { label: "Học sinh", icon: "pi pi-users", to: "/students" },
    { label: "Hóa đơn", icon: "pi pi-file", to: "/invoices" },
    {
      label: "Đối soát tiền vào",
      icon: "pi pi-wallet",
      to: "/transactions",
      visible: auth.role.can_see_bank_data,
    },
    { label: "Thông báo", icon: "pi pi-bell", to: "/notifications" },
  ].filter((item) => item.visible !== false),
);

const roleLabel = computed(() => {
  if (auth.role.is_staff_admin) return "Quản trị";
  if (auth.role.is_teacher) return "Giáo viên";
  if (auth.role.is_guardian) return "Phụ huynh";
  return "Chưa gán vai trò";
});

const initials = computed(() =>
  auth.displayName
    .split(" ")
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join(""),
);

const userMenuItems = computed(() => [
  { label: auth.user?.username ?? "", disabled: true },
  { separator: true },
  { label: "Đăng xuất", icon: "pi pi-sign-out", command: signOut },
]);

async function signOut() {
  await auth.logout();
  await router.replace({ path: "/login" });
}
</script>

<template>
  <RouterView v-if="bare" />

  <div v-else class="min-h-screen flex bg-surface-50 dark:bg-surface-950">
    <aside
      v-show="sidebarOpen"
      class="w-60 shrink-0 border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900"
    >
      <div class="px-4 py-4 font-semibold text-lg">Quản lý học phí</div>
      <nav class="px-2 space-y-1">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-surface-100 dark:hover:bg-surface-800"
          :class="route.path === item.to ? 'bg-surface-100 dark:bg-surface-800 font-medium' : ''"
        >
          <i :class="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>

    <div class="flex-1 min-w-0 flex flex-col">
      <header
        class="h-14 flex items-center gap-3 px-4 border-b border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900"
      >
        <button
          class="p-2 rounded hover:bg-surface-100 dark:hover:bg-surface-800"
          type="button"
          aria-label="Ẩn/hiện menu"
          @click="sidebarOpen = !sidebarOpen"
        >
          <i class="pi pi-bars" />
        </button>
        <h1 class="text-sm text-surface-600 dark:text-surface-300">
          {{ route.meta.title ?? "" }}
        </h1>

        <div class="ml-auto flex items-center gap-2">
          <Tag :value="roleLabel" severity="secondary" />
          <Button
            text
            rounded
            aria-haspopup="true"
            aria-controls="user-menu"
            :aria-label="`Tài khoản ${auth.displayName}`"
            @click="userMenu.toggle($event)"
          >
            <Avatar :label="initials" shape="circle" size="normal" />
            <span class="ml-2 text-sm hidden sm:inline">{{ auth.displayName }}</span>
          </Button>
          <Menu id="user-menu" ref="userMenu" :model="userMenuItems" :popup="true" />
        </div>
      </header>

      <main class="flex-1 p-4 overflow-auto">
        <RouterView />
      </main>
    </div>
  </div>

  <Toast />
  <ConfirmDialog />
</template>
