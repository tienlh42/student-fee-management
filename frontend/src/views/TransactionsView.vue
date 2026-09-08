<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Tag from "primevue/tag";
import Toolbar from "primevue/toolbar";

import AllocateTransactionDialog from "@/components/AllocateTransactionDialog.vue";
import AppDialog from "@/components/AppDialog.vue";
import StatusLegendDialog from "@/components/StatusLegendDialog.vue";
import { errorMessage } from "@/api/client";
import { incomingTransactionsApi } from "@/api/payments";
import { formatDateTime } from "@/utils/date";
import { formatMoney } from "@/utils/money";

const toast = useToast();
const confirm = useConfirm();

const STATUS_SEVERITY = {
  unmatched: "warn",
  partially_matched: "info",
  matched: "success",
  ignored: "secondary",
};

const STATUS_HELP = [
  {
    value: "unmatched",
    label: "Chưa khớp",
    severity: STATUS_SEVERITY.unmatched,
    description:
      "Chưa có khoản nào trong giao dịch được phân bổ vào hóa đơn nào — hệ thống không tìm được mã tham chiếu khớp, hoặc chưa thử khớp lại.",
  },
  {
    value: "partially_matched",
    label: "Khớp một phần",
    severity: STATUS_SEVERITY.partially_matched,
    description: "Một phần số tiền đã phân bổ vào hóa đơn, phần còn lại vẫn chưa có nơi nhận.",
  },
  {
    value: "matched",
    label: "Đã khớp",
    severity: STATUS_SEVERITY.matched,
    description: "Toàn bộ số tiền của giao dịch đã được phân bổ hết vào (các) hóa đơn.",
  },
  {
    value: "ignored",
    label: "Bỏ qua",
    severity: STATUS_SEVERITY.ignored,
    description:
      "Đánh dấu không cần đối soát (vd: chuyển khoản không liên quan đến học phí). Chỉ bỏ qua được khi giao dịch chưa khớp phần nào.",
  },
];
const statusHelpVisible = ref(false);

const meta = ref({ statuses: [] });
const rows = ref([]);
const total = ref(0);
const loading = ref(false);
const filters = reactive({ search: "", status: null });
const paging = reactive({ page: 1, rows: 25 });

const allocateVisible = ref(false);
const selectedTransaction = ref(null);

const allocationsVisible = ref(false);
const selectedAllocations = ref([]);

async function load() {
  loading.value = true;
  try {
    const page = await incomingTransactionsApi.list({
      search: filters.search,
      status: filters.status,
      page: paging.page,
      page_size: paging.rows,
    });
    rows.value = page.results ?? page;
    total.value = page.count ?? rows.value.length;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    loading.value = false;
  }
}

async function loadMeta() {
  try {
    meta.value = await incomingTransactionsApi.meta();
  } catch {
    meta.value = { statuses: [] };
  }
}

let searchTimer;
watch(
  () => filters.search,
  () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      paging.page = 1;
      load();
    }, 300);
  },
);
watch(
  () => filters.status,
  () => {
    paging.page = 1;
    load();
  },
);

function onPage(event) {
  paging.page = event.page + 1;
  paging.rows = event.rows;
  load();
}

async function retryMatch(row) {
  try {
    const result = await incomingTransactionsApi.retryMatch(row.id);
    toast.add({
      severity: result.matched ? "success" : "info",
      summary: result.matched ? `Đã khớp thêm ${result.matched} khoản` : "Không khớp thêm được gì mới",
      life: 3000,
    });
    await load();
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  }
}

function openAllocate(row) {
  selectedTransaction.value = row;
  allocateVisible.value = true;
}

async function onAllocated() {
  toast.add({ severity: "success", summary: "Đã phân bổ", life: 2500 });
  await load();
}

function viewAllocations(row) {
  selectedAllocations.value = row.payments;
  allocationsVisible.value = true;
}

