<script setup>
import { reactive, ref, watch } from "vue";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage } from "@/api/client";
import { invoicesApi } from "@/api/billing";
import { formatDate, formatDateTime } from "@/utils/date";
import { formatMoney } from "@/utils/money";

const confirm = useConfirm();
const toast = useToast();

const props = defineProps({
  visible: { type: Boolean, default: false },
  invoice: { type: Object, default: null },
  // false khi hóa đơn đã thanh toán đủ / đã hoàn đủ / người dùng không có quyền —
  // chỉ còn xem chi tiết hóa đơn + lịch sử, không ghi nhận thêm được.
  canRecord: { type: Boolean, default: false },
  methodOptions: { type: Array, required: true }, // [{value, label}]
});
const emit = defineEmits(["update:visible", "recorded"]);

const MODE_OPTIONS = [
  { label: "Thanh toán ngay (đủ số còn nợ)", value: "full" },
  { label: "Chia thành nhiều đợt", value: "installment" },
];

const payments = ref([]);
const loading = ref(false);
const listError = ref("");

// Bản chụp hóa đơn dùng để tính "còn nợ" trong dialog — cập nhật lại từ
// response sau mỗi lần ghi nhận, để ghi nhiều đợt liên tiếp trong cùng lần mở
// dialog vẫn thấy đúng số còn lại (props.invoice chỉ làm mới khi bảng hóa đơn
// ở ngoài load lại).
const currentInvoice = ref(null);

const form = reactive({ mode: "full", amount: null, method: "cash", note: "" });
const saving = ref(false);
const formError = ref("");

function defaultAmountFor(mode) {
  if (mode !== "full") return null;
  return Number(currentInvoice.value?.outstanding_amount) || null;
}

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
    currentInvoice.value = props.invoice;
    form.mode = "full";
    form.amount = defaultAmountFor("full");
    form.method = "cash";
    form.note = "";
    load();
  },
);

watch(
  () => form.mode,
  (mode) => {
    form.amount = defaultAmountFor(mode);
  },
);

async function submit() {
  formError.value = "";
  saving.value = true;
  try {
    currentInvoice.value = await invoicesApi.recordPayment(props.invoice.id, {
      amount: form.amount,
      method: form.method,
      note: form.note,
    });
    form.amount = defaultAmountFor(form.mode);
    form.note = "";
    await load();
    emit("recorded");
  } catch (err) {
    formError.value = errorMessage(err, "Không ghi nhận được thanh toán.");
  } finally {
    saving.value = false;
  }
}

function confirmCreditExcess() {
  const excess = Math.abs(Number(currentInvoice.value.outstanding_amount));
  confirm.require({
    header: "Hoàn phần thu dư vào số dư học sinh",
    message: `Hóa đơn ${currentInvoice.value.qr_reference_code} đang thu dư ${formatMoney(excess)}. Hoàn số này vào số dư (credit) của học sinh để dùng cho kỳ sau?`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Hoàn vào số dư",
    rejectLabel: "Đóng",
    accept: async () => {
      try {
        currentInvoice.value = await invoicesApi.refund(currentInvoice.value.id, {
          amount: excess,
          method: "credit",
          cancel_obligation: false,
          reason: "Hoàn phần thu dư vào số dư học sinh",
        });
        form.amount = defaultAmountFor(form.mode);
        toast.add({ severity: "success", summary: "Đã hoàn vào số dư học sinh", life: 2500 });
        emit("recorded");
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="invoice ? `Thanh toán — ${invoice.qr_reference_code}` : 'Thanh toán'"
    :loading="loading"
    :style="{ width: '42rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-4">
      <section class="flex flex-col gap-2">
        <span class="text-sm font-medium">Chi tiết hóa đơn</span>

        <DataTable :value="invoice?.items ?? []" size="small" striped-rows data-key="id">
          <template #empty>
            <div class="py-2 text-center text-surface-500 text-sm">Không có dòng nào.</div>
          </template>
          <Column field="fee_item_name_snapshot" header="Khoản thu" />
          <Column header="Số tiền" style="width: 8rem">
            <template #body="{ data }">{{ formatMoney(data.amount) }}</template>
          </Column>
        </DataTable>

        <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-surface-600 dark:text-surface-300">
          <span v-if="Number(invoice?.adjustment_amount)">
            Điều chỉnh: <strong>{{ formatMoney(invoice.adjustment_amount) }}</strong>
            <template v-if="invoice.adjustment_note"> ({{ invoice.adjustment_note }})</template>
          </span>
          <span>Phải thu: <strong>{{ formatMoney(invoice?.net_amount) }}</strong></span>
          <span class="inline-flex items-center gap-1">
            Còn nợ:
            <strong :class="Number(currentInvoice?.outstanding_amount) < 0 ? 'text-orange-500' : ''">
              {{ formatMoney(currentInvoice?.outstanding_amount) }}
            </strong>
            <Button
              v-if="Number(currentInvoice?.outstanding_amount) < 0"
              label="Hoàn về số dư của học sinh"
              icon="pi pi-wallet"
              severity="warn"
              text
              size="small"
              @click="confirmCreditExcess"
            />
          </span>
          <span>Hạn nộp: <strong>{{ formatDate(invoice?.due_date) }}</strong></span>
        </div>
      </section>

      <section class="flex flex-col gap-2 pt-3 border-t border-surface-200 dark:border-surface-700">
        <span class="text-sm font-medium">Lịch sử thanh toán</span>
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
      </section>

      <form
        v-if="canRecord"
        id="pay-form"
        class="flex flex-col gap-3 pt-3 border-t border-surface-200 dark:border-surface-700"
        @submit.prevent="submit"
      >
        <span class="text-sm font-medium">Ghi nhận thanh toán</span>
        <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>

        <SelectButton
          v-model="form.mode"
          :options="MODE_OPTIONS"
          option-label="label"
          option-value="value"
          :allow-empty="false"
        />

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
              :disabled="form.mode === 'full'"
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
            type="submit"
            :label="form.mode === 'full' ? 'Thanh toán ngay' : 'Ghi nhận đợt này'"
            icon="pi pi-check"
            :loading="saving"
            :disabled="!form.amount"
          />
        </div>
      </form>

      <Message v-else-if="invoice?.status === 'fully_refunded'" severity="info" :closable="false">
        Hóa đơn này đã được hoàn đủ tiền — không thể ghi nhận thanh toán thêm. Nếu học sinh cần
        đóng lại khoản phí này, hãy tạo một hóa đơn mới.
      </Message>
    </div>
  </AppDialog>
</template>
