<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Column from "primevue/column";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Toolbar from "primevue/toolbar";

import { errorMessage } from "@/api/client";
import { studentsApi } from "@/api/people";
import AppDataTable from "@/components/AppDataTable.vue";
import StatusLegendDialog from "@/components/StatusLegendDialog.vue";
import StatusTag from "@/components/StatusTag.vue";
import StudentFormDialog from "@/components/StudentFormDialog.vue";
import StudentGuardiansDialog from "@/components/StudentGuardiansDialog.vue";
import { useAuthStore } from "@/stores/auth";
import { useHouseScopeStore } from "@/stores/houseScope";
import { formatDate } from "@/utils/date";
import { formatMoney } from "@/utils/money";

const auth = useAuthStore();
const houseScope = useHouseScopeStore();
const toast = useToast();
const confirm = useConfirm();

const STATUS_SEVERITY = {
  active: "success",
  paused: "warn",
  graduated: "info",
  withdrawn: "danger",
};

const STUDENT_STATUS_HELP = [
  {
    value: "active",
    label: "Đang học",
    severity: STATUS_SEVERITY.active,
    description:
      "Học sinh đang theo học bình thường. Chỉ học sinh ở trạng thái này mới được đưa vào khi sinh hóa đơn hàng loạt theo kỳ.",
  },
  {
    value: "paused",
    label: "Tạm nghỉ",
    severity: STATUS_SEVERITY.paused,
    description: "Tạm nghỉ học trong một khoảng thời gian, không bị tính vào lần sinh hóa đơn tiếp theo.",
  },
  {
    value: "graduated",
    label: "Đã tốt nghiệp",
    severity: STATUS_SEVERITY.graduated,
    description: "Đã hoàn thành chương trình học, không còn sinh hóa đơn mới.",
  },
  {
    value: "withdrawn",
    label: "Đã nghỉ",
    severity: STATUS_SEVERITY.withdrawn,
    description:
      "Đã thôi học. Học sinh không bị xóa khỏi hệ thống (hóa đơn cũ vẫn cần giữ lại) — chỉ đổi sang trạng thái này.",
  },
];
const statusHelpVisible = ref(false);

const rows = ref([]);
const total = ref(0);
const loading = ref(false);
const meta = ref({ statuses: [], genders: [], relationships: [], class_grades: [], houses: [] });

const filters = reactive({ search: "", status: null, class_grade: null });
const paging = reactive({ page: 1, rows: 10 });

const formVisible = ref(false);
const guardiansVisible = ref(false);
const selected = ref(null);

const classGradeOptions = computed(() =>
  meta.value.class_grades.map((grade) => ({ label: grade, value: grade })),
);

async function load() {
  loading.value = true;
  try {
    const page = await studentsApi.list({
      search: filters.search,
      status: filters.status,
      class_grade: filters.class_grade,
      house: houseScope.houseId,
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
    meta.value = await studentsApi.meta();
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  }
}

// Gõ tới đâu lọc tới đó, nhưng chỉ gọi API sau khi ngừng gõ 300ms.
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

watch([() => filters.status, () => filters.class_grade, () => houseScope.houseId], () => {
  paging.page = 1;
  load();
});

function onPage(event) {
  paging.page = event.page + 1;
  paging.rows = event.rows;
  load();
}

function openCreate() {
  selected.value = null;
  formVisible.value = true;
}

function openEdit(student) {
  selected.value = student;
  formVisible.value = true;
}

function openGuardians(student) {
  selected.value = student;
  guardiansVisible.value = true;
}

async function onSaved(_student, wasEdit) {
  toast.add({
    severity: "success",
    summary: wasEdit ? "Đã cập nhật học sinh" : "Đã thêm học sinh",
    life: 2500,
  });
  await Promise.all([load(), loadMeta()]);
}

function confirmDelete(student) {
  confirm.require({
    header: "Xóa học sinh",
    message: `Xóa ${student.full_name}? Thao tác này không hoàn tác được.`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await studentsApi.remove(student.id);
        toast.add({ severity: "success", summary: "Đã xóa học sinh", life: 2500 });
        await load();
      } catch (err) {
        // Student bị PROTECT bởi Invoice — báo rõ thay vì để 500 im lặng.
        toast.add({
          severity: "error",
          summary: errorMessage(err, "Không xóa được — học sinh đã có hóa đơn."),
          life: 5000,
        });
      }
    },
  });
}

function primaryGuardian(student) {
  return student.guardians.find((g) => g.is_primary_contact) ?? student.guardians[0] ?? null;
}

