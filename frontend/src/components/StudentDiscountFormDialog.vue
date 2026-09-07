<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import DatePicker from "primevue/datepicker";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";

import { errorMessage, fieldErrors } from "@/api/client";
import { studentDiscountsApi } from "@/api/billing";
import { fromIsoDate, toIsoDate } from "@/utils/date";

const props = defineProps({
  visible: { type: Boolean, default: false },
  discount: { type: Object, default: null }, // null = tạo mới
  studentOptions: { type: Array, required: true },
  feeItemOptions: { type: Array, required: true }, // [{value, label}], không bắt buộc chọn
});
const emit = defineEmits(["update:visible", "saved"]);

function blankForm() {
  return {
    student: null,
    fee_item: null,
    name: "",
    discount_type: "percentage",
    value: null,
    effective_from: new Date(),
    effective_until: null,
    is_active: true,
  };
}

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const errors = ref({});

const isEdit = computed(() => props.discount !== null);
const title = computed(() => (isEdit.value ? "Sửa giảm trừ" : "Thêm giảm trừ"));
const valueSuffix = computed(() => (form.discount_type === "percentage" ? " %" : " đ"));

watch(
  () => props.visible,
  (open) => {
    if (!open) return;
    error.value = "";
    errors.value = {};
    Object.assign(form, blankForm());
    if (props.discount) {
      Object.assign(form, props.discount);
      form.effective_from = fromIsoDate(props.discount.effective_from);
      form.effective_until = fromIsoDate(props.discount.effective_until);
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
      ? await studentDiscountsApi.update(props.discount.id, payload)
      : await studentDiscountsApi.create(payload);
    emit("saved", saved, isEdit.value);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không lưu được giảm trừ.");
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
    :style="{ width: '34rem' }"
    :breakpoints="{ '960px': '95vw' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="student-discount-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div class="flex flex-col gap-1">
        <label for="sd-student" class="text-sm font-medium">Học sinh *</label>
        <Select
          id="sd-student"
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
        <label for="sd-name" class="text-sm font-medium">Tên giảm trừ *</label>
        <InputText id="sd-name" v-model="form.name" :invalid="!!errors.name" required />
        <small v-if="errors.name" class="text-red-500">{{ errors.name }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="sd-fee-item" class="text-sm font-medium">Áp dụng cho khoản thu</label>
        <Select
          id="sd-fee-item"
          v-model="form.fee_item"
          :options="feeItemOptions"
          option-label="label"
          option-value="value"
          placeholder="Toàn bộ hóa đơn (bỏ trống)"
          show-clear
          filter
        />
      </div>

      <section class="grid grid-cols-2 gap-4">
        <div class="flex flex-col gap-1">
          <label for="sd-type" class="text-sm font-medium">Kiểu</label>
          <Select
            id="sd-type"
            v-model="form.discount_type"
            :options="[
              { value: 'percentage', label: 'Theo phần trăm' },
              { value: 'fixed_amount', label: 'Số tiền cố định' },
            ]"
            option-label="label"
            option-value="value"
          />
        </div>

        <div class="flex flex-col gap-1">
          <label for="sd-value" class="text-sm font-medium">Giá trị *</label>
          <InputNumber
            id="sd-value"
            v-model="form.value"
            :invalid="!!errors.value"
            mode="decimal"
            :min="0"
            :max-fraction-digits="0"
            :suffix="valueSuffix"
          />
          <small v-if="errors.value" class="text-red-500">{{ errors.value }}</small>
        </div>
      </section>

      <section class="grid grid-cols-2 gap-4">
        <div class="flex flex-col gap-1">
          <label for="sd-from" class="text-sm font-medium">Áp dụng từ *</label>
          <DatePicker id="sd-from" v-model="form.effective_from" date-format="dd/mm/yy" show-icon />
        </div>

        <div class="flex flex-col gap-1">
          <label for="sd-until" class="text-sm font-medium">Áp dụng đến</label>
          <DatePicker id="sd-until" v-model="form.effective_until" date-format="dd/mm/yy" show-icon />
        </div>
      </section>

      <div class="flex items-center gap-2">
        <Checkbox v-model="form.is_active" input-id="sd-active" binary />
        <label for="sd-active" class="text-sm">Đang áp dụng</label>
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="emit('update:visible', false)" />
      <Button
        type="submit"
        form="student-discount-form"
        label="Lưu"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!form.student || !form.name || !form.value"
      />
    </template>
  </Dialog>
</template>
