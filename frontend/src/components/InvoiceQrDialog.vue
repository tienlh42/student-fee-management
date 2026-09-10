<script setup>
import { ref, watch } from "vue";

import Message from "primevue/message";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage } from "@/api/client";
import { invoicesApi } from "@/api/billing";
import { formatMoney } from "@/utils/money";

const props = defineProps({
  visible: { type: Boolean, default: false },
  invoice: { type: Object, default: null },
});
const emit = defineEmits(["update:visible"]);

const loading = ref(false);
const error = ref("");
const qr = ref(null);

watch(
  () => props.visible,
  async (open) => {
    if (!open || !props.invoice) return;
    error.value = "";
    qr.value = null;
    loading.value = true;
    try {
      qr.value = await invoicesApi.vietqr(props.invoice.id);
    } catch (err) {
      error.value = errorMessage(err, "Không tạo được mã QR thanh toán.");
    } finally {
      loading.value = false;
    }
  },
);
</script>

<template>
  <AppDialog
    :visible="visible"
    header="QR thanh toán"
    :loading="loading"
    :style="{ width: '26rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-3">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <template v-if="qr">
        <Message v-if="!qr.url" severity="warn" :closable="false">
          Cơ sở chưa cấu hình tài khoản ngân hàng nhận tiền, hoặc hóa đơn này không còn số tiền
          phải thu.
        </Message>

        <template v-else>
          <div class="flex justify-center">
            <img :src="qr.url" alt="Mã QR thanh toán" class="w-56 h-56" />
          </div>

          <div class="flex flex-col gap-1 text-sm">
            <div class="flex justify-between">
              <span class="text-surface-500">Số tiền</span>
              <strong>{{ formatMoney(qr.amount) }}</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Nội dung chuyển khoản</span>
              <strong>{{ qr.reference_code }}</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Ngân hàng</span>
              <span>{{ qr.bank_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Chủ tài khoản</span>
              <span>{{ qr.account_holder_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Số tài khoản</span>
              <span>****{{ qr.account_number_last4 }}</span>
            </div>
          </div>

          <p class="text-xs text-surface-500">
            Quét mã bằng app ngân hàng/ví — giữ nguyên nội dung chuyển khoản để hệ thống tự động
            khớp thanh toán vào hóa đơn này.
          </p>
        </template>
      </template>
    </div>
  </AppDialog>
</template>
