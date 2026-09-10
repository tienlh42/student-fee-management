<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import DatePicker from "primevue/datepicker";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import Tag from "primevue/tag";
import Toolbar from "primevue/toolbar";

import { errorMessage } from "@/api/client";
import { studentsApi } from "@/api/people";
import {
  feeItemsApi,
  feePackagesApi,
  invoicesApi,
  studentDiscountsApi,
  studentFeePackagesApi,
} from "@/api/billing";
import { paymentsApi } from "@/api/payments";
import AppDataTable from "@/components/AppDataTable.vue";
import FeeItemFormDialog from "@/components/FeeItemFormDialog.vue";
import FeePackageFormDialog from "@/components/FeePackageFormDialog.vue";
import InvoiceGenerateDialog from "@/components/InvoiceGenerateDialog.vue";
import InvoicePaymentsDialog from "@/components/InvoicePaymentsDialog.vue";
import StatusLegendDialog from "@/components/StatusLegendDialog.vue";
import StatusTag from "@/components/StatusTag.vue";
import StudentBillingSummaryDialog from "@/components/StudentBillingSummaryDialog.vue";
import StudentDiscountFormDialog from "@/components/StudentDiscountFormDialog.vue";
import StudentFeePackageFormDialog from "@/components/StudentFeePackageFormDialog.vue";
import { useAuthStore } from "@/stores/auth";
import { useHouseScopeStore } from "@/stores/houseScope";
import { formatDate, toIsoDate } from "@/utils/date";
import { formatMoney, formatPeriod } from "@/utils/money";

const auth = useAuthStore();
const houseScope = useHouseScopeStore();
const toast = useToast();
const confirm = useConfirm();

const STATUS_SEVERITY = {
  draft: "secondary",
  issued: "info",
  partially_paid: "warn",
  paid: "success",
  void: "danger",
};

const INVOICE_STATUS_HELP = [
  {
    value: "draft",
    label: "Nháp",
    severity: STATUS_SEVERITY.draft,
    description:
      "Hóa đơn vừa được sinh, chưa ghi nhận khoản thu nào. Chỉ chuyển sang trạng thái khác khi có thanh toán.",
  },
  {
    value: "issued",
    label: "Đã phát hành",
    severity: STATUS_SEVERITY.issued,
    description:
      "Không còn ở trạng thái nháp nhưng cũng chưa thu được đồng nào — thường gặp nhất sau khi khôi phục một hóa đơn đã hủy mà trước đó chưa thu tiền.",
  },
  {
    value: "partially_paid",
    label: "Thanh toán một phần",
    severity: STATUS_SEVERITY.partially_paid,
    description: "Đã thu được một phần số tiền phải thu, vẫn còn nợ.",
  },
  {
    value: "paid",
    label: "Đã thanh toán",
    severity: STATUS_SEVERITY.paid,
    description: "Đã thu đủ số tiền phải thu (sau điều chỉnh/giảm trừ), không còn nợ.",
  },
  {
    value: "void",
    label: "Đã hủy",
    severity: STATUS_SEVERITY.void,
    description:
      "Hóa đơn bị hủy, không tính vào công nợ và không tự đổi trạng thái nữa. Có thể khôi phục lại — khi đó hệ thống tính lại đúng trạng thái theo số tiền đã thu trước khi hủy.",
  },
];
const invoiceStatusHelpVisible = ref(false);

const activeTab = ref("invoices");
const studentOptions = ref([]);

/* ---------- Hóa đơn ---------- */
const invoiceMeta = ref({ statuses: [] });
const invoiceRows = ref([]);
const invoiceTotal = ref(0);
const invoiceLoading = ref(false);
const invoiceFilters = reactive({ search: "", status: null, period: null });
const invoicePaging = reactive({ page: 1, rows: 10 });
const generateVisible = ref(false);
const studentSummaryVisible = ref(false);
const selectedStudentForSummary = ref(null);

function openStudentSummary(invoice) {
  selectedStudentForSummary.value = { id: invoice.student, name: invoice.student_name };
  studentSummaryVisible.value = true;
}

