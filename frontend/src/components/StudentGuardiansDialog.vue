<script setup>
import { ref, watch } from "vue";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Tag from "primevue/tag";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage } from "@/api/client";
import { guardiansApi, studentsApi } from "@/api/people";

const props = defineProps({
  visible: { type: Boolean, default: false },
  student: { type: Object, default: null },
  meta: { type: Object, required: true },
  canEdit: { type: Boolean, default: false },
});
const emit = defineEmits(["update:visible", "changed"]);

const toast = useToast();
const confirm = useConfirm();

const links = ref([]);
const loading = ref(false);
const saving = ref(false);

// Ô "thêm phụ huynh": chọn người đã có, hoặc gõ tên để tạo mới.
const guardianOptions = ref([]);
const draft = ref({ guardian: null, relationship_type: "mother", is_primary_contact: false });
const newGuardian = ref({ full_name: "", phone: "" });
const creatingNew = ref(false);

watch(
  () => props.visible,
  async (open) => {
    if (!open || !props.student) return;
    resetDraft();
    await Promise.all([loadLinks(), loadGuardianOptions()]);
  },
);

function resetDraft() {
  draft.value = { guardian: null, relationship_type: "mother", is_primary_contact: false };
  newGuardian.value = { full_name: "", phone: "" };
  creatingNew.value = false;
}

async function loadLinks() {
  loading.value = true;
  try {
    links.value = await studentsApi.guardians(props.student.id);
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    loading.value = false;
  }
}

async function loadGuardianOptions() {
  try {
    const page = await guardiansApi.list({ page_size: 200 });
    guardianOptions.value = (page.results ?? page).map((g) => ({
      value: g.id,
      label: g.phone ? `${g.full_name} · ${g.phone}` : g.full_name,
    }));
  } catch {
    guardianOptions.value = [];
  }
}

async function addLink() {
  saving.value = true;
  try {
    let guardianId = draft.value.guardian;

    if (creatingNew.value) {
      const created = await guardiansApi.create({
        person: { full_name: newGuardian.value.full_name, phone: newGuardian.value.phone },
      });
      guardianId = created.id;
    }

    await studentsApi.linkGuardian(props.student.id, {
      guardian: guardianId,
      relationship_type: draft.value.relationship_type,
      is_primary_contact: draft.value.is_primary_contact,
    });

    resetDraft();
    await Promise.all([loadLinks(), loadGuardianOptions()]);
    emit("changed");
    toast.add({ severity: "success", summary: "Đã gắn phụ huynh", life: 2500 });
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    saving.value = false;
  }
}

function removeLink(link) {
  confirm.require({
    message: `Gỡ ${link.guardian_name} khỏi học sinh này?`,
    header: "Xác nhận",
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Gỡ",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await studentsApi.unlinkGuardian(props.student.id, link.guardian);
        await loadLinks();
        emit("changed");
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
      }
    },
  });
}

const canSubmit = () =>
  creatingNew.value ? newGuardian.value.full_name.trim().length > 0 : draft.value.guardian !== null;
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="`Phụ huynh · ${student?.full_name ?? ''}`"
    :loading="loading"
    :style="{ width: '44rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <DataTable :value="links" size="small" data-key="id">
      <template #empty>
        <span class="text-surface-500 text-sm">Chưa gắn phụ huynh nào.</span>
      </template>

      <Column field="guardian_name" header="Họ tên" />
      <Column field="relationship_type_display" header="Quan hệ" />
      <Column field="guardian_phone" header="Điện thoại">
        <template #body="{ data }">{{ data.guardian_phone || "—" }}</template>
      </Column>
      <Column header="" style="width: 9rem">
        <template #body="{ data }">
          <div class="flex items-center justify-end gap-2">
            <Tag v-if="data.is_primary_contact" value="Liên hệ chính" severity="info" />
            <Button
              v-if="canEdit"
              icon="pi pi-times"
              severity="danger"
              text
              rounded
              aria-label="Gỡ phụ huynh"
              @click="removeLink(data)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <div v-if="canEdit" class="mt-5 pt-4 border-t border-surface-200 dark:border-surface-700">
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm font-medium">Gắn thêm phụ huynh</span>
        <Button
          :label="creatingNew ? 'Chọn người đã có' : 'Tạo phụ huynh mới'"
          size="small"
          text
          @click="creatingNew = !creatingNew"
        />
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <template v-if="creatingNew">
          <InputText v-model="newGuardian.full_name" placeholder="Họ và tên" />
          <InputText v-model="newGuardian.phone" placeholder="Điện thoại" />
        </template>
        <Select
          v-else
          v-model="draft.guardian"
          :options="guardianOptions"
          option-label="label"
          option-value="value"
          placeholder="Chọn phụ huynh"
          filter
          class="md:col-span-2"
        />

        <Select
          v-model="draft.relationship_type"
          :options="meta.relationships"
          option-label="label"
          option-value="value"
          placeholder="Quan hệ"
        />

        <div class="flex items-center gap-2">
          <Checkbox v-model="draft.is_primary_contact" input-id="primary" binary />
          <label for="primary" class="text-sm">Liên hệ chính</label>
        </div>
      </div>

      <Button
        class="mt-3"
        label="Gắn phụ huynh"
        icon="pi pi-plus"
        size="small"
        :loading="saving"
        :disabled="!canSubmit()"
        @click="addLink"
      />
    </div>

    <template #footer>
      <Button label="Đóng" severity="secondary" text @click="emit('update:visible', false)" />
    </template>
  </AppDialog>
</template>
