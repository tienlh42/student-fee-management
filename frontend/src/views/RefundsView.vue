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
import { refundsApi } from "@/api/payments";
import { formatDateTime } from "@/utils/date";
import { formatMoney } from "@/utils/money";

const toast = useToast();

const METHOD_SEVERITY = { bank_transfer: "info", cash: "success", credit: "warn" };

const meta = ref({ methods: [] });
const rows = ref([]);
const total = ref(0);
const loading = ref(false);
const filters = reactive({ search: "", method: null });
const paging = reactive({ page: 1, rows: 25 });

async function load() {
  loading.value = true;
  try {
    const page = await refundsApi.list({
      search: filters.search,
      method: filters.method,
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
    meta.value = await refundsApi.meta();
  } catch {
    meta.value = { methods: [] };
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
  () => filters.method,
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
            <InputText v-model="filters.search" placeholder="Tìm mã HĐ, tên học sinh, lý do…" />
          </IconField>

          <Select
            v-model="filters.method"
            :options="meta.methods"
            option-label="label"
            option-value="value"
            placeholder="Phương thức"
            show-clear
            class="w-44"
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
          Không có khoản hoàn tiền nào khớp bộ lọc.
        </div>
      </template>

      <Column field="refunded_at" header="Thời gian" style="width: 10rem">
        <template #body="{ data }">{{ formatDateTime(data.refunded_at) }}</template>
      </Column>

      <Column field="invoice_reference" header="Mã HĐ" style="width: 8rem" />

      <Column field="student_name" header="Học sinh" />

      <Column header="Số tiền hoàn" style="width: 9rem">
        <template #body="{ data }">{{ formatMoney(data.amount) }}</template>
      </Column>

      <Column header="Phương thức" style="width: 9rem">
        <template #body="{ data }">
          <Tag :value="data.method_display" :severity="METHOD_SEVERITY[data.method]" />
        </template>
      </Column>

      <Column header="Nghĩa vụ" style="width: 8rem">
        <template #body="{ data }">
          <Tag
            :value="data.invoice_status === 'void' ? 'Đã hủy' : 'Còn hiệu lực'"
            :severity="data.invoice_status === 'void' ? 'danger' : 'secondary'"
          />
        </template>
      </Column>

      <Column field="reason" header="Lý do" />

      <Column field="refunded_by_username" header="Người thực hiện" style="width: 9rem" />
    </DataTable>
  </div>
</template>
