<script setup>
import { reactive, ref, watch } from "vue";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import Select from "primevue/select";
import Textarea from "primevue/textarea";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage } from "@/api/client";
import { invoicesApi } from "@/api/billing";
import { useCloseGuard, useDirtyTracking } from "@/utils/dirty";
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

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const { dirty, markClean } = useDirtyTracking(form);
const { guardedClose } = useCloseGuard();

function cancel() {
  guardedClose(dirty.value, () => emit("update:visible", false));
}

watch(
  () => props.visible,
  (open) => {
    if (!open || !props.invoice) return;
    error.value = "";
    Object.assign(form, blankForm());
    form.amount = Number(props.invoice.net_paid) || null;
    markClean();
  },
);

async function submit() {
  error.value = "";
  saving.value = true;
  try {
    await invoicesApi.refund(props.invoice.id, { ...form });
    emit("refunded");
    emit("update:visible", false);
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
    :style="{ width: '32rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="refund-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <p v-if="invoice" class="text-sm text-surface-500">
        Đã thực nhận (sau các lần hoàn trước, nếu có):
        <span class="font-medium text-surface-700 dark:text-surface-200">
          {{ formatMoney(invoice.net_paid) }}
        </span>
      </p>

      <div class="flex flex-col gap-1">
        <label for="refund-amount" class="text-sm font-medium">Số tiền hoàn *</label>
        <InputNumber
          id="refund-amount"
          v-model="form.amount"
          mode="decimal"
          :min="0"
          :max="Number(invoice?.net_paid) || 0"
          :max-fraction-digits="0"
          suffix=" đ"
        />
        <small class="text-surface-500">Tối đa bằng số đã thực nhận — mặc định gợi ý bằng số đó.</small>
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
      </div>

      <div class="flex flex-col gap-1">
        <label for="refund-reason" class="text-sm font-medium">Lý do</label>
        <Textarea id="refund-reason" v-model="form.reason" rows="2" auto-resize />
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="cancel" />
      <Button
        type="submit"
        form="refund-form"
        label="Xác nhận hoàn tiền"
        icon="pi pi-replay"
        severity="warn"
        :loading="saving"
        :disabled="!form.amount"
      />
    </template>
  </AppDialog>
</template>
