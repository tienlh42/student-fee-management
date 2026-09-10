<script setup>
// Wrapper chung quanh PrimeVue DataTable cho mọi bảng danh sách trong app:
// - Cột #ID luôn ở đầu, ẩn/hiện được (nút trong thanh phân trang).
// - Header tách màu rõ với row, hover row rõ ràng theo màu brand.
// - Data render theo animation xuất hiện từ từ theo từng dòng (không giật, không quá nhanh).
// Mọi prop/slot của DataTable (value, loading, lazy, paginator, #empty, #header, @page, ...)
// đều truyền xuyên qua bình thường — chỉ dùng <AppDataTable> thay cho <DataTable>.
import { computed, ref, useAttrs, useSlots, watch } from "vue";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";

defineOptions({ inheritAttrs: false });

const props = defineProps({
  // Tắt hẳn tính năng cột ID cho các bảng phụ (vd danh sách con trong dialog)
  // không có cột id ý nghĩa để hiển thị.
  idColumn: { type: Boolean, default: true },
  // Khóa lưu lựa chọn ẩn/hiện cột ID vào localStorage, riêng theo từng bảng
  // (vd "students", "invoices"). Không truyền thì chỉ nhớ trong phiên hiện tại.
  storageKey: { type: String, default: null },
});

const attrs = useAttrs();
const slots = useSlots();

function loadShowId() {
  if (!props.storageKey) return true;
  try {
    const saved = localStorage.getItem(`edufi.table.${props.storageKey}.showId`);
    return saved === null ? true : saved === "1";
  } catch {
    return true;
  }
}

const showId = ref(loadShowId());

watch(showId, (value) => {
  if (!props.storageKey) return;
  try {
    localStorage.setItem(`edufi.table.${props.storageKey}.showId`, value ? "1" : "0");
  } catch {
    // localStorage có thể bị chặn (chế độ riêng tư, cookie bị tắt) — bỏ qua, không lưu được thì thôi.
  }
});

const tableAttrs = computed(() => ({
  rowHover: true,
  stripedRows: true,
  ...attrs,
}));

// Slot của consumer được forward nguyên vẹn, trừ các slot wrapper tự xử lý riêng
// (default: chèn cột ID trước; empty/paginatorstart/loading: có fallback mặc định).
const WRAPPER_OWNED_SLOTS = ["default", "empty", "paginatorstart", "loading"];
const passthroughSlotNames = computed(() =>
  Object.keys(slots).filter((name) => !WRAPPER_OWNED_SLOTS.includes(name)),
);

// Mỗi lần load xong dữ liệu mới, đổi key để toàn bộ bảng remount — animation
// xuất-hiện-từ-từ (xem CSS .app-table-row) chạy lại từ đầu thay vì chỉ chạy
// một lần lúc mount component.
const renderKey = ref(0);
watch(
  () => attrs.loading,
  (loading, wasLoading) => {
    if (wasLoading && !loading) renderKey.value += 1;
  },
);

const MAX_STAGGER_STEPS = 10;

function rowClass() {
  return "app-table-row";
}

function rowStyle(data) {
  const rows = attrs.value ?? [];
  const index = rows.indexOf(data);
  return { "--row-i": Math.max(0, Math.min(index, MAX_STAGGER_STEPS)) };
}
</script>

