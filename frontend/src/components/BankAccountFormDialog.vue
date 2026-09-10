<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage, fieldErrors } from "@/api/client";
import { bankAccountsApi } from "@/api/payments";
import { useCloseGuard, useDirtyTracking } from "@/utils/dirty";

const props = defineProps({
  visible: { type: Boolean, default: false },
  bankAccount: { type: Object, default: null }, // null = tạo mới
  houseOptions: { type: Array, required: true }, // [{value, label}]
});
const emit = defineEmits(["update:visible", "saved"]);

const bankOptions = ref([]);

function blankForm() {
  return { house: null, bank_code: null, account_holder_name: "", account_number: "" };
}

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const errors = ref({});
const { dirty, markClean } = useDirtyTracking(form);
const { guardedClose } = useCloseGuard();

const revealedNumber = ref("");
const revealing = ref(false);

const isEdit = computed(() => props.bankAccount !== null);
const title = computed(() => (isEdit.value ? "Sửa tài khoản ngân hàng" : "Thêm tài khoản ngân hàng"));

function cancel() {
  guardedClose(dirty.value, () => emit("update:visible", false));
}

watch(
  () => props.visible,
  (open) => {
    if (!open) return;
    error.value = "";
    errors.value = {};
    revealedNumber.value = "";
    Object.assign(form, blankForm());
    if (props.bankAccount) Object.assign(form, { ...props.bankAccount, account_number: "" });
    markClean();
  },
);

onMounted(async () => {
  try {
    const meta = await bankAccountsApi.meta();
    bankOptions.value = meta.banks;
  } catch {
    bankOptions.value = [];
  }
});

async function reveal() {
  revealing.value = true;
  try {
    const { account_number } = await bankAccountsApi.reveal(props.bankAccount.id);
    revealedNumber.value = account_number;
  } catch (err) {
    error.value = errorMessage(err, "Không xem được số tài khoản.");
  } finally {
    revealing.value = false;
  }
}

async function submit() {
  error.value = "";
  errors.value = {};
  saving.value = true;
  try {
    const payload = { ...form };
    if (!payload.account_number) delete payload.account_number;
    const saved = isEdit.value
      ? await bankAccountsApi.update(props.bankAccount.id, payload)
      : await bankAccountsApi.create(payload);
    emit("saved", saved, isEdit.value);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không lưu được tài khoản ngân hàng.");
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
    <form id="bank-account-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div class="flex flex-col gap-1">
        <label for="bank-account-house" class="text-sm font-medium">Cơ sở *</label>
        <Select
          id="bank-account-house"
          v-model="form.house"
          :options="houseOptions"
          option-label="label"
          option-value="value"
          :invalid="!!errors.house"
          :disabled="isEdit"
        />
        <small v-if="errors.house" class="text-red-500">{{ errors.house }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="bank-account-bank" class="text-sm font-medium">Ngân hàng *</label>
        <Select
          id="bank-account-bank"
          v-model="form.bank_code"
          :options="bankOptions"
          option-label="label"
          option-value="value"
          filter
          :invalid="!!errors.bank_code"
        />
        <small v-if="errors.bank_code" class="text-red-500">{{ errors.bank_code }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="bank-account-holder" class="text-sm font-medium">Chủ tài khoản *</label>
        <InputText
          id="bank-account-holder"
          v-model="form.account_holder_name"
          :invalid="!!errors.account_holder_name"
          required
        />
        <small v-if="errors.account_holder_name" class="text-red-500">
          {{ errors.account_holder_name }}
        </small>
      </div>

      <div v-if="isEdit" class="flex flex-col gap-1">
        <label class="text-sm font-medium">Số tài khoản hiện tại</label>
        <div class="flex items-center gap-2">
          <span class="text-sm">
            {{ revealedNumber || `****${bankAccount.account_number_last4}` }}
          </span>
          <Button
            v-if="!revealedNumber"
            v-tooltip.top="'Hiện số đầy đủ'"
            icon="pi pi-eye"
            text
            rounded
            size="small"
            :loading="revealing"
            aria-label="Hiện số đầy đủ"
            @click="reveal"
          />
        </div>
      </div>

      <div class="flex flex-col gap-1">
        <label for="bank-account-number" class="text-sm font-medium">
          {{ isEdit ? "Đổi số tài khoản" : "Số tài khoản *" }}
        </label>
        <InputText
          id="bank-account-number"
          v-model="form.account_number"
          :invalid="!!errors.account_number"
          :placeholder="isEdit ? 'Để trống nếu không đổi số tài khoản' : ''"
          :required="!isEdit"
          autocomplete="off"
        />
        <small v-if="errors.account_number" class="text-red-500">{{ errors.account_number }}</small>
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="cancel" />
      <Button
        type="submit"
        form="bank-account-form"
        label="Lưu"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!form.house || !form.bank_code || !form.account_holder_name || (!isEdit && !form.account_number)"
      />
    </template>
  </AppDialog>
</template>
