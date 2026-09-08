<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import Tag from "primevue/tag";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage } from "@/api/client";
import { invoicesApi } from "@/api/billing";
import { formatDateTime } from "@/utils/date";
import { formatMoney } from "@/utils/money";

const props = defineProps({
  visible: { type: Boolean, default: false },
  invoice: { type: Object, default: null },
  canRecord: { type: Boolean, default: false },
  // "full" = thanh toán ngay (trả đủ số còn nợ), "installment" = chia thành nhiều đợt.
  mode: { type: String, default: "installment" },
  methodOptions: { type: Array, required: true }, // [{value, label}]
});
const emit = defineEmits(["update:visible", "recorded"]);

const isFullMode = computed(() => props.mode === "full");
const formTitle = computed(() =>
  isFullMode.value ? "Thanh toán ngay (đủ số còn nợ)" : "Ghi nhận một đợt thanh toán",
);
const submitLabel = computed(() => (isFullMode.value ? "Thanh toán ngay" : "Ghi nhận đợt này"));

const payments = ref([]);
const loading = ref(false);
const listError = ref("");

const form = reactive({ amount: null, method: "cash", note: "" });
const saving = ref(false);
const formError = ref("");

async function load() {
  loading.value = true;
  listError.value = "";
  try {
    payments.value = await invoicesApi.payments(props.invoice.id);
  } catch (err) {
    listError.value = errorMessage(err, "Không tải được lịch sử thanh toán.");
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.visible,
  (open) => {
    if (!open || !props.invoice) return;
    formError.value = "";
    form.amount = isFullMode.value ? Number(props.invoice.outstanding_amount) || null : null;
    form.method = "cash";
    form.note = "";
    load();
  },
);

async function submit() {
  formError.value = "";
  saving.value = true;
  try {
    await invoicesApi.recordPayment(props.invoice.id, {
      amount: form.amount,
      method: form.method,
      note: form.note,
    });
    form.amount = null;
    form.note = "";
    await load();
    emit("recorded");
    if (isFullMode.value) emit("update:visible", false);
  } catch (err) {
    formError.value = errorMessage(err, "Không ghi nhận được thanh toán.");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="invoice ? `Lịch sử thanh toán — ${invoice.qr_reference_code}` : 'Lịch sử thanh toán'"
    :loading="loading"
    :style="{ width: '40rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-4">
      <Message v-if="listError" severity="error" :closable="false">{{ listError }}</Message>

      <DataTable :value="payments" size="small" striped-rows data-key="id">
        <template #empty>
          <div class="py-4 text-center text-surface-500 text-sm">Chưa có thanh toán nào.</div>
        </template>
        <Column field="created_at" header="Thời gian" style="width: 10rem">
          <template #body="{ data }">{{ formatDateTime(data.created_at) }}</template>
        </Column>
        <Column header="Số tiền" style="width: 8rem">
          <template #body="{ data }">{{ formatMoney(data.amount_applied) }}</template>
        </Column>
        <Column field="payment_method_display" header="Hình thức" style="width: 8rem" />
        <Column header="Cách khớp" style="width: 8rem">
          <template #body="{ data }">
            <Tag
              :value="data.matched_by_display"
              :severity="data.matched_by === 'auto' ? 'info' : 'secondary'"
            />
          </template>
        </Column>
        <Column field="recorded_by_username" header="Người thu" />
        <Column field="note" header="Ghi chú" />
      </DataTable>

      <section
        v-if="canRecord"
        class="flex flex-col gap-3 pt-3 border-t border-surface-200 dark:border-surface-700"
      >
        <span class="text-sm font-medium">{{ formTitle }}</span>
        <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>

        <div class="flex flex-wrap items-end gap-3">
          <div class="flex flex-col gap-1">
            <label for="pay-amount" class="text-sm">Số tiền *</label>
            <InputNumber
              id="pay-amount"
              v-model="form.amount"
              mode="decimal"
              :min="0"
              :max-fraction-digits="0"
              suffix=" đ"
              :disabled="isFullMode"
              class="w-44"
            />
          </div>
          <div class="flex flex-col gap-1">
            <label for="pay-method" class="text-sm">Hình thức</label>
            <Select
              id="pay-method"
              v-model="form.method"
              :options="methodOptions"
              option-label="label"
              option-value="value"
              class="w-40"
            />
          </div>
          <div class="flex flex-col gap-1 flex-1 min-w-40">
            <label for="pay-note" class="text-sm">Ghi chú</label>
            <InputText id="pay-note" v-model="form.note" />
          </div>
          <Button
            :label="submitLabel"
            icon="pi pi-check"
            :loading="saving"
            :disabled="!form.amount"
            @click="submit"
          />
        </div>
      </section>
    </div>
  </AppDialog>
</template>
