<script setup>
import { ref, watch } from "vue";

import Dialog from "primevue/dialog";
import Message from "primevue/message";
import Tag from "primevue/tag";

import { errorMessage } from "@/api/client";
import { studentDiscountsApi, studentFeePackagesApi } from "@/api/billing";
import { formatDate } from "@/utils/date";
import { formatMoney } from "@/utils/money";

const props = defineProps({
  visible: { type: Boolean, default: false },
  student: { type: Object, default: null }, // { id, name }
  // Danh sách gói phí đầy đủ (kèm items) đã tải sẵn ở view cha — tránh gọi lại API.
  feePackages: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:visible"]);

const loading = ref(false);
const error = ref("");
const subscriptions = ref([]);
const discounts = ref([]);

function packageFor(feePackageId) {
  return props.feePackages.find((pkg) => pkg.id === feePackageId) ?? null;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [subsPage, discPage] = await Promise.all([
      studentFeePackagesApi.list({ student: props.student.id, page_size: 200 }),
      studentDiscountsApi.list({ student: props.student.id, page_size: 200 }),
    ]);
    subscriptions.value = subsPage.results ?? subsPage;
    discounts.value = discPage.results ?? discPage;
  } catch (err) {
    error.value = errorMessage(err, "Không tải được dữ liệu học sinh.");
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.visible,
  (open) => {
    if (open && props.student) load();
  },
);
</script>

<template>
  <Dialog
    :visible="visible"
    :header="student ? `Chi tiết học phí — ${student.name}` : 'Chi tiết học phí'"
    modal
    :style="{ width: '38rem' }"
    :breakpoints="{ '960px': '95vw' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-5">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <section v-if="!loading" class="flex flex-col gap-2">
        <h3 class="text-sm font-semibold text-surface-600 dark:text-surface-300">
          Gói phí đang đăng ký
        </h3>
        <p v-if="!subscriptions.length" class="text-sm text-surface-500">Chưa đăng ký gói phí nào.</p>
        <div
          v-for="sub in subscriptions"
          :key="sub.id"
          class="flex flex-col gap-1 rounded border border-surface-200 p-3 dark:border-surface-700"
        >
          <div class="flex items-center justify-between">
            <span class="font-medium">{{ sub.fee_package_name }}</span>
            <span class="text-sm text-surface-500">
              {{ formatDate(sub.effective_from) }} –
              {{ sub.effective_until ? formatDate(sub.effective_until) : "nay" }}
            </span>
          </div>
          <ul v-if="packageFor(sub.fee_package)" class="flex flex-col gap-0.5 pl-4 text-sm list-disc">
            <li v-for="item in packageFor(sub.fee_package).items" :key="item.id" class="flex justify-between gap-4">
              <span>{{ item.fee_item_name }}</span>
              <span>{{ formatMoney(item.effective_amount) }}</span>
            </li>
          </ul>
        </div>
      </section>

      <section v-if="!loading" class="flex flex-col gap-2">
        <h3 class="text-sm font-semibold text-surface-600 dark:text-surface-300">Giảm trừ</h3>
        <p v-if="!discounts.length" class="text-sm text-surface-500">Chưa có giảm trừ nào.</p>
        <div
          v-for="discount in discounts"
          :key="discount.id"
          class="flex items-center justify-between gap-4 rounded border border-surface-200 p-3 dark:border-surface-700"
        >
          <div class="flex flex-col">
            <span class="font-medium">{{ discount.name }}</span>
            <span class="text-sm text-surface-500">
              {{ discount.fee_item_name || "Toàn bộ hóa đơn" }} ·
              {{
                discount.discount_type === "percentage"
                  ? `${discount.value}%`
                  : formatMoney(discount.value)
              }}
            </span>
          </div>
          <Tag
            :value="discount.is_active ? 'Đang áp dụng' : 'Ngừng áp dụng'"
            :severity="discount.is_active ? 'success' : 'secondary'"
          />
        </div>
      </section>

      <div v-if="loading" class="py-6 text-center text-sm text-surface-500">Đang tải…</div>
    </div>
  </Dialog>
</template>
