<script setup>
import { computed, onMounted, ref, watch } from "vue";

import Card from "primevue/card";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";

import { usersApi } from "@/api/accounts";
import { guardiansApi, studentsApi, teachersApi } from "@/api/people";
import { useAuthStore } from "@/stores/auth";
import { useHouseScopeStore } from "@/stores/houseScope";

const auth = useAuthStore();
const houseScope = useHouseScopeStore();

// Học sinh/phụ huynh: ai cũng quan tâm (teacher lẫn quản trị). Giáo viên/tài
// khoản là số liệu nâng cao, chỉ quản trị mới cần — tài khoản còn nhạy cảm
// hơn nữa nên chỉ hiện với superuser (khớp CanManageUsers ở backend, gọi
// bằng vai trò thấp hơn sẽ bị 403).
const sections = computed(() => {
  const list = [
    {
      title: "Học sinh",
      cards: [
        { key: "students_total", label: "Tổng học sinh", api: studentsApi, filter: {} },
        {
          key: "students_active",
          label: "Đang học",
          api: studentsApi,
          filter: { status: "active" },
        },
        {
          key: "students_paused",
          label: "Tạm nghỉ",
          api: studentsApi,
          filter: { status: "paused" },
        },
      ],
    },
  ];

  if (auth.canEdit) {
    list.push({
      title: "Phụ huynh",
      cards: [{ key: "guardians_total", label: "Tổng phụ huynh", api: guardiansApi, filter: {} }],
    });
  }

  if (auth.role.is_staff_admin) {
    list.push({
      title: "Giáo viên",
      cards: [{ key: "teachers_total", label: "Tổng giáo viên", api: teachersApi, filter: {} }],
    });
  }

  if (auth.role.is_superuser) {
    list.push({
      title: "Tài khoản",
      cards: [{ key: "users_total", label: "Tổng tài khoản", api: usersApi, filter: {} }],
    });
  }

  return list;
});

const allCards = computed(() => sections.value.flatMap((section) => section.cards));

const counts = ref({});
const loading = ref(true);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const cards = allCards.value;
    const results = await Promise.allSettled(
      cards.map((card) =>
        card.api.list({ ...card.filter, house: houseScope.houseId, page_size: 1 }),
      ),
    );
    const next = {};
    let hadError = false;
    results.forEach((result, index) => {
      if (result.status === "fulfilled") {
        next[cards[index].key] = result.value.count;
      } else {
        hadError = true;
      }
    });
    counts.value = next;
    if (hadError) error.value = "Một số số liệu không tải được.";
  } finally {
    loading.value = false;
  }
}

watch(() => houseScope.houseId, load);
onMounted(load);
</script>

<template>
  <div class="space-y-6">
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div v-for="section in sections" :key="section.title" class="space-y-2">
      <h2 class="text-sm font-medium text-surface-500">{{ section.title }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card v-for="card in section.cards" :key="card.key">
          <template #title>
            <span class="text-sm font-medium text-surface-500">{{ card.label }}</span>
          </template>
          <template #content>
            <Skeleton v-if="loading" width="4rem" height="2rem" />
            <div v-else class="text-3xl font-semibold">{{ counts[card.key] ?? 0 }}</div>
          </template>
        </Card>
      </div>
    </div>

    <Message severity="info" :closable="false">
      Màn hình <strong>Học sinh</strong>, <strong>Hóa đơn</strong>, <strong>Thanh toán</strong> và
      <strong>Đối soát tiền vào</strong> đã dùng được. <strong>Thông báo</strong> vẫn là
      placeholder — API của <code>notifications</code> chưa viết.
    </Message>

    <p v-if="!auth.canEdit" class="text-sm text-surface-500">
      Bạn đang đăng nhập với quyền chỉ đọc, nên các nút thêm/sửa/xóa được ẩn đi.
    </p>
  </div>
</template>
