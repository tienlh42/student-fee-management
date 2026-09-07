<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import Select from "primevue/select";

import { errorMessage, fieldErrors } from "@/api/client";
import { studentFeePackagesApi } from "@/api/billing";
import { fromIsoDate, toIsoDate } from "@/utils/date";

const props = defineProps({
  visible: { type: Boolean, default: false },
  subscription: { type: Object, default: null }, // null = tạo mới
  studentOptions: { type: Array, required: true },
  packageOptions: { type: Array, required: true },
});
const emit = defineEmits(["update:visible", "saved"]);

function blankForm() {
  return {
    student: null,
    fee_package: null,
    effective_from: new Date(),
    effective_until: null,
  };
}

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const errors = ref({});

const isEdit = computed(() => props.subscription !== null);
const title = computed(() => (isEdit.value ? "Sửa đăng ký gói phí" : "Đăng ký gói phí"));

watch(
  () => props.visible,
  (open) => {
    if (!open) return;
    error.value = "";
    errors.value = {};
    Object.assign(form, blankForm());
    if (props.subscription) {
      Object.assign(form, props.subscription);
      form.effective_from = fromIsoDate(props.subscription.effective_from);
      form.effective_until = fromIsoDate(props.subscription.effective_until);
    }
  },
);

function buildPayload() {
  return {
    ...form,
    effective_from: toIsoDate(form.effective_from),
    effective_until: toIsoDate(form.effective_until),
  };
}

async function submit() {
  error.value = "";
  errors.value = {};
  saving.value = true;
  try {
    const payload = buildPayload();
    const saved = isEdit.value
      ? await studentFeePackagesApi.update(props.subscription.id, payload)
      : await studentFeePackagesApi.create(payload);
    emit("saved", saved, isEdit.value);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không lưu được đăng ký gói phí.");
    errors.value = fieldErrors(err);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="title"
    modal
    :style="{ width: '30rem' }"
    :breakpoints="{ '960px': '95vw' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="student-fee-package-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div class="flex flex-col gap-1">
        <label for="sfp-student" class="text-sm font-medium">Học sinh *</label>
        <Select
          id="sfp-student"
          v-model="form.student"
          :options="studentOptions"
          option-label="label"
          option-value="value"
          placeholder="Chọn học sinh"
          filter
          :invalid="!!errors.student"
          :disabled="isEdit"
        />
        <small v-if="errors.student" class="text-red-500">{{ errors.student }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="sfp-package" class="text-sm font-medium">Gói phí *</label>
        <Select
          id="sfp-package"
          v-model="form.fee_package"
          :options="packageOptions"
          option-label="label"
          option-value="value"
          placeholder="Chọn gói phí"
          :invalid="!!errors.fee_package"
        />
        <small v-if="errors.fee_package" class="text-red-500">{{ errors.fee_package }}</small>
      </div>

      <section class="grid grid-cols-2 gap-4">
        <div class="flex flex-col gap-1">
          <label for="sfp-from" class="text-sm font-medium">Áp dụng từ *</label>
          <DatePicker id="sfp-from" v-model="form.effective_from" date-format="dd/mm/yy" show-icon />
        </div>

        <div class="flex flex-col gap-1">
          <label for="sfp-until" class="text-sm font-medium">Áp dụng đến</label>
          <DatePicker id="sfp-until" v-model="form.effective_until" date-format="dd/mm/yy" show-icon />
        </div>
      </section>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="emit('update:visible', false)" />
      <Button
        type="submit"
        form="student-fee-package-form"
        label="Lưu"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!form.student || !form.fee_package"
      />
    </template>
  </Dialog>
</template>