function confirmIgnore(row) {
  confirm.require({
    header: "Bỏ qua giao dịch",
    message: `Đánh dấu giao dịch "${row.transfer_content || row.id}" là không cần đối soát?`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Bỏ qua",
    rejectLabel: "Đóng",
    accept: async () => {
      try {
        await incomingTransactionsApi.ignore(row.id);
        toast.add({ severity: "success", summary: "Đã bỏ qua giao dịch", life: 2500 });
        await load();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

onMounted(async () => {
  await Promise.all([loadMeta(), load()]);
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <Toolbar>
      <template #start>
        <div class="flex flex-wrap items-center gap-2">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="filters.search" placeholder="Tìm nội dung chuyển khoản…" />
          </IconField>

          <Select
            v-model="filters.status"
            :options="meta.statuses"
            option-label="label"
            option-value="value"
            placeholder="Trạng thái"
            show-clear
            class="w-48"
          />
        </div>
      </template>
    </Toolbar>

    <DataTable
      :value="rows"
      :loading="loading"
      data-key="id"
      lazy
      paginator
      :rows="paging.rows"
      :total-records="total"
      :rows-per-page-options="[25, 50, 100]"
      :first="(paging.page - 1) * paging.rows"
      size="small"
      striped-rows
      @page="onPage"
    >
      <template #empty>
        <div class="py-6 text-center text-surface-500 text-sm">
          Không có giao dịch nào khớp bộ lọc.
        </div>
      </template>

      <Column field="transaction_time" header="Thời gian" style="width: 10rem">
        <template #body="{ data }">{{ formatDateTime(data.transaction_time) }}</template>
      </Column>

      <Column field="transfer_content" header="Nội dung chuyển khoản" />

      <Column header="Số tiền" style="width: 9rem">
        <template #body="{ data }">{{ formatMoney(data.amount) }}</template>
      </Column>

      <Column header="Chưa phân bổ" style="width: 9rem">
        <template #body="{ data }">
          <span :class="Number(data.unallocated_amount) > 0 ? 'text-red-500 font-medium' : ''">
            {{ formatMoney(data.unallocated_amount) }}
          </span>
        </template>
      </Column>

      <Column field="status" style="width: 10rem">
        <template #header>
          <span class="inline-flex items-center gap-1">
            Trạng thái
            <Button
              v-tooltip.top="'Ý nghĩa các trạng thái'"
              icon="pi pi-question-circle"
              text
              rounded
              size="small"
              aria-label="Ý nghĩa các trạng thái"
              @click="statusHelpVisible = true"
            />
          </span>
        </template>
        <template #body="{ data }">
          <Tag :value="data.status_display" :severity="STATUS_SEVERITY[data.status]" />
        </template>
      </Column>

      <Column header="" style="width: 11rem">
        <template #body="{ data }">
          <div class="flex justify-end">
            <Button
              v-tooltip.top="'Xem đã phân bổ vào đâu'"
              icon="pi pi-eye"
              text
              rounded
              aria-label="Xem phân bổ"
              @click="viewAllocations(data)"
            />
            <Button
              v-if="data.status !== 'ignored' && data.status !== 'matched'"
              v-tooltip.top="'Khớp lại tự động'"
              icon="pi pi-refresh"
              text
              rounded
              aria-label="Khớp lại tự động"
              @click="retryMatch(data)"
            />
            <Button
              v-if="data.status !== 'ignored'"
              v-tooltip.top="'Phân bổ thủ công'"
              icon="pi pi-sitemap"
              text
              rounded
              aria-label="Phân bổ thủ công"
              @click="openAllocate(data)"
            />
            <Button
              v-if="data.status === 'unmatched'"
              v-tooltip.top="'Bỏ qua'"
              icon="pi pi-eye-slash"
              severity="danger"
              text
              rounded
              aria-label="Bỏ qua"
              @click="confirmIgnore(data)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <AllocateTransactionDialog
      v-model:visible="allocateVisible"
      :transaction="selectedTransaction"
      @allocated="onAllocated"
    />

    <AppDialog v-model:visible="allocationsVisible" header="Đã phân bổ vào" :style="{ width: '34rem' }">
      <p v-if="!selectedAllocations.length" class="text-sm text-surface-500">
        Chưa phân bổ vào hóa đơn nào.
      </p>
      <ul class="flex flex-col gap-2">
        <li
          v-for="payment in selectedAllocations"
          :key="payment.id"
          class="flex items-center justify-between gap-4 rounded border border-surface-200 p-3 dark:border-surface-700"
        >
          <div class="flex flex-col">
            <span class="font-medium">{{ payment.invoice_reference }}</span>
            <span class="text-sm text-surface-500">{{ payment.student_name }}</span>
          </div>
          <span class="font-medium">{{ formatMoney(payment.amount_applied) }}</span>
        </li>
      </ul>
    </AppDialog>

    <StatusLegendDialog
      v-model:visible="statusHelpVisible"
      title="Ý nghĩa các trạng thái giao dịch"
      :items="STATUS_HELP"
    />
  </div>
</template>