async function loadInvoices() {
  invoiceLoading.value = true;
  try {
    const page = await invoicesApi.list({
      search: invoiceFilters.search,
      status: invoiceFilters.status,
      period: invoiceFilters.period ? toIsoDate(invoiceFilters.period).slice(0, 8) + "01" : null,
      house: houseScope.houseId,
      page: invoicePaging.page,
      page_size: invoicePaging.rows,
    });
    invoiceRows.value = page.results ?? page;
    invoiceTotal.value = page.count ?? invoiceRows.value.length;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    invoiceLoading.value = false;
  }
}

async function loadInvoiceMeta() {
  try {
    invoiceMeta.value = await invoicesApi.meta();
  } catch {
    invoiceMeta.value = { statuses: [] };
  }
}

let invoiceSearchTimer;
watch(
  () => invoiceFilters.search,
  () => {
    clearTimeout(invoiceSearchTimer);
    invoiceSearchTimer = setTimeout(() => {
      invoicePaging.page = 1;
      loadInvoices();
    }, 300);
  },
);
watch(
  [() => invoiceFilters.status, () => invoiceFilters.period, () => houseScope.houseId],
  () => {
    invoicePaging.page = 1;
    loadInvoices();
  },
);

function onInvoicePage(event) {
  invoicePaging.page = event.page + 1;
  invoicePaging.rows = event.rows;
  loadInvoices();
}

const paymentsVisible = ref(false);
const selectedInvoiceForPayments = ref(null);
const paymentDialogMode = ref("installment");
const paymentMethodOptions = ref([]);

async function loadPaymentMethodOptions() {
  if (!auth.role.can_see_bank_data) return;
  try {
    const meta = await paymentsApi.meta();
    paymentMethodOptions.value = meta.payment_methods;
  } catch {
    paymentMethodOptions.value = [];
  }
}

function openPayNow(invoice) {
  selectedInvoiceForPayments.value = invoice;
  paymentDialogMode.value = "full";
  paymentsVisible.value = true;
}

function openPayments(invoice) {
  selectedInvoiceForPayments.value = invoice;
  paymentDialogMode.value = "installment";
  paymentsVisible.value = true;
}

async function onPaymentRecorded() {
  toast.add({ severity: "success", summary: "Đã ghi nhận thanh toán", life: 2500 });
  await loadInvoices();
}

async function onGenerated(result) {
  toast.add({
    severity: "success",
    summary: `Đã sinh ${result.created} hóa đơn mới (${result.existing} đã có sẵn).`,
    life: 4000,
  });
  await loadInvoices();
}

function confirmVoid(invoice) {
  confirm.require({
    header: "Hủy hóa đơn",
    message: `Hủy hóa đơn ${invoice.qr_reference_code} của ${invoice.student_name}?`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Hủy hóa đơn",
    rejectLabel: "Đóng",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await invoicesApi.void(invoice.id);
        toast.add({ severity: "success", summary: "Đã hủy hóa đơn", life: 2500 });
        await loadInvoices();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

function confirmDeleteInvoice(invoice) {
  confirm.require({
    header: "Xóa hóa đơn",
    message: `Xóa hẳn hóa đơn ${invoice.qr_reference_code} của ${invoice.student_name}? Sau khi xóa có thể sinh lại hóa đơn khác cho cùng kỳ này.`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await invoicesApi.remove(invoice.id);
        toast.add({ severity: "success", summary: "Đã xóa hóa đơn", life: 2500 });
        await loadInvoices();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 5000 });
      }
    },
  });
}

