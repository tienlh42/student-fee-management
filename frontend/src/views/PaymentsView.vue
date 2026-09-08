<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import { useToast } from "primevue/usetoast";

import Column from "primevue/column";
import DataTable from "primevue/datatable";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Tag from "primevue/tag";
import Toolbar from "primevue/toolbar";

import { errorMessage } from "@/api/client";
import { paymentsApi } from "@/api/payments";
import { formatDateTime } from "@/utils/date";
import { formatMoney } from "@/utils/money";

const toast = useToast();

const MATCHED_BY_SEVERITY = { auto: "info", manual: "secondary" };

const meta = ref({ payment_methods: [], matched_by: [] });
const rows = ref([]);
const total = ref(0);
const loading = ref(false);
const filters = reactive({ search: "", payment_method: null, matched_by: null });
const paging = reactive({ page: 1, rows: 25 });

async function load() {
  loading.value = true;
  try {
    const page = await paymentsApi.list({
      search: filters.search,
      payment_method: filters.payment_method,
      matched_by: filters.matched_by,
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
    meta.value = await paymentsApi.meta();
  } catch {
    meta.value = { payment_methods: [], matched_by: [] };
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
watch([() => filters.payment_method, () => filters.matched_by], () => {
  paging.page = 1;
  load();
});

function onPage(event) {
  paging.page = event.page + 1;
  paging.rows = event.rows;
  load();
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
            <InputText v-model="filters.search" placeholder="Tìm mã HĐ, tên học sinh, ghi chú…" />
          </IconField>

          <Select
            v-model="filters.payment_method"
            :options="meta.payment_methods"
            option-label="label"
            option-value="value"
            placeholder="Hình thức"
            show-clear
            class="w-40"
          />

          <Select
            v-model="filters.matched_by"
            :options="meta.matched_by"
            option-label="label"
            option-value="value"
            placeholder="Cách khớp"
            show-clear
            class="w-40"
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
          Không có thanh toán nào khớp bộ lọc.
        </div>
      </template>

      <Column field="created_at" header="Thời gian" style="width: 10rem">
        <template #body="{ data }">{{ formatDateTime(data.created_at) }}</template>
      </Column>

      <Column field="invoice_reference" header="Mã HĐ" style="width: 8rem" />

      <Column field="student_name" header="Học sinh" />

      <Column header="Số tiền" style="width: 9rem">
        <template #body="{ data }">{{ formatMoney(data.amount_applied) }}</template>
      </Column>

      <Column field="payment_method_display" header="Hình thức" style="width: 9rem" />

      <Column header="Cách khớp" style="width: 8rem">
        <template #body="{ data }">
          <Tag :value="data.matched_by_display" :severity="MATCHED_BY_SEVERITY[data.matched_by]" />
        </template>
      </Column>

      <Column field="recorded_by_username" header="Người thu" style="width: 8rem" />

      <Column field="note" header="Ghi chú" />
    </DataTable>
  </div>
</template>
