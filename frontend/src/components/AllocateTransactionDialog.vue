<script setup>
import { reactive, ref, watch } from "vue";

import Button from "primevue/button";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import Select from "primevue/select";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage } from "@/api/client";
import { invoicesApi } from "@/api/billing";
import { incomingTransactionsApi } from "@/api/payments";
import { useCloseGuard, useDirtyTracking } from "@/utils/dirty";
import { formatMoney } from "@/utils/money";

const props = defineProps({
  visible: { type: Boolean, default: false },
  transaction: { type: Object, default: null },
});
const emit = defineEmits(["update:visible", "allocated"]);

const form = reactive({ invoice: null, amount: null });
const invoiceOptions = ref([]);
const loadingInvoices = ref(false);
const saving = ref(false);
const error = ref("");
const { dirty, markClean } = useDirtyTracking(form);
const { guardedClose } = useCloseGuard();

function cancel() {
  guardedClose(dirty.value, () => emit("update:visible", false));
}

async function loadInvoiceOptions() {
  loadingInvoices.value = true;
  try {
    const page = await invoicesApi.list({
      house: props.transaction.house,
      page_size: 200,
    });
    const rows = page.results ?? page;
    invoiceOptions.value = rows
      .filter((row) => row.status !== "void")
      .map((row) => ({
        value: row.id,
        label: `${row.qr_reference_code} · ${row.student_name} · còn nợ ${formatMoney(row.outstanding_amount)}`,
      }));
  } catch {
    invoiceOptions.value = [];
  } finally {
    loadingInvoices.value = false;
  }
}

watch(
  () => props.visible,
  (open) => {
    if (!open || !props.transaction) return;
    error.value = "";
    form.invoice = null;
    form.amount = Number(props.transaction.unallocated_amount) || null;
    markClean();
    loadInvoiceOptions();
  },
);

async function submit() {
  error.value = "";
  saving.value = true;
  try {
    await incomingTransactionsApi.allocate(props.transaction.id, {
      invoice: form.invoice,
      amount: form.amount,
    });
    emit("allocated");
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không phân bổ được.");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppDialog
    :visible="visible"
    header="Phân bổ thủ công"
    :loading="saving"
    :dirty="dirty"
    :style="{ width: '32rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="allocate-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <p v-if="transaction" class="text-sm text-surface-500">
        Giao dịch "{{ transaction.transfer_content || "—" }}" — chưa phân bổ
        {{ formatMoney(transaction.unallocated_amount) }}.
      </p>

      <div class="flex flex-col gap-1">
        <label for="alloc-invoice" class="text-sm font-medium">Hóa đơn *</label>
        <Select
          id="alloc-invoice"
          v-model="form.invoice"
          :options="invoiceOptions"
          option-label="label"
          option-value="value"
          placeholder="Chọn hóa đơn"
          filter
          :loading="loadingInvoices"
        />
      </div>

      <div class="flex flex-col gap-1">
        <label for="alloc-amount" class="text-sm font-medium">Số tiền *</label>
        <InputNumber
          id="alloc-amount"
          v-model="form.amount"
          mode="decimal"
          :min="0"
          :max-fraction-digits="0"
          suffix=" đ"
        />
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="cancel" />
      <Button
        type="submit"
        form="allocate-form"
        label="Phân bổ"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!form.invoice || !form.amount"
      />
    </template>
  </AppDialog>
</template>