function confirmRestore(invoice) {
  confirm.require({
    header: "Khôi phục hóa đơn",
    message: `Khôi phục hóa đơn ${invoice.qr_reference_code} của ${invoice.student_name}?`,
    icon: "pi pi-question-circle",
    acceptLabel: "Khôi phục",
    rejectLabel: "Đóng",
    accept: async () => {
      try {
        await invoicesApi.restore(invoice.id);
        toast.add({ severity: "success", summary: "Đã khôi phục hóa đơn", life: 2500 });
        await loadInvoices();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

/* ---------- Khoản thu ---------- */
const feeItemMeta = ref({ categories: [] });
const feeItemRows = ref([]);
const feeItemLoading = ref(false);
const feeItemFormVisible = ref(false);
const selectedFeeItem = ref(null);
const feeItemSearch = ref("");

const feeItemOptions = computed(() =>
  feeItemRows.value.map((item) => ({ value: item.id, label: item.name })),
);

const filteredFeeItemRows = computed(() => {
  const term = feeItemSearch.value.trim().toLowerCase();
  if (!term) return feeItemRows.value;
  return feeItemRows.value.filter((row) => row.name.toLowerCase().includes(term));
});

async function loadFeeItems() {
  feeItemLoading.value = true;
  try {
    const page = await feeItemsApi.list({ page_size: 200 });
    feeItemRows.value = page.results ?? page;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    feeItemLoading.value = false;
  }
}

async function loadFeeItemMeta() {
  try {
    feeItemMeta.value = await feeItemsApi.meta();
  } catch {
    feeItemMeta.value = { categories: [] };
  }
}

function openCreateFeeItem() {
  selectedFeeItem.value = null;
  feeItemFormVisible.value = true;
}

function openEditFeeItem(row) {
  selectedFeeItem.value = row;
  feeItemFormVisible.value = true;
}

async function onFeeItemSaved(_row, wasEdit) {
  toast.add({
    severity: "success",
    summary: wasEdit ? "Đã cập nhật khoản thu" : "Đã thêm khoản thu",
    life: 2500,
  });
  await loadFeeItems();
}

function confirmDeleteFeeItem(row) {
  confirm.require({
    header: "Xóa khoản thu",
    message: `Xóa "${row.name}"? Thao tác này không hoàn tác được.`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await feeItemsApi.remove(row.id);
        toast.add({ severity: "success", summary: "Đã xóa khoản thu", life: 2500 });
        await loadFeeItems();
      } catch (err) {
        toast.add({
          severity: "error",
          summary: errorMessage(err, "Không xóa được — khoản thu đang được dùng trong gói phí."),
          life: 5000,
        });
      }
    },
  });
}

/* ---------- Gói phí ---------- */
const feePackageMeta = ref({ billing_timings: [], fee_items: [] });
const feePackageRows = ref([]);
const feePackageLoading = ref(false);
const feePackageFormVisible = ref(false);
const selectedFeePackage = ref(null);
const feePackageSearch = ref("");

const packageOptions = computed(() =>
  feePackageRows.value.map((pkg) => ({ value: pkg.id, label: pkg.name })),
);

const filteredFeePackageRows = computed(() => {
  const term = feePackageSearch.value.trim().toLowerCase();
  if (!term) return feePackageRows.value;
  return feePackageRows.value.filter((row) => row.name.toLowerCase().includes(term));
});

async function loadFeePackages() {
  feePackageLoading.value = true;
  try {
    const page = await feePackagesApi.list({ page_size: 200 });
    feePackageRows.value = page.results ?? page;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    feePackageLoading.value = false;
  }
}

async function loadFeePackageMeta() {
  try {
    feePackageMeta.value = await feePackagesApi.meta();
  } catch {
    feePackageMeta.value = { billing_timings: [], fee_items: [] };
  }
}

function openCreateFeePackage() {
  selectedFeePackage.value = null;
  feePackageFormVisible.value = true;
}

function openEditFeePackage(row) {
  selectedFeePackage.value = row;
  feePackageFormVisible.value = true;
}

async function onFeePackageSaved(_row, wasEdit) {
  toast.add({
    severity: "success",
    summary: wasEdit ? "Đã cập nhật gói phí" : "Đã thêm gói phí",
    life: 2500,
  });
  await Promise.all([loadFeePackages(), loadFeePackageMeta()]);
}

function confirmDeleteFeePackage(row) {
  confirm.require({
    header: "Xóa gói phí",
    message: `Xóa gói "${row.name}"? Thao tác này không hoàn tác được.`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await feePackagesApi.remove(row.id);
        toast.add({ severity: "success", summary: "Đã xóa gói phí", life: 2500 });
        await loadFeePackages();
      } catch (err) {
        toast.add({
          severity: "error",
          summary: errorMessage(err, "Không xóa được — gói phí đang có học sinh đăng ký."),
          life: 5000,
        });
      }
    },
  });
}

/* ---------- Đăng ký gói phí của học sinh ---------- */
const subscriptionRows = ref([]);
const subscriptionLoading = ref(false);
const subscriptionFormVisible = ref(false);
const selectedSubscription = ref(null);
const subscriptionSearch = ref("");

const filteredSubscriptionRows = computed(() => {
  const term = subscriptionSearch.value.trim().toLowerCase();
  if (!term) return subscriptionRows.value;
  return subscriptionRows.value.filter(
    (row) =>
      row.student_name.toLowerCase().includes(term) ||
      row.fee_package_name.toLowerCase().includes(term),
  );
});

async function loadSubscriptions() {
  subscriptionLoading.value = true;
  try {
    const page = await studentFeePackagesApi.list({ page_size: 200 });
    subscriptionRows.value = page.results ?? page;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    subscriptionLoading.value = false;
  }
}

function openCreateSubscription() {
  selectedSubscription.value = null;
  subscriptionFormVisible.value = true;
}

function openEditSubscription(row) {
  selectedSubscription.value = row;
  subscriptionFormVisible.value = true;
}

async function onSubscriptionSaved(_row, wasEdit) {
  toast.add({
    severity: "success",
    summary: wasEdit ? "Đã cập nhật đăng ký" : "Đã đăng ký gói phí",
    life: 2500,
  });
  await loadSubscriptions();
}

function confirmDeleteSubscription(row) {
  confirm.require({
    header: "Hủy đăng ký",
    message: `Hủy đăng ký gói "${row.fee_package_name}" của ${row.student_name}?`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Hủy đăng ký",
    rejectLabel: "Đóng",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await studentFeePackagesApi.remove(row.id);
        toast.add({ severity: "success", summary: "Đã hủy đăng ký", life: 2500 });
        await loadSubscriptions();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

/* ---------- Giảm trừ ---------- */
const discountRows = ref([]);
const discountLoading = ref(false);
const discountFormVisible = ref(false);
const selectedDiscount = ref(null);
const discountSearch = ref("");

const filteredDiscountRows = computed(() => {
  const term = discountSearch.value.trim().toLowerCase();
  if (!term) return discountRows.value;
  return discountRows.value.filter(
    (row) =>
      row.student_name.toLowerCase().includes(term) || row.name.toLowerCase().includes(term),
  );
});

async function loadDiscounts() {
  discountLoading.value = true;
  try {
    const page = await studentDiscountsApi.list({ page_size: 200 });
    discountRows.value = page.results ?? page;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    discountLoading.value = false;
  }
}

function openCreateDiscount() {
  selectedDiscount.value = null;
  discountFormVisible.value = true;
}

function openEditDiscount(row) {
  selectedDiscount.value = row;
  discountFormVisible.value = true;
}

async function onDiscountSaved(_row, wasEdit) {
  toast.add({
    severity: "success",
    summary: wasEdit ? "Đã cập nhật giảm trừ" : "Đã thêm giảm trừ",
    life: 2500,
  });
  await loadDiscounts();
}

function confirmDeleteDiscount(row) {
  confirm.require({
    header: "Xóa giảm trừ",
    message: `Xóa giảm trừ "${row.name}"?`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await studentDiscountsApi.remove(row.id);
        toast.add({ severity: "success", summary: "Đã xóa giảm trừ", life: 2500 });
        await loadDiscounts();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

onMounted(async () => {
  try {
    const page = await studentsApi.list({ page_size: 200 });
    studentOptions.value = (page.results ?? page).map((s) => ({
      value: s.id,
      label: s.class_grade ? `${s.full_name} · ${s.class_grade}` : s.full_name,
    }));
  } catch {
    studentOptions.value = [];
  }

  await Promise.all([
    loadInvoiceMeta(),
    loadInvoices(),
    loadFeeItemMeta(),
    loadFeeItems(),
    loadFeePackageMeta(),
    loadFeePackages(),
    loadSubscriptions(),
    loadDiscounts(),
    loadPaymentMethodOptions(),
  ]);
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="invoices">Hóa đơn</Tab>
        <Tab value="fee-items">Khoản thu</Tab>
        <Tab value="fee-packages">Gói phí</Tab>
        <Tab value="discounts">Giảm trừ</Tab>
      </TabList>

      <TabPanels>
        <!-- ===================== HÓA ĐƠN ===================== -->
        <TabPanel value="invoices">
          <div class="flex flex-col gap-4">
            <Toolbar>
              <template #start>
                <div class="flex flex-wrap items-center gap-2">
                  <IconField>
                    <InputIcon class="pi pi-search" />
                    <InputText v-model="invoiceFilters.search" placeholder="Tìm mã HĐ, tên học sinh…" />
                  </IconField>

                  <DatePicker
                    v-model="invoiceFilters.period"
                    view="month"
                    date-format="mm/yy"
                    placeholder="Kỳ"
                    show-icon
                    show-button-bar
                    class="w-40"
                  />

                  <Select
                    v-model="invoiceFilters.status"
                    :options="invoiceMeta.statuses"
                    option-label="label"
                    option-value="value"
                    placeholder="Trạng thái"
                    show-clear
                    class="w-44"
                  />
                </div>
              </template>

              <template #end>
                <Button
                  v-if="auth.canEdit"
                  label="Sinh hóa đơn"
                  icon="pi pi-file-plus"
                  @click="generateVisible = true"
                />
              </template>
            </Toolbar>

            <AppDataTable
              :value="invoiceRows"
              :loading="invoiceLoading"
              storage-key="invoices"
              data-key="id"
              lazy
              paginator
              :rows="invoicePaging.rows"
              :total-records="invoiceTotal"
              :rows-per-page-options="[10, 25, 50, 100]"
              :first="(invoicePaging.page - 1) * invoicePaging.rows"
              @page="onInvoicePage"
            >
              <template #empty>
                <div class="flex flex-col items-center gap-2 py-10 text-surface-400 dark:text-surface-500">
                  <i class="pi pi-file text-3xl" />
                  <span class="text-sm">Không có hóa đơn nào khớp bộ lọc.</span>
                </div>
              </template>

              <Column field="qr_reference_code" header="Mã HĐ" style="width: 8rem" />

              <Column field="student_name" header="Học sinh" sortable />

              <Column field="period" header="Kỳ" style="width: 6rem">
                <template #body="{ data }">{{ formatPeriod(data.period) }}</template>
              </Column>

              <Column field="due_date" header="Hạn nộp" style="width: 8rem">
                <template #body="{ data }">{{ formatDate(data.due_date) }}</template>
              </Column>

              <Column header="Phải thu" style="width: 9rem">
                <template #body="{ data }">{{ formatMoney(data.net_amount) }}</template>
              </Column>

              <Column header="Đã thu" style="width: 9rem">
                <template #body="{ data }">{{ formatMoney(data.paid_amount) }}</template>
              </Column>

              <Column header="Còn nợ" style="width: 9rem">
                <template #body="{ data }">
                  <span :class="Number(data.outstanding_amount) > 0 ? 'text-red-500 font-medium' : ''">
                    {{ formatMoney(data.outstanding_amount) }}
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
                      @click="invoiceStatusHelpVisible = true"
                    />
                  </span>
                </template>
                <template #body="{ data }">
                  <StatusTag :value="data.status_display" :severity="STATUS_SEVERITY[data.status]" />
                </template>
              </Column>

              <Column header="" style="width: 15.5rem">
                <template #body="{ data }">
                  <div class="flex justify-end">
                    <Button
                      v-tooltip.top="'Xem khoản thu, gói phí, giảm trừ của học sinh'"
                      icon="pi pi-eye"
                      text
                      rounded
                      aria-label="Xem chi tiết học sinh"
                      @click="openStudentSummary(data)"
                    />
                    <Button
                      v-if="auth.role.can_see_bank_data && data.status !== 'void' && data.status !== 'paid'"
                      v-tooltip.top="'Thanh toán ngay (đủ số còn nợ)'"
                      icon="pi pi-check-circle"
                      severity="success"
                      text
                      rounded
                      aria-label="Thanh toán ngay"
                      @click="openPayNow(data)"
                    />
                    <Button
                      v-if="auth.role.can_see_bank_data"
                      v-tooltip.top="'Chia thành nhiều đợt / lịch sử thanh toán'"
                      icon="pi pi-wallet"
                      text
                      rounded
                      aria-label="Lịch sử thanh toán"
                      @click="openPayments(data)"
                    />
                    <Button
                      v-if="auth.canEdit && data.status === 'void'"
                      v-tooltip.top="'Khôi phục hóa đơn'"
                      icon="pi pi-history"
                      text
                      rounded
                      aria-label="Khôi phục hóa đơn"
                      @click="confirmRestore(data)"
                    />
                    <Button
                      v-if="auth.canEdit && data.status !== 'void' && data.status !== 'paid'"
                      v-tooltip.top="'Hủy hóa đơn'"
                      icon="pi pi-ban"
                      severity="danger"
                      text
                      rounded
                      aria-label="Hủy hóa đơn"
                      @click="confirmVoid(data)"
                    />
                    <Button
                      v-if="auth.canEdit"
                      v-tooltip.top="'Xóa hóa đơn (để sinh lại kỳ này)'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      aria-label="Xóa hóa đơn"
                      @click="confirmDeleteInvoice(data)"
                    />
                  </div>
                </template>
              </Column>
            </AppDataTable>
          </div>
        </TabPanel>

        <!-- ===================== KHOẢN THU ===================== -->
        <TabPanel value="fee-items">
          <div class="flex flex-col gap-4">
            <Toolbar>
              <template #start>
                <IconField>
                  <InputIcon class="pi pi-search" />
                  <InputText v-model="feeItemSearch" placeholder="Tìm khoản thu…" />
                </IconField>
              </template>
              <template #end>
                <Button
                  v-if="auth.canEdit"
                  label="Thêm khoản thu"
                  icon="pi pi-plus"
                  @click="openCreateFeeItem"
                />
              </template>
            </Toolbar>

            <DataTable :value="filteredFeeItemRows" :loading="feeItemLoading" data-key="id" size="small" striped-rows>
              <template #empty>
                <div class="py-6 text-center text-surface-500 text-sm">Chưa có khoản thu nào.</div>
              </template>

              <Column field="name" header="Tên khoản thu" sortable />
              <Column field="category_display" header="Nhóm" style="width: 10rem" />
              <Column header="Số tiền mặc định" style="width: 10rem">
                <template #body="{ data }">{{ formatMoney(data.default_amount) }}</template>
              </Column>
              <Column header="Trạng thái" style="width: 9rem">
                <template #body="{ data }">
                  <Tag
                    :value="data.is_active ? 'Đang áp dụng' : 'Ngừng áp dụng'"
                    :severity="data.is_active ? 'success' : 'secondary'"
                  />
                </template>
              </Column>
              <Column header="" style="width: 7rem">
                <template #body="{ data }">
                  <div v-if="auth.canEdit" class="flex justify-end gap-1">
                    <Button
                      v-tooltip.top="'Sửa'"
                      icon="pi pi-pencil"
                      text
                      rounded
                      aria-label="Sửa"
                      @click="openEditFeeItem(data)"
                    />
                    <Button
                      v-tooltip.top="'Xóa'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      aria-label="Xóa"
                      @click="confirmDeleteFeeItem(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>

        <!-- ===================== GÓI PHÍ ===================== -->
        <TabPanel value="fee-packages">
          <div class="flex flex-col gap-6">
            <div class="flex flex-col gap-4">
              <Toolbar>
                <template #start>
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="font-medium">Gói phí</span>
                    <IconField>
                      <InputIcon class="pi pi-search" />
                      <InputText v-model="feePackageSearch" placeholder="Tìm gói phí…" />
                    </IconField>
                  </div>
                </template>
                <template #end>
                  <Button
                    v-if="auth.canEdit"
                    label="Thêm gói phí"
                    icon="pi pi-plus"
                    @click="openCreateFeePackage"
                  />
                </template>
              </Toolbar>

              <DataTable
                :value="filteredFeePackageRows"
                :loading="feePackageLoading"
                data-key="id"
                size="small"
                striped-rows
              >
                <template #empty>
                  <div class="py-6 text-center text-surface-500 text-sm">Chưa có gói phí nào.</div>
                </template>

                <Column field="name" header="Tên gói" sortable />
                <Column header="Số khoản thu" style="width: 8rem">
                  <template #body="{ data }">{{ data.items.length }}</template>
                </Column>
                <Column field="due_day_of_month" header="Hạn đóng" style="width: 8rem">
                  <template #body="{ data }">Ngày {{ data.due_day_of_month }}</template>
                </Column>
                <Column field="billing_timing_display" header="Thời điểm thu" style="width: 9rem" />
                <Column header="Trạng thái" style="width: 9rem">
                  <template #body="{ data }">
                    <Tag
                      :value="data.is_active ? 'Đang áp dụng' : 'Ngừng áp dụng'"
                      :severity="data.is_active ? 'success' : 'secondary'"
                    />
                  </template>
                </Column>
                <Column header="" style="width: 7rem">
                  <template #body="{ data }">
                    <div v-if="auth.canEdit" class="flex justify-end gap-1">
                      <Button
                        v-tooltip.top="'Sửa'"
                        icon="pi pi-pencil"
                        text
                        rounded
                        aria-label="Sửa"
                        @click="openEditFeePackage(data)"
                      />
                      <Button
                        v-tooltip.top="'Xóa'"
                        icon="pi pi-trash"
                        severity="danger"
                        text
                        rounded
                        aria-label="Xóa"
                        @click="confirmDeleteFeePackage(data)"
                      />
                    </div>
                  </template>
                </Column>
              </DataTable>
            </div>

            <div class="flex flex-col gap-4 pt-2 border-t border-surface-200 dark:border-surface-700">
              <Toolbar>
                <template #start>
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="font-medium">Học sinh đăng ký gói phí</span>
                    <IconField>
                      <InputIcon class="pi pi-search" />
                      <InputText v-model="subscriptionSearch" placeholder="Tìm học sinh, gói phí…" />
                    </IconField>
                  </div>
                </template>
                <template #end>
                  <Button
                    v-if="auth.canEdit"
                    label="Đăng ký"
                    icon="pi pi-plus"
                    @click="openCreateSubscription"
                  />
                </template>
              </Toolbar>

              <DataTable
                :value="filteredSubscriptionRows"
                :loading="subscriptionLoading"
                data-key="id"
                size="small"
                striped-rows
              >
                <template #empty>
                  <div class="py-6 text-center text-surface-500 text-sm">Chưa có học sinh nào đăng ký.</div>
                </template>

                <Column field="student_name" header="Học sinh" sortable />
                <Column field="fee_package_name" header="Gói phí" />
                <Column field="effective_from" header="Từ ngày" style="width: 8rem">
                  <template #body="{ data }">{{ formatDate(data.effective_from) }}</template>
                </Column>
                <Column field="effective_until" header="Đến ngày" style="width: 8rem">
                  <template #body="{ data }">{{ formatDate(data.effective_until) }}</template>
                </Column>
                <Column header="" style="width: 7rem">
                  <template #body="{ data }">
                    <div v-if="auth.canEdit" class="flex justify-end gap-1">
                      <Button
                        v-tooltip.top="'Sửa'"
                        icon="pi pi-pencil"
                        text
                        rounded
                        aria-label="Sửa"
                        @click="openEditSubscription(data)"
                      />
                      <Button
                        v-tooltip.top="'Hủy đăng ký'"
                        icon="pi pi-trash"
                        severity="danger"
                        text
                        rounded
                        aria-label="Hủy đăng ký"
                        @click="confirmDeleteSubscription(data)"
                      />
                    </div>
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </TabPanel>

        <!-- ===================== GIẢM TRỪ ===================== -->
        <TabPanel value="discounts">
          <div class="flex flex-col gap-4">
            <Toolbar>
              <template #start>
                <IconField>
                  <InputIcon class="pi pi-search" />
                  <InputText v-model="discountSearch" placeholder="Tìm học sinh, giảm trừ…" />
                </IconField>
              </template>
              <template #end>
                <Button
                  v-if="auth.canEdit"
                  label="Thêm giảm trừ"
                  icon="pi pi-plus"
                  @click="openCreateDiscount"
                />
              </template>
            </Toolbar>

            <DataTable :value="filteredDiscountRows" :loading="discountLoading" data-key="id" size="small" striped-rows>
              <template #empty>
                <div class="py-6 text-center text-surface-500 text-sm">Chưa có giảm trừ nào.</div>
              </template>

              <Column field="student_name" header="Học sinh" sortable />
              <Column field="name" header="Tên giảm trừ" />
              <Column header="Áp dụng cho" style="width: 10rem">
                <template #body="{ data }">{{ data.fee_item_name || "Toàn bộ hóa đơn" }}</template>
              </Column>
              <Column header="Giá trị" style="width: 8rem">
                <template #body="{ data }">
                  {{ data.discount_type === "percentage" ? `${data.value}%` : formatMoney(data.value) }}
                </template>
              </Column>
              <Column field="effective_from" header="Từ ngày" style="width: 8rem">
                <template #body="{ data }">{{ formatDate(data.effective_from) }}</template>
              </Column>
              <Column header="Trạng thái" style="width: 9rem">
                <template #body="{ data }">
                  <Tag
                    :value="data.is_active ? 'Đang áp dụng' : 'Ngừng áp dụng'"
                    :severity="data.is_active ? 'success' : 'secondary'"
                  />
                </template>
              </Column>
              <Column header="" style="width: 7rem">
                <template #body="{ data }">
                  <div v-if="auth.canEdit" class="flex justify-end gap-1">
                    <Button
                      v-tooltip.top="'Sửa'"
                      icon="pi pi-pencil"
                      text
                      rounded
                      aria-label="Sửa"
                      @click="openEditDiscount(data)"
                    />
                    <Button
                      v-tooltip.top="'Xóa'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      aria-label="Xóa"
                      @click="confirmDeleteDiscount(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <InvoiceGenerateDialog
      v-model:visible="generateVisible"
      :student-options="studentOptions"
      @generated="onGenerated"
    />

    <StudentBillingSummaryDialog
      v-model:visible="studentSummaryVisible"
      :student="selectedStudentForSummary"
      :fee-packages="feePackageRows"
    />

    <InvoicePaymentsDialog
      v-model:visible="paymentsVisible"
      :invoice="selectedInvoiceForPayments"
      :can-record="auth.canEdit"
      :mode="paymentDialogMode"
      :method-options="paymentMethodOptions"
      @recorded="onPaymentRecorded"
    />

    <StatusLegendDialog
      v-model:visible="invoiceStatusHelpVisible"
      title="Ý nghĩa các trạng thái hóa đơn"
      :items="INVOICE_STATUS_HELP"
    />

    <FeeItemFormDialog
      v-model:visible="feeItemFormVisible"
      :fee-item="selectedFeeItem"
      :meta="feeItemMeta"
      @saved="onFeeItemSaved"
    />

    <FeePackageFormDialog
      v-model:visible="feePackageFormVisible"
      :fee-package="selectedFeePackage"
      :meta="feePackageMeta"
      @saved="onFeePackageSaved"
    />

    <StudentFeePackageFormDialog
      v-model:visible="subscriptionFormVisible"
      :subscription="selectedSubscription"
      :student-options="studentOptions"
      :package-options="packageOptions"
      @saved="onSubscriptionSaved"
    />

    <StudentDiscountFormDialog
      v-model:visible="discountFormVisible"
      :discount="selectedDiscount"
      :student-options="studentOptions"
      :fee-item-options="feeItemOptions"
      @saved="onDiscountSaved"
    />
  </div>
</template>