onMounted(async () => {
  await loadMeta();
  await load();
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <Toolbar>
      <template #start>
        <div class="flex flex-wrap items-center gap-2">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="filters.search" placeholder="Tìm tên, số điện thoại…" />
          </IconField>

          <Select
            v-model="filters.status"
            :options="meta.statuses"
            option-label="label"
            option-value="value"
            placeholder="Trạng thái"
            show-clear
            class="w-44"
          />

          <Select
            v-model="filters.class_grade"
            :options="classGradeOptions"
            option-label="label"
            option-value="value"
            placeholder="Lớp"
            show-clear
            class="w-36"
          />
        </div>
      </template>

      <template #end>
        <Button v-if="auth.canEdit" label="Thêm học sinh" icon="pi pi-plus" @click="openCreate" />
      </template>
    </Toolbar>

    <AppDataTable
      :value="rows"
      :loading="loading"
      storage-key="students"
      data-key="id"
      lazy
      paginator
      :rows="paging.rows"
      :total-records="total"
      :rows-per-page-options="[10, 25, 50, 100]"
      :first="(paging.page - 1) * paging.rows"
      @page="onPage"
    >
      <template #empty>
        <div class="flex flex-col items-center gap-2 py-10 text-surface-400 dark:text-surface-500">
          <i class="pi pi-users text-3xl" />
          <span class="text-sm">Không có học sinh nào khớp bộ lọc.</span>
        </div>
      </template>

      <Column field="full_name" header="Họ và tên" sortable>
        <template #body="{ data }">
          <div class="font-medium">{{ data.full_name }}</div>
          <div class="text-xs text-surface-500">{{ data.phone || "—" }}</div>
        </template>
      </Column>

      <Column field="class_grade" header="Lớp" style="width: 7rem">
        <template #body="{ data }">{{ data.class_grade || "—" }}</template>
      </Column>

      <Column header="Phụ huynh">
        <template #body="{ data }">
          <template v-if="primaryGuardian(data)">
            <div>{{ primaryGuardian(data).full_name }}</div>
            <div class="text-xs text-surface-500">
              {{ primaryGuardian(data).relationship_type_display }}
              <template v-if="primaryGuardian(data).phone">
                · {{ primaryGuardian(data).phone }}
              </template>
              <template v-if="data.guardians.length > 1">
                (+{{ data.guardians.length - 1 }})
              </template>
            </div>
          </template>
          <span v-else class="text-surface-400 text-sm">Chưa có</span>
        </template>
      </Column>

      <Column field="enrolled_date" header="Nhập học" style="width: 8rem">
        <template #body="{ data }">{{ formatDate(data.enrolled_date) }}</template>
      </Column>

      <Column header="Số dư credit" style="width: 9rem">
        <template #body="{ data }">
          <span v-if="Number(data.credit_balance) > 0" class="text-green-600 font-medium">
            {{ formatMoney(data.credit_balance) }}
          </span>
          <span v-else class="text-surface-400">—</span>
        </template>
      </Column>

      <Column field="status" style="width: 9rem">
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
          <StatusTag :value="data.status_display" :severity="STATUS_SEVERITY[data.status]" />
        </template>
      </Column>

      <Column header="" style="width: 10rem">
        <template #body="{ data }">
          <div class="flex justify-end gap-1">
            <Button
              v-tooltip.top="'Phụ huynh'"
              icon="pi pi-users"
              text
              rounded
              aria-label="Phụ huynh"
              @click="openGuardians(data)"
            />
            <Button
              v-if="auth.canEdit"
              v-tooltip.top="'Sửa'"
              icon="pi pi-pencil"
              text
              rounded
              aria-label="Sửa"
              @click="openEdit(data)"
            />
            <Button
              v-if="auth.canEdit"
              v-tooltip.top="'Xóa'"
              icon="pi pi-trash"
              severity="danger"
              text
              rounded
              aria-label="Xóa"
              @click="confirmDelete(data)"
            />
          </div>
        </template>
      </Column>
    </AppDataTable>

    <StudentFormDialog
      v-model:visible="formVisible"
      :student="selected"
      :meta="meta"
      @saved="onSaved"
    />

    <StudentGuardiansDialog
      v-model:visible="guardiansVisible"
      :student="selected"
      :meta="meta"
      :can-edit="auth.canEdit"
      @changed="load"
    />

    <StatusLegendDialog
      v-model:visible="statusHelpVisible"
      title="Ý nghĩa các trạng thái học sinh"
      :items="STUDENT_STATUS_HELP"
    />
  </div>
</template>
