<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage, fieldErrors } from "@/api/client";
import { housesApi } from "@/api/accounts";
import { useCloseGuard, useDirtyTracking } from "@/utils/dirty";

const props = defineProps({
  visible: { type: Boolean, default: false },
  house: { type: Object, default: null }, // null = tạo mới
});
const emit = defineEmits(["update:visible", "saved"]);

function blankForm() {
  return { name: "", address: "", inbound_email_slug: "" };
}

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const errors = ref({});
const { dirty, markClean } = useDirtyTracking(form);
const { guardedClose } = useCloseGuard();

const isEdit = computed(() => props.house !== null);
const title = computed(() => (isEdit.value ? "Sửa cơ sở" : "Thêm cơ sở"));

function cancel() {
  guardedClose(dirty.value, () => emit("update:visible", false));
}

watch(
  () => props.visible,
  (open) => {
    if (!open) return;
    error.value = "";
    errors.value = {};
    Object.assign(form, blankForm());
    if (props.house) Object.assign(form, props.house);
    markClean();
  },
);

async function submit() {
  error.value = "";
  errors.value = {};
  saving.value = true;
  try {
    const saved = isEdit.value
      ? await housesApi.update(props.house.id, form)
      : await housesApi.create(form);
    emit("saved", saved, isEdit.value);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không lưu được cơ sở.");
    errors.value = fieldErrors(err);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="title"
    :loading="saving"
    :dirty="dirty"
    :style="{ width: '30rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="house-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div class="flex flex-col gap-1">
        <label for="house-name" class="text-sm font-medium">Tên cơ sở *</label>
        <InputText id="house-name" v-model="form.name" :invalid="!!errors.name" required autofocus />
        <small v-if="errors.name" class="text-red-500">{{ errors.name }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="house-address" class="text-sm font-medium">Địa chỉ</label>
        <InputText id="house-address" v-model="form.address" :invalid="!!errors.address" />
        <small v-if="errors.address" class="text-red-500">{{ errors.address }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="house-slug" class="text-sm font-medium">Slug email nhận thư *</label>
        <InputText
          id="house-slug"
          v-model="form.inbound_email_slug"
          :invalid="!!errors.inbound_email_slug"
          required
        />
        <small class="text-surface-500">Dùng cho địa chỉ nhận mail/webhook riêng của cơ sở.</small>
        <small v-if="errors.inbound_email_slug" class="text-red-500">
          {{ errors.inbound_email_slug }}
        </small>
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="cancel" />
      <Button
        type="submit"
        form="house-form"
        label="Lưu"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!form.name || !form.inbound_email_slug"
      />
    </template>
  </AppDialog>
</template>
