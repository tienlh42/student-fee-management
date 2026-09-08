<script setup>
import { reactive, ref, watch } from "vue";

import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import Message from "primevue/message";
import Select from "primevue/select";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage } from "@/api/client";
import { invoicesApi } from "@/api/billing";
import { toIsoDate } from "@/utils/date";
import { useCloseGuard, useDirtyTracking } from "@/utils/dirty";

const props = defineProps({
  visible: { type: Boolean, default: false },
  studentOptions: { type: Array, required: true },
});
const emit = defineEmits(["update:visible", "generated"]);

const form = reactive({ period: new Date(), student: null });
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
    if (!open) return;
    error.value = "";
    form.period = new Date();
    form.student = null;
    markClean();
  },
);

async function submit() {
  error.value = "";
  saving.value = true;
  try {
    const period = toIsoDate(form.period).slice(0, 7); // YYYY-MM
    const result = await invoicesApi.generate({ period, student: form.student ?? undefined });
    emit("generated", result);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không sinh được hóa đơn.");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppDialog
    :visible="visible"
    header="Sinh hóa đơn theo kỳ"
    :loading="saving"
    :dirty="dirty"
    :style="{ width: '26rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="invoice-generate-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <p class="text-sm text-surface-500">
        Sinh hóa đơn nháp cho toàn bộ học sinh đang học trong cơ sở của bạn. Đã có hóa đơn
        của kỳ này thì bỏ qua, không tạo trùng.
      </p>

      <div class="flex flex-col gap-1">
        <label for="gen-period" class="text-sm font-medium">Kỳ *</label>
        <DatePicker
          id="gen-period"
          v-model="form.period"
          view="month"
          date-format="mm/yy"
          show-icon
        />
      </div>

      <div class="flex flex-col gap-1">
        <label for="gen-student" class="text-sm font-medium">Chỉ một học sinh (tùy chọn)</label>
        <Select
          id="gen-student"
          v-model="form.student"
          :options="studentOptions"
          option-label="label"
          option-value="value"
          placeholder="Toàn bộ học sinh"
          show-clear
          filter
        />
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="cancel" />
      <Button
        type="submit"
        form="invoice-generate-form"
        label="Sinh hóa đơn"
        icon="pi pi-file-plus"
        :loading="saving"
      />
    </template>
  </AppDialog>
</template>
