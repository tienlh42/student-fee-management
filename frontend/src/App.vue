<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Avatar from "primevue/avatar";
import Button from "primevue/button";
import ConfirmDialog from "primevue/confirmdialog";
import Menu from "primevue/menu";
import Tag from "primevue/tag";
import Toast from "primevue/toast";

import BrandLogo from "@/components/BrandLogo.vue";
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
      label: "Thanh toán",
      icon: "pi pi-money-bill",
      to: "/payments",
      visible: auth.role.can_see_bank_data,
    },
    {
      label: "Đối soát tiền vào",
      icon: "pi pi-wallet",
      to: "/transactions",
      visible: auth.role.can_see_bank_data,
    },
    {
      label: "Hoàn tiền",
      icon: "pi pi-replay",
      to: "/refunds",
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
  {
    label: "Hồ sơ cá nhân",
    icon: "pi pi-user-edit",
    command: () => router.push("/profile"),
  },
  {
    label: "Quản trị Django",
    icon: "pi pi-external-link",
    visible: auth.role.is_staff_admin,
    command: () => window.open("/admin/", "_blank", "noopener"),
  },
  { separator: true },
  { label: "Đăng xuất", icon: "pi pi-sign-out", command: signOut },
]);

async function signOut() {
  await auth.logout();
  await router.replace({ path: "/login" });
}
</script>

<template>
  <Transition name="page" mode="out-in">
    <RouterView v-if="bare" :key="route.fullPath" />
  </Transition>

  <div v-if="!bare" class="min-h-screen flex bg-surface-50 dark:bg-surface-950">
    <aside
      class="shrink-0 overflow-hidden border-r border-surface-200/70 dark:border-surface-800 bg-white dark:bg-surface-900 transition-[width] duration-300 ease-in-out"
      :class="sidebarOpen ? 'w-60' : 'w-0'"
    >
      <div class="w-60 h-full flex flex-col">
        <div class="px-4 py-4 flex items-center gap-2">
          <BrandLogo
            variant="red"
            class="w-9 h-9 shrink-0 transition-transform duration-300 ease-out hover:scale-110"
          />
          <div class="leading-tight">
            <div class="font-display font-bold text-lg">EduFi</div>
            <div class="text-xs text-surface-500 dark:text-surface-400">Quản lý học phí</div>
          </div>
        </div>
        <nav class="px-2 space-y-1">
          <RouterLink
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            class="group relative flex items-center gap-2 pl-3 pr-3 py-2 rounded-md text-sm border-l-4 transition-colors duration-200 ease-out"
            :class="
              route.path === item.to
                ? 'border-brand-teal bg-brand-teal/10 text-brand-teal font-medium'
                : 'border-transparent text-surface-600 dark:text-surface-300 hover:border-brand-teal/40 hover:bg-surface-100 dark:hover:bg-surface-800'
            "
          >
            <i
              :class="[
                item.icon,
                'transition-colors duration-200 ease-out group-hover:text-brand-teal',
                route.path === item.to ? 'text-brand-teal' : 'text-surface-400 dark:text-surface-500',
              ]"
            />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
      </div>
    </aside>

    <div class="flex-1 min-w-0 flex flex-col">
      <header
        class="h-14 flex items-center gap-3 px-4 border-b border-surface-200/70 dark:border-surface-800 bg-white dark:bg-surface-900"
      >
        <button
          class="p-2 rounded-full hover:bg-brand-teal/10 hover:text-brand-teal transition-colors duration-200 ease-out"
          type="button"
          :aria-label="sidebarOpen ? 'Ẩn menu' : 'Hiện menu'"
          @click="sidebarOpen = !sidebarOpen"
        >
          <i
            class="pi pi-angle-double-left transition-transform duration-300 ease-in-out"
            :class="{ 'rotate-180': !sidebarOpen }"
          />
        </button>
        <Transition name="fade" mode="out-in">
          <h1 :key="route.path" class="text-sm text-surface-600 dark:text-surface-300">
            {{ route.meta.title ?? "" }}
          </h1>
        </Transition>

        <div class="ml-auto flex items-center gap-2">
          <Tag :value="roleLabel" severity="secondary" />
          <Button
            text
            rounded
            class="transition-colors duration-200 ease-out"
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
        <Transition name="page" mode="out-in">
          <RouterView :key="route.fullPath" />
        </Transition>
      </main>
    </div>
  </div>

  <Toast />
  <ConfirmDialog />
</template>
