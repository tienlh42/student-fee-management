<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import Select from "primevue/select";
import Textarea from "primevue/textarea";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage } from "@/api/client";
import { invoicesApi } from "@/api/billing";
import { refundsApi } from "@/api/payments";
import { useCloseGuard, useDirtyTracking } from "@/utils/dirty";
import { formatDateTime } from "@/utils/date";
import { formatMoney } from "@/utils/money";

const props = defineProps({
  visible: { type: Boolean, default: false },
  invoice: { type: Object, default: null },
  methodOptions: { type: Array, required: true }, // [{value, label}]
});
const emit = defineEmits(["update:visible", "refunded"]);

function blankForm() {
  return { amount: null, cancel_obligation: false, method: "bank_transfer", reason: "" };
}

const METHOD_DESCRIPTIONS = {
  bank_transfer: "Chuyển khoản lại vào tài khoản ngân hàng của phụ huynh.",
  cash: "Trả lại trực tiếp bằng tiền mặt.",
  credit:
    "Không chuyển tiền ra ngoài — cộng vào số dư (credit) của học sinh để trừ dần vào hóa đơn kỳ sau.",
};

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const { dirty, markClean } = useDirtyTracking(form);
const { guardedClose } = useCloseGuard();

// Bản chụp hóa đơn dùng để hiển thị/tính toán trong dialog — cập nhật lại từ
// response sau mỗi lần hoàn, để hoàn nhiều lần liên tiếp trong cùng lần mở
// dialog vẫn thấy đúng "đã thực nhận" còn lại (props.invoice chỉ làm mới khi
// bảng hóa đơn ở ngoài load lại).
const currentInvoice = ref(null);

const refundHistory = ref([]);
const historyLoading = ref(false);
const historyError = ref("");

const maxRefundAmount = computed(() => Number(currentInvoice.value?.net_paid) || 0);
const amountExceedsAvailable = computed(
  () => Number(form.amount) > maxRefundAmount.value,
);

function cancel() {
  guardedClose(dirty.value, () => emit("update:visible", false));
}

async function loadHistory() {
  historyLoading.value = true;
  historyError.value = "";
  try {
    const page = await refundsApi.list({ invoice: props.invoice.id, page_size: 100 });
    refundHistory.value = page.results ?? page;
  } catch (err) {
    historyError.value = errorMessage(err, "Không tải được lịch sử hoàn tiền.");
  } finally {
    historyLoading.value = false;
  }
}

watch(
  () => props.visible,
  (open) => {
    if (!open || !props.invoice) return;
    error.value = "";
    currentInvoice.value = props.invoice;
    Object.assign(form, blankForm());
    form.amount = Number(props.invoice.net_paid) || null;
    markClean();
    loadHistory();
  },
);

async function submit() {
  error.value = "";
  if (amountExceedsAvailable.value) {
    error.value = "Số tiền hoàn không được vượt quá số đã thực nhận.";
    return;
  }
  saving.value = true;
  try {
    currentInvoice.value = await invoicesApi.refund(props.invoice.id, { ...form });
    Object.assign(form, blankForm());
    form.amount = Number(currentInvoice.value.net_paid) || null;
    markClean();
    await loadHistory();
    emit("refunded");
  } catch (err) {
    error.value = errorMessage(err, "Không hoàn tiền được.");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="invoice ? `Hoàn tiền — ${invoice.qr_reference_code}` : 'Hoàn tiền'"
    :loading="saving"
    :dirty="dirty"
    :style="{ width: '38rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-4">
      <Message v-if="historyError" severity="error" :closable="false">{{ historyError }}</Message>

      <DataTable :value="refundHistory" :loading="historyLoading" size="small" striped-rows data-key="id">
        <template #empty>
          <div class="py-4 text-center text-surface-500 text-sm">Chưa có lần hoàn tiền nào.</div>
        </template>
        <Column field="refunded_at" header="Thời gian" style="width: 10rem">
          <template #body="{ data }">{{ formatDateTime(data.refunded_at) }}</template>
        </Column>
        <Column header="Số tiền" style="width: 8rem">
          <template #body="{ data }">{{ formatMoney(data.amount) }}</template>
        </Column>
        <Column field="method_display" header="Phương thức" style="width: 8rem" />
        <Column field="refunded_by_username" header="Người thực hiện" />
        <Column field="reason" header="Lý do" />
      </DataTable>

      <form
        id="refund-form"
        class="flex flex-col gap-4 pt-3 border-t border-surface-200 dark:border-surface-700"
        @submit.prevent="submit"
      >
        <span class="text-sm font-medium">Hoàn tiền một lần mới</span>
        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <p v-if="currentInvoice" class="text-sm text-surface-500">
          Đã thực nhận (sau các lần hoàn trước, nếu có):
          <span class="font-medium text-surface-700 dark:text-surface-200">
            {{ formatMoney(currentInvoice.net_paid) }}
          </span>
        </p>

        <div class="flex flex-col gap-1">
          <label for="refund-amount" class="text-sm font-medium">Số tiền hoàn *</label>
          <InputNumber
            id="refund-amount"
            v-model="form.amount"
            mode="decimal"
            :min="0"
            :max-fraction-digits="0"
            suffix=" đ"
            :invalid="amountExceedsAvailable"
          />
          <small v-if="amountExceedsAvailable" class="text-red-500">
            Vượt quá số đã thực nhận — tối đa {{ formatMoney(maxRefundAmount) }}.
          </small>
          <small v-else class="text-surface-500">
            Tối đa bằng số đã thực nhận — mặc định gợi ý bằng số đó.
          </small>
        </div>

        <div class="flex items-start gap-2">
          <Checkbox v-model="form.cancel_obligation" input-id="refund-cancel" binary class="mt-0.5" />
          <label for="refund-cancel" class="text-sm">
            Hủy nghĩa vụ của hóa đơn này (học sinh không còn nợ khoản này nữa — nghỉ học, hủy dịch vụ...).
            Bỏ trống nếu khoản phí vẫn còn hiệu lực, chỉ điều chỉnh lại số đã nộp.
          </label>
        </div>

        <div class="flex flex-col gap-1">
          <label for="refund-method" class="text-sm font-medium">Phương thức hoàn *</label>
          <Select
            id="refund-method"
            v-model="form.method"
            :options="methodOptions"
            option-label="label"
            option-value="value"
          />
          <small v-if="METHOD_DESCRIPTIONS[form.method]" class="text-surface-500">
            {{ METHOD_DESCRIPTIONS[form.method] }}
          </small>
        </div>

        <div class="flex flex-col gap-1">
          <label for="refund-reason" class="text-sm font-medium">Lý do</label>
          <Textarea id="refund-reason" v-model="form.reason" rows="2" auto-resize />
        </div>
      </form>
    </div>

    <template #footer>
      <Button label="Đóng" severity="secondary" text @click="cancel" />
      <Button
        type="submit"
        form="refund-form"
        label="Xác nhận hoàn tiền"
        icon="pi pi-replay"
        severity="warn"
        :loading="saving"
        :disabled="!form.amount || amountExceedsAvailable"
      />
    </template>
  </AppDialog>
</template>
