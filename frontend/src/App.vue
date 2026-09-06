<script setup>
import { ref } from "vue";
import { useRoute } from "vue-router";

import Toast from "primevue/toast";
import ConfirmDialog from "primevue/confirmdialog";

const route = useRoute();
const sidebarOpen = ref(true);

const nav = [
  { label: "Tổng quan", icon: "pi pi-home", to: "/" },
  { label: "Học sinh", icon: "pi pi-users", to: "/students" },
  { label: "Hóa đơn", icon: "pi pi-file", to: "/invoices" },
  { label: "Đối soát tiền vào", icon: "pi pi-wallet", to: "/transactions" },
  { label: "Thông báo", icon: "pi pi-bell", to: "/notifications" },
];
</script>

<template>
  <div class="min-h-screen flex bg-surface-50 dark:bg-surface-950">
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
      </header>

      <main class="flex-1 p-4 overflow-auto">
        <RouterView />
      </main>
    </div>

    <Toast />
    <ConfirmDialog />
  </div>
</template>
