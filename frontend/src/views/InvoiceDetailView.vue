<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Card from "primevue/card";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";
import Tag from "primevue/tag";

import { errorMessage } from "@/api/client";
import { housesApi } from "@/api/accounts";
import { invoicesApi } from "@/api/billing";
import { studentsApi } from "@/api/people";
import { paymentsApi, refundsApi } from "@/api/payments";
import InvoicePaymentsDialog from "@/components/InvoicePaymentsDialog.vue";
import RefundDialog from "@/components/RefundDialog.vue";
import StatusTag from "@/components/StatusTag.vue";
import { useAuthStore } from "@/stores/auth";
import { formatDate, formatDateTime } from "@/utils/date";
import { formatMoney, formatPeriod } from "@/utils/money";

const STATUS_SEVERITY = {
  draft: "secondary",
  issued: "info",
  partially_paid: "warn",
  paid: "success",
  fully_refunded: "contrast",
  void: "danger",
};

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const toast = useToast();
const confirm = useConfirm();

const loading = ref(true);
const notFound = ref(false);
const error = ref("");

const invoice = ref(null);
const student = ref(null);
const house = ref(null);
const activity = ref([]);

const guardians = computed(() => student.value?.guardians ?? []);

const paymentsVisible = ref(false);
const refundVisible = ref(false);
const paymentMethodOptions = ref([]);
const refundMethodOptions = ref([]);

const canRecordPayment = computed(
  () =>
    auth.canEdit &&
    invoice.value?.status !== "paid" &&
    invoice.value?.status !== "fully_refunded",
);
const canVoid = computed(
  () =>
    auth.canEdit &&
    !["void", "paid", "fully_refunded"].includes(invoice.value?.status),
);

async function loadMethodOptions() {
  if (!auth.role.can_see_bank_data) return;
  try {
    const [paymentMeta, refundMeta] = await Promise.all([
      paymentsApi.meta(),
      refundsApi.meta(),
    ]);
    paymentMethodOptions.value = paymentMeta.payment_methods;
    refundMethodOptions.value = refundMeta.methods;
  } catch {
    paymentMethodOptions.value = [];
    refundMethodOptions.value = [];
  }
}

async function loadActivity() {
  if (!auth.role.can_see_bank_data) return;
  const [payments, refundPage] = await Promise.all([
    invoicesApi.payments(invoice.value.id),
    refundsApi.list({ invoice: invoice.value.id, page_size: 100 }),
  ]);
  const refunds = refundPage.results ?? refundPage;
  activity.value = [
    ...payments.map((p) => ({
      key: `payment-${p.id}`,
      type: "payment",
      at: p.created_at,
      amount: Number(p.amount_applied),
      method_display: p.payment_method_display,
      actor: p.recorded_by_username,
      note: p.note,
    })),
    ...refunds.map((r) => ({
      key: `refund-${r.id}`,
      type: "refund",
      at: r.refunded_at,
      amount: -Number(r.amount),
      method_display: r.method_display,
      actor: r.refunded_by_username,
      note: r.reason,
    })),
  ].sort((a, b) => new Date(b.at) - new Date(a.at));
}

async function load() {
  loading.value = true;
  error.value = "";
  notFound.value = false;
  try {
    const page = await invoicesApi.list({ code: route.params.code, page_size: 1 });
    const rows = page.results ?? page;
    if (!rows.length) {
      notFound.value = true;
      return;
    }
    invoice.value = rows[0];

    const [studentData, houseData] = await Promise.all([
      studentsApi.retrieve(invoice.value.student),
      housesApi.retrieve(invoice.value.house),
    ]);
    student.value = studentData;
    house.value = houseData;

    await loadActivity();
  } catch (err) {
    error.value = errorMessage(err, "Không tải được hóa đơn.");
  } finally {
    loading.value = false;
  }
}

async function onRecorded() {
  toast.add({ severity: "success", summary: "Đã ghi nhận thanh toán", life: 2500 });
  await load();
}

async function onRefunded() {
  toast.add({ severity: "success", summary: "Đã hoàn tiền", life: 2500 });
  await load();
}