<template>
  <DataTable :key="renderKey" v-bind="tableAttrs" :row-class="rowClass" :row-style="rowStyle" class="app-table">
    <template v-for="name in passthroughSlotNames" :key="name" #[name]="scope">
      <slot :name="name" v-bind="scope" />
    </template>

    <template #loading>
      <slot name="loading">
        <div class="app-table-progress" role="progressbar" aria-label="Đang tải dữ liệu" />
      </slot>
    </template>

    <template #empty>
      <slot name="empty">
        <div class="flex flex-col items-center gap-2 py-10 text-surface-400 dark:text-surface-500">
          <i class="pi pi-inbox text-3xl" />
          <span class="text-sm">Không có dữ liệu.</span>
        </div>
      </slot>
    </template>

    <template #paginatorstart>
      <slot name="paginatorstart">
        <Button
          v-if="idColumn"
          v-tooltip.top="showId ? 'Ẩn cột #ID' : 'Hiện cột #ID'"
          :icon="showId ? 'pi pi-eye-slash' : 'pi pi-eye'"
          text
          rounded
          size="small"
          class="text-surface-400 hover:text-brand-teal transition-colors duration-150"
          :aria-label="showId ? 'Ẩn cột ID' : 'Hiện cột ID'"
          @click="showId = !showId"
        />
      </slot>
    </template>

    <Column v-if="idColumn && showId" field="id" header="ID" style="width: 4.5rem">
      <template #body="{ data }">
        <span class="font-numeric text-xs text-surface-400 dark:text-surface-500">#{{ data.id }}</span>
      </template>
    </Column>

    <slot />
  </DataTable>
</template>

<style scoped>
/* Tách nền header khỏi row rõ ràng, không cần khai riêng theo light/dark:
   trộn theo currentColor nên tự thích nghi màu chữ sáng/tối của mỗi theme. */
:deep(.p-datatable-thead) {
  background-color: color-mix(in srgb, currentColor 6%, transparent);
}
:deep(.p-datatable-header-cell) {
  border-bottom: 2px solid color-mix(in srgb, currentColor 15%, transparent);
  font-weight: 700;
}

/* Hover rõ ràng theo màu brand, mượt chứ không đổi màu đột ngột. */
:deep(.p-datatable-tbody > tr) {
  transition: background-color 0.15s ease-out;
}
:deep(.p-datatable-tbody > tr:hover) {
  background-color: color-mix(in srgb, var(--edufi-teal) 10%, transparent);
}

/* Animation xuất hiện từ từ theo từng dòng — thời lượng đủ dài, độ trễ tăng
   dần nhưng có trần (MAX_STAGGER_STEPS) để bảng nhiều dòng không "rả" quá lâu. */
:deep(.app-table-row) {
  animation: app-table-row-in 0.5s ease-out both;
  animation-delay: calc(var(--row-i, 0) * 45ms);
}

/* Thanh phân trang dính cố định ở đáy vùng scroll (main), luôn thấy được dù
   cuộn bảng dài cỡ nào — không phải cuộn xuống tận cuối mới đổi trang được. */
:deep(.p-datatable-paginator-bottom) {
  position: sticky;
  bottom: 0;
  z-index: 10;
  border-top: 1px solid color-mix(in srgb, currentColor 15%, transparent);
}

/* Loading: thay khối overlay che cả bảng (mặc định position:fixed phủ kín màn
   hình) bằng một thanh progress bar mỏng dính trên đầu bảng — dữ liệu cũ vẫn
   thấy được, không chặn thao tác trong lúc chờ tải. */
:deep(.p-datatable) {
  position: relative;
}
:deep(.p-datatable-mask) {
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  width: 100%;
  /* PrimeVue tự fade mask qua lại bằng biến này (xem @primeuix/styles base) —
     đặt qua biến thay vì `background` thẳng để hưởng luôn animation fade sẵn có. */
  --px-mask-background: color-mix(in srgb, var(--edufi-teal) 20%, transparent);
  background: var(--px-mask-background);
  pointer-events: none;
  overflow: hidden;
}

.app-table-progress {
  position: relative;
  width: 100%;
  height: 100%;
}
.app-table-progress::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  width: 40%;
  background: var(--edufi-teal);
  animation: app-table-progress-slide 1.1s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  :deep(.app-table-row) {
    animation: none;
  }
  .app-table-progress::after {
    animation: none;
    left: 0;
    width: 100%;
  }
}
</style>

<style>
@keyframes app-table-row-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes app-table-progress-slide {
  0% {
    left: -40%;
  }
  100% {
    left: 100%;
  }
}
</style>
