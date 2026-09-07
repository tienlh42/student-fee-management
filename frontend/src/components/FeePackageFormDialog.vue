<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import Textarea from "primevue/textarea";

import { errorMessage, fieldErrors } from "@/api/client";
import { feePackagesApi } from "@/api/billing";

const props = defineProps({
  visible: { type: Boolean, default: false },
  feePackage: { type: Object, default: null }, // null = tạo mới
  meta: { type: Object, required: true }, // { billing_timings, fee_items, default_house }
});
const emit = defineEmits(["update:visible", "saved"]);

function blankForm() {
  return {
    house: props.meta.default_house ?? null,
    name: "",
    description: "",
    due_day_of_month: 5,
    billing_timing: "prepaid",
    is_active: true,
    items: [],
  };
}

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const errors = ref({});

const isEdit = computed(() => props.feePackage !== null);
const title = computed(() => (isEdit.value ? "Sửa gói phí" : "Thêm gói phí"));

watch(
  () => props.visible,
  (open) => {
    if (!open) return;
    error.value = "";
    errors.value = {};
    Object.assign(form, blankForm());
    if (props.feePackage) {
      Object.assign(form, props.feePackage);
      form.items = props.feePackage.items.map((item) => ({
        fee_item: item.fee_item,
        amount: item.amount,
      }));
    }
  },
);

function addItemRow() {
  form.items.push({ fee_item: null, amount: null });
}

function removeItemRow(index) {
  form.items.splice(index, 1);
}

function buildPayload() {
  return {
    ...form,
    items: form.items.filter((item) => item.fee_item !== null),
  };
}

async function submit() {
  error.value = "";
  errors.value = {};
  saving.value = true;
  try {
    const payload = buildPayload();
    const saved = isEdit.value
      ? await feePackagesApi.update(props.feePackage.id, payload)
      : await feePackagesApi.create(payload);
    emit("saved", saved, isEdit.value);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không lưu được gói phí.");
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
    :style="{ width: '40rem' }"
    :breakpoints="{ '960px': '95vw' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="fee-package-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div class="flex flex-col gap-1">
        <label for="fp-name" class="text-sm font-medium">Tên gói *</label>
        <InputText id="fp-name" v-model="form.name" :invalid="!!errors.name" required autofocus />
        <small v-if="errors.name" class="text-red-500">{{ errors.name }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="fp-desc" class="text-sm font-medium">Mô tả</label>
        <Textarea id="fp-desc" v-model="form.description" rows="2" auto-resize />
      </div>

      <section class="grid grid-cols-2 gap-4">
        <div class="flex flex-col gap-1">
          <label for="fp-due" class="text-sm font-medium">Hạn đóng (ngày trong tháng)</label>
          <InputNumber id="fp-due" v-model="form.due_day_of_month" :min="1" :max="31" show-buttons />
        </div>

        <div class="flex flex-col gap-1">
          <label for="fp-timing" class="text-sm font-medium">Thời điểm thu</label>
          <Select
            id="fp-timing"
            v-model="form.billing_timing"
            :options="meta.billing_timings"
            option-label="label"
            option-value="value"
          />
        </div>
      </section>

      <div class="flex items-center gap-2">
        <Checkbox v-model="form.is_active" input-id="fp-active" binary />
        <label for="fp-active" class="text-sm">Đang áp dụng</label>
      </div>

      <section class="pt-3 border-t border-surface-200 dark:border-surface-700">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium">Khoản thu trong gói</span>
          <Button label="Thêm dòng" icon="pi pi-plus" size="small" text @click="addItemRow" />
        </div>
        <small v-if="errors.items" class="text-red-500 block mb-2">{{ errors.items }}</small>

        <div v-if="!form.items.length" class="text-sm text-surface-500">
          Chưa có khoản thu nào trong gói.
        </div>

        <div
          v-for="(item, index) in form.items"
          :key="index"
          class="flex items-center gap-2 mb-2"
        >
          <Select
            v-model="item.fee_item"
            :options="meta.fee_items"
            option-label="label"
            option-value="value"
            placeholder="Khoản thu"
            filter
            class="flex-1"
          />
          <InputNumber
            v-model="item.amount"
            placeholder="Mặc định"
            mode="decimal"
            :max-fraction-digits="0"
            class="w-40"
          />
          <Button
            icon="pi pi-trash"
            severity="danger"
            text
            rounded
            aria-label="Xóa dòng"
            @click="removeItemRow(index)"
          />
        </div>
      </section>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="emit('update:visible', false)" />
      <Button
        type="submit"
        form="fee-package-form"
        label="Lưu"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!form.name"
      />
    </template>
  </Dialog>
</template>