function confirmCreditExcess() {
  const excess = Math.abs(Number(invoice.value.outstanding_amount));
  confirm.require({
    header: "Hoàn phần thu dư vào số dư học sinh",
    message: `Hóa đơn ${invoice.value.qr_reference_code} đang thu dư ${formatMoney(excess)}. Hoàn số này vào số dư (credit) của ${invoice.value.student_name} để dùng cho kỳ sau?`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Hoàn vào số dư",
    rejectLabel: "Đóng",
    accept: async () => {
      try {
        await invoicesApi.refund(invoice.value.id, {
          amount: excess,
          method: "credit",
          cancel_obligation: false,
          reason: "Hoàn phần thu dư vào số dư học sinh",
        });
        toast.add({ severity: "success", summary: "Đã hoàn vào số dư học sinh", life: 2500 });
        await load();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

function confirmVoid() {
  confirm.require({
    header: "Hủy hóa đơn",
    message: `Hủy hóa đơn ${invoice.value.qr_reference_code} của ${invoice.value.student_name}?`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Hủy hóa đơn",
    rejectLabel: "Đóng",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await invoicesApi.void(invoice.value.id);
        toast.add({ severity: "success", summary: "Đã hủy hóa đơn", life: 2500 });
        await load();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

function confirmRestore() {
  confirm.require({
    header: "Khôi phục hóa đơn",
    message: `Khôi phục hóa đơn ${invoice.value.qr_reference_code} của ${invoice.value.student_name}?`,
    icon: "pi pi-question-circle",
    acceptLabel: "Khôi phục",
    rejectLabel: "Đóng",
    accept: async () => {
      try {
        await invoicesApi.restore(invoice.value.id);
        toast.add({ severity: "success", summary: "Đã khôi phục hóa đơn", life: 2500 });
        await load();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

function confirmDelete() {
  confirm.require({
    header: "Xóa hóa đơn",
    message: `Xóa hẳn hóa đơn ${invoice.value.qr_reference_code} của ${invoice.value.student_name}? Sau khi xóa có thể sinh lại hóa đơn khác cho cùng kỳ này.`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await invoicesApi.remove(invoice.value.id);
        toast.add({ severity: "success", summary: "Đã xóa hóa đơn", life: 2500 });
        router.push("/invoices");
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 5000 });
      }
    },
  });
}

watch(() => route.params.code, load);
onMounted(async () => {
  await Promise.all([load(), loadMethodOptions()]);
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-2">
      <Button
        icon="pi pi-arrow-left"
        text
        rounded
        aria-label="Quay lại danh sách hóa đơn"
        @click="router.push('/invoices')"
      />
      <h1 class="text-lg font-semibold">
        Hóa đơn {{ invoice?.qr_reference_code ?? route.params.code }}
      </h1>
    </div>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-if="notFound" severity="warn" :closable="false">
      Không tìm thấy hóa đơn với mã "{{ route.params.code }}".
    </Message>

    <Skeleton v-if="loading" height="12rem" />

    <template v-else-if="invoice">
      <div class="flex flex-wrap items-center gap-3">
        <StatusTag :value="invoice.status_display" :severity="STATUS_SEVERITY[invoice.status]" />
        <span class="text-sm text-surface-500">
          Kỳ {{ formatPeriod(invoice.period) }} · Hạn nộp {{ formatDate(invoice.due_date) }}
        </span>

        <div class="ml-auto flex flex-wrap gap-2">
          <Button
            v-if="auth.role.can_see_bank_data"
            label="Thanh toán / lịch sử"
            icon="pi pi-wallet"
            @click="paymentsVisible = true"
          />
          <Button
            v-if="auth.role.can_see_bank_data && Number(invoice.net_paid) > 0"
            label="Hoàn tiền"
            icon="pi pi-replay"
            severity="warn"
            @click="refundVisible = true"
          />
          <Button
            v-if="auth.canEdit && invoice.status === 'void'"
            label="Khôi phục"
            icon="pi pi-history"
            @click="confirmRestore"
          />
          <Button
            v-if="canVoid"
            label="Hủy hóa đơn"
            icon="pi pi-ban"
            severity="danger"
            outlined
            @click="confirmVoid"
          />
          <Button
            v-if="auth.canEdit && invoice.status === 'draft'"
            label="Xóa"
            icon="pi pi-trash"
            severity="danger"
            outlined
            @click="confirmDelete"
          />
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <template #title>
            <span class="text-sm font-medium text-surface-500">Học sinh</span>
          </template>
          <template #content>
            <div v-if="student" class="flex flex-col gap-1 text-sm">
              <div class="text-base font-medium">{{ student.full_name }}</div>
              <div>Lớp: {{ student.class_grade || "—" }}</div>
              <div>Điện thoại: {{ student.phone || "—" }}</div>
              <div>Trạng thái: {{ student.status_display }}</div>
            </div>
          </template>
        </Card>

        <Card>
          <template #title>
            <span class="text-sm font-medium text-surface-500">Phụ huynh</span>
          </template>
          <template #content>
            <div v-if="guardians.length" class="flex flex-col gap-2 text-sm">
              <div v-for="g in guardians" :key="g.person_id">
                <div class="font-medium">
                  {{ g.full_name }}
                  <Tag v-if="g.is_primary_contact" value="Liên hệ chính" severity="info" />
                </div>
                <div class="text-surface-500">
                  {{ g.relationship_type_display }}
                  <template v-if="g.phone"> · {{ g.phone }}</template>
                </div>
              </div>
            </div>
            <span v-else class="text-sm text-surface-400">Chưa có phụ huynh liên kết.</span>
          </template>
        </Card>

        <Card>
          <template #title>
            <span class="text-sm font-medium text-surface-500">Cơ sở</span>
          </template>
          <template #content>
            <div v-if="house" class="flex flex-col gap-1 text-sm">
              <div class="text-base font-medium">{{ house.name }}</div>
              <div>{{ house.address || "—" }}</div>
            </div>
          </template>
        </Card>
      </div>

      <Card>
        <template #title>
          <span class="text-sm font-medium text-surface-500">Chi tiết hóa đơn</span>
        </template>
        <template #content>
          <DataTable :value="invoice.items" size="small" striped-rows data-key="id">
            <template #empty>
              <div class="py-2 text-center text-surface-500 text-sm">Không có dòng nào.</div>
            </template>
            <Column field="fee_item_name_snapshot" header="Khoản thu" />
            <Column header="Số tiền" style="width: 10rem">
              <template #body="{ data }">{{ formatMoney(data.amount) }}</template>
            </Column>
          </DataTable>

          <div class="flex flex-wrap gap-x-6 gap-y-1 pt-3 text-sm text-surface-600 dark:text-surface-300">
            <span v-if="Number(invoice.adjustment_amount)">
              Điều chỉnh: <strong>{{ formatMoney(invoice.adjustment_amount) }}</strong>
              <template v-if="invoice.adjustment_note"> ({{ invoice.adjustment_note }})</template>
            </span>
            <span>Phải thu: <strong>{{ formatMoney(invoice.net_amount) }}</strong></span>
            <span>Đã thu: <strong>{{ formatMoney(invoice.net_paid) }}</strong></span>
            <span v-if="Number(invoice.refunded_amount)">
              Đã hoàn: <strong>{{ formatMoney(invoice.refunded_amount) }}</strong>
            </span>
            <span class="inline-flex items-center gap-1">
              Còn nợ:
              <strong
                :class="
                  Number(invoice.outstanding_amount) > 0
                    ? 'text-red-500'
                    : Number(invoice.outstanding_amount) < 0
                      ? 'text-orange-500'
                      : ''
                "
              >
                {{ formatMoney(invoice.outstanding_amount) }}
              </strong>
              <Button
                v-if="auth.role.can_see_bank_data && Number(invoice.outstanding_amount) < 0"
                label="Hoàn về số dư của học sinh"
                icon="pi pi-wallet"
                severity="warn"
                text
                size="small"
                @click="confirmCreditExcess"
              />
            </span>
          </div>
        </template>
      </Card>

      <Card v-if="auth.role.can_see_bank_data">
        <template #title>
          <span class="text-sm font-medium text-surface-500">Lịch sử hoạt động</span>
        </template>
        <template #content>
          <DataTable :value="activity" size="small" striped-rows data-key="key">
            <template #empty>
              <div class="py-4 text-center text-surface-500 text-sm">Chưa có hoạt động nào.</div>
            </template>
            <Column header="Loại" style="width: 8rem">
              <template #body="{ data }">
                <Tag
                  :value="data.type === 'payment' ? 'Thu' : 'Hoàn'"
                  :severity="data.type === 'payment' ? 'success' : 'warn'"
                />
              </template>
            </Column>
            <Column header="Thời gian" style="width: 10rem">
              <template #body="{ data }">{{ formatDateTime(data.at) }}</template>
            </Column>
            <Column header="Số tiền" style="width: 9rem">
              <template #body="{ data }">
                <span :class="data.amount < 0 ? 'text-orange-500' : ''">
                  {{ data.amount < 0 ? "" : "+" }}{{ formatMoney(data.amount) }}
                </span>
              </template>
            </Column>
            <Column field="method_display" header="Hình thức" style="width: 9rem" />
            <Column field="actor" header="Người thực hiện" style="width: 9rem" />
            <Column field="note" header="Ghi chú / lý do" />
          </DataTable>
        </template>
      </Card>
    </template>

    <InvoicePaymentsDialog
      v-model:visible="paymentsVisible"
      :invoice="invoice"
      :can-record="canRecordPayment"
      :method-options="paymentMethodOptions"
      @recorded="onRecorded"
    />

    <RefundDialog
      v-model:visible="refundVisible"
      :invoice="invoice"
      :method-options="refundMethodOptions"
      @refunded="onRefunded"
    />
  </div>
</template>
