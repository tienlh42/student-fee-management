<script setup>
import { onMounted, ref } from "vue";

import Card from "primevue/card";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import { errorMessage } from "@/api/client";
import { studentsApi } from "@/api/people";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

// Chỉ cần `count` của mỗi bộ lọc, không cần dữ liệu dòng -> page_size=1.
const CARDS = [
  { key: "total", label: "Tổng học sinh", filter: {} },
  { key: "active", label: "Đang học", filter: { status: "active" } },
  { key: "paused", label: "Tạm nghỉ", filter: { status: "paused" } },
];

const counts = ref({});
const loading = ref(true);
const error = ref("");

onMounted(async () => {
  try {
    const pages = await Promise.all(
      CARDS.map((card) => studentsApi.list({ ...card.filter, page_size: 1 })),
    );
    counts.value = Object.fromEntries(
      CARDS.map((card, index) => [card.key, pages[index].count]),
    );
  } catch (err) {
    error.value = errorMessage(err, "Không tải được số liệu.");
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="space-y-4">
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card v-for="card in CARDS" :key="card.key">
        <template #title>
          <span class="text-sm font-medium text-surface-500">{{ card.label }}</span>
        </template>
        <template #content>
          <Skeleton v-if="loading" width="4rem" height="2rem" />
          <div v-else class="text-3xl font-semibold">{{ counts[card.key] ?? 0 }}</div>
        </template>
      </Card>
    </div>

    <Message severity="info" :closable="false">
      Màn hình <strong>Học sinh</strong> và <strong>Hóa đơn</strong> đã dùng được. Đối soát
      tiền vào và Thông báo vẫn là placeholder — API của <code>payments</code>,
      <code>notifications</code> chưa viết.
    </Message>

    <p v-if="!auth.canEdit" class="text-sm text-surface-500">
      Bạn đang đăng nhập với quyền chỉ đọc, nên các nút thêm/sửa/xóa được ẩn đi.
    </p>
  </div>
</template>
