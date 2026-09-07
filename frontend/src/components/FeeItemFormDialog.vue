<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";

import { errorMessage, fieldErrors } from "@/api/client";
import { feeItemsApi } from "@/api/billing";

const props = defineProps({
  visible: { type: Boolean, default: false },
  feeItem: { type: Object, default: null }, // null = tạo mới
  meta: { type: Object, required: true }, // { categories, default_house }
});
const emit = defineEmits(["update:visible", "saved"]);

function blankForm() {
  return {
    house: props.meta.default_house ?? null,
    name: "",
    category: "other",
    default_amount: null,
    is_active: true,
  };
}

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const errors = ref({});

const isEdit = computed(() => props.feeItem !== null);
const title = computed(() => (isEdit.value ? "Sửa khoản thu" : "Thêm khoản thu"));

watch(
  () => props.visible,
  (open) => {
    if (!open) return;
    error.value = "";
    errors.value = {};
    Object.assign(form, blankForm());
    if (props.feeItem) Object.assign(form, props.feeItem);
  },
);

async function submit() {
  error.value = "";
  errors.value = {};
  saving.value = true;
  try {
    const saved = isEdit.value
      ? await feeItemsApi.update(props.feeItem.id, form)
      : await feeItemsApi.create(form);
    emit("saved", saved, isEdit.value);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không lưu được khoản thu.");
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
    <form id="fee-item-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div class="flex flex-col gap-1">
        <label for="fi-name" class="text-sm font-medium">Tên khoản thu *</label>
        <InputText id="fi-name" v-model="form.name" :invalid="!!errors.name" required autofocus />
        <small v-if="errors.name" class="text-red-500">{{ errors.name }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="fi-category" class="text-sm font-medium">Nhóm</label>
        <Select
          id="fi-category"
          v-model="form.category"
          :options="meta.categories"
          option-label="label"
          option-value="value"
        />
      </div>

      <div class="flex flex-col gap-1">
        <label for="fi-amount" class="text-sm font-medium">Số tiền mặc định *</label>
        <InputNumber
          id="fi-amount"
          v-model="form.default_amount"
          :invalid="!!errors.default_amount"
          mode="decimal"
          :min="0"
          :max-fraction-digits="0"
          suffix=" đ"
        />
        <small v-if="errors.default_amount" class="text-red-500">{{ errors.default_amount }}</small>
      </div>

      <div class="flex items-center gap-2">
        <Checkbox v-model="form.is_active" input-id="fi-active" binary />
        <label for="fi-active" class="text-sm">Đang áp dụng</label>
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="emit('update:visible', false)" />
      <Button
        type="submit"
        form="fee-item-form"
        label="Lưu"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!form.name || !form.default_amount"
      />
    </template>
  </Dialog>
</template>
