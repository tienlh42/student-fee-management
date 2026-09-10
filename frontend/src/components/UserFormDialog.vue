<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import Select from "primevue/select";
import ToggleSwitch from "primevue/toggleswitch";

import AppDialog from "@/components/AppDialog.vue";
import { errorMessage, fieldErrors } from "@/api/client";
import { usersApi } from "@/api/accounts";
import { useCloseGuard, useDirtyTracking } from "@/utils/dirty";

const props = defineProps({
  visible: { type: Boolean, default: false },
  user: { type: Object, default: null }, // null = tạo mới
  houseOptions: { type: Array, required: true }, // [{value, label}]
  // Tài khoản đang sửa là chính người đang đăng nhập — backend luôn chặn tự
  // khóa/tự hạ quyền, ở đây chỉ vô hiệu hóa control cho rõ ràng hơn là để
  // người dùng bấm xong mới thấy lỗi.
  isSelf: { type: Boolean, default: false },
});
const emit = defineEmits(["update:visible", "saved"]);

const ROLE_OPTIONS = [
  { label: "Không", value: "" },
  { label: "Giáo viên", value: "teacher" },
  { label: "Phụ huynh", value: "guardian" },
];

function blankForm() {
  return {
    username: "",
    email: "",
    password: "",
    is_active: true,
    is_staff: false,
    is_superuser: false,
    role_kind: "",
    role_house: null,
    role_full_name: "",
  };
}

const form = reactive(blankForm());
const resetPassword = ref(false);
const saving = ref(false);
const error = ref("");
const errors = ref({});
const { dirty, markClean } = useDirtyTracking(form);
const { guardedClose } = useCloseGuard();

const isEdit = computed(() => props.user !== null);
const title = computed(() => (isEdit.value ? "Sửa tài khoản" : "Thêm tài khoản"));
const showPasswordField = computed(() => !isEdit.value || resetPassword.value);

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
    resetPassword.value = false;
    if (props.user) {
      form.username = props.user.username;
      form.email = props.user.email;
      form.is_active = props.user.is_active;
      form.is_staff = props.user.is_staff;
      form.is_superuser = props.user.is_superuser;
      form.role_kind = props.user.current_role?.kind ?? "";
      form.role_house = props.user.current_role?.house ?? null;
      form.role_full_name = props.user.person_full_name ?? "";
    }
    markClean();
  },
);

const canSubmit = computed(() => {
  if (!form.username) return false;
  if (!isEdit.value && !form.password) return false;
  if (form.role_kind === "teacher" && !form.role_house) return false;
  if (form.role_kind && !form.role_full_name) return false;
  return true;
});

async function submit() {
  error.value = "";
  errors.value = {};
  saving.value = true;
  try {
    const payload = { ...form };
    if (isEdit.value && !resetPassword.value) delete payload.password;
    if (!payload.role_kind) payload.role_house = null;

    const saved = isEdit.value
      ? await usersApi.update(props.user.id, payload)
      : await usersApi.create(payload);
    emit("saved", saved, isEdit.value);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không lưu được tài khoản.");
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
    :style="{ width: '34rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="user-form" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div class="flex flex-col gap-1">
        <label for="user-username" class="text-sm font-medium">Tên đăng nhập *</label>
        <InputText
          id="user-username"
          v-model="form.username"
          :invalid="!!errors.username"
          :disabled="isEdit"
          required
          autofocus
        />
        <small v-if="errors.username" class="text-red-500">{{ errors.username }}</small>
      </div>

      <div class="flex flex-col gap-1">
        <label for="user-email" class="text-sm font-medium">Email</label>
        <InputText id="user-email" v-model="form.email" :invalid="!!errors.email" type="email" />
        <small v-if="errors.email" class="text-red-500">{{ errors.email }}</small>
      </div>

      <div v-if="isEdit" class="flex items-center gap-2">
        <Checkbox v-model="resetPassword" input-id="user-reset-password" binary />
        <label for="user-reset-password" class="text-sm">Đặt mật khẩu mới</label>
      </div>

      <div v-if="showPasswordField" class="flex flex-col gap-1">
        <label for="user-password" class="text-sm font-medium">
          Mật khẩu {{ isEdit ? "mới" : "" }} *
        </label>
        <Password
          id="user-password"
          v-model="form.password"
          :invalid="!!errors.password"
          toggle-mask
          :feedback="false"
          input-class="w-full"
          fluid
        />
        <small v-if="errors.password" class="text-red-500">{{ errors.password }}</small>
      </div>

      <div class="flex flex-col gap-2 pt-2 border-t border-surface-200 dark:border-surface-700">
        <div class="flex items-center justify-between">
          <label for="user-active" class="text-sm">Đang hoạt động</label>
          <ToggleSwitch v-model="form.is_active" input-id="user-active" :disabled="isSelf" />
        </div>
        <div class="flex items-center justify-between">
          <div>
            <label for="user-staff" class="text-sm">Quản trị (is_staff)</label>
            <p class="text-xs text-surface-500">Thấy được dữ liệu ở mọi cơ sở.</p>
          </div>
          <ToggleSwitch v-model="form.is_staff" input-id="user-staff" />
        </div>
        <div class="flex items-center justify-between">
          <div>
            <label for="user-superuser" class="text-sm">Superuser</label>
            <p class="text-xs text-surface-500">Quản lý được Cơ sở &amp; Tài khoản (root).</p>
          </div>
          <ToggleSwitch v-model="form.is_superuser" input-id="user-superuser" :disabled="isSelf" />
        </div>
        <small v-if="isSelf" class="text-surface-500">
          Không thể tự khóa hoặc tự hạ quyền tài khoản đang đăng nhập.
        </small>
      </div>

      <div class="flex flex-col gap-3 pt-2 border-t border-surface-200 dark:border-surface-700">
        <span class="text-sm font-medium">Vai trò nhân thân</span>

        <div class="flex flex-col gap-1">
          <label for="user-role-kind" class="text-sm">Vai trò</label>
          <Select
            id="user-role-kind"
            v-model="form.role_kind"
            :options="ROLE_OPTIONS"
            option-label="label"
            option-value="value"
          />
        </div>

        <div v-if="form.role_kind" class="flex flex-col gap-1">
          <label for="user-role-full-name" class="text-sm">Họ tên *</label>
          <InputText
            id="user-role-full-name"
            v-model="form.role_full_name"
            :invalid="!!errors.role_full_name"
          />
        </div>

        <div v-if="form.role_kind === 'teacher'" class="flex flex-col gap-1">
          <label for="user-role-house" class="text-sm">Cơ sở *</label>
          <Select
            id="user-role-house"
            v-model="form.role_house"
            :options="houseOptions"
            option-label="label"
            option-value="value"
            :invalid="!!errors.role_house"
          />
        </div>
      </div>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="cancel" />
      <Button
        type="submit"
        form="user-form"
        label="Lưu"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!canSubmit"
      />
    </template>
  </AppDialog>
</template>
