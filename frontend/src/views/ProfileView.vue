<script setup>
import { onMounted, reactive, ref } from "vue";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Card from "primevue/card";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import Select from "primevue/select";
import Tag from "primevue/tag";

import { errorMessage, fieldErrors } from "@/api/client";
import { accountsApi } from "@/api/accounts";
import { useAuthStore } from "@/stores/auth";
import { fromIsoDate, toIsoDate } from "@/utils/date";

const auth = useAuthStore();
const toast = useToast();

const DATE_FIELDS = ["date_of_birth", "id_issued_date"];

const GENDERS = [
  { label: "Nam", value: "male" },
  { label: "Nữ", value: "female" },
  { label: "Khác", value: "other" },
];

const VIA_SEVERITY = { admin: "danger", teacher: "info", guardian: "secondary" };

const loading = ref(true);
const saving = ref(false);
const loadError = ref("");
const errors = ref({});

const profile = ref(null);
const form = reactive({
  account_email: "",
  person: {
    full_name: "",
    gender: "",
    date_of_birth: null,
    place_of_birth: "",
    nationality: "",
    ethnicity: "",
    id_number: "",
    id_issued_date: null,
    id_issued_place: "",
    permanent_address: "",
    current_address: "",
    phone: "",
    email: "",
  },
});

const password = reactive({ current_password: "", new_password: "", confirm: "" });
const passwordErrors = ref({});
const changingPassword = ref(false);

function fill(data) {
  profile.value = data;
  form.account_email = data.account_email ?? "";

  if (data.person) {
    for (const key of Object.keys(form.person)) {
      form.person[key] = data.person[key] ?? "";
    }
    for (const field of DATE_FIELDS) {
      form.person[field] = fromIsoDate(data.person[field]);
    }
  }
}

async function load() {
  loading.value = true;
  try {
    fill(await accountsApi.profile());
  } catch (err) {
    loadError.value = errorMessage(err, "Không tải được hồ sơ.");
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  errors.value = {};
  try {
    const person = { ...form.person };
    for (const field of DATE_FIELDS) person[field] = toIsoDate(person[field]);

    fill(await accountsApi.updateProfile({ account_email: form.account_email, person }));
    // Tên hiển thị ở header lấy từ store -> phải nạp lại, không thì vẫn là tên cũ.
    await auth.fetchMe();
    toast.add({ severity: "success", summary: "Đã lưu hồ sơ", life: 2500 });
  } catch (err) {
    errors.value = { ...fieldErrors(err), ...fieldErrors({ payload: err?.payload?.person }) };
    toast.add({ severity: "error", summary: errorMessage(err, "Không lưu được hồ sơ."), life: 4000 });
  } finally {
    saving.value = false;
  }
}

async function submitPassword() {
  passwordErrors.value = {};

  if (password.new_password !== password.confirm) {
    passwordErrors.value = { confirm: "Hai lần nhập mật khẩu mới không khớp." };
    return;
  }

  changingPassword.value = true;
  try {
    await accountsApi.changePassword({
      current_password: password.current_password,
      new_password: password.new_password,
    });
    Object.assign(password, { current_password: "", new_password: "", confirm: "" });
    toast.add({ severity: "success", summary: "Đã đổi mật khẩu", life: 2500 });
  } catch (err) {
    passwordErrors.value = fieldErrors(err);
  } finally {
    changingPassword.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="max-w-3xl flex flex-col gap-4">
    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="!loading">
      <Card>
        <template #title><span class="text-base">Tài khoản</span></template>
        <template #content>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1">
              <label class="text-sm font-medium">Tên đăng nhập</label>
              <InputText :model-value="profile.username" disabled />
              <small class="text-surface-500">Không đổi được.</small>
            </div>

            <div class="flex flex-col gap-1">
              <label for="account_email" class="text-sm font-medium">Email tài khoản</label>
              <InputText
                id="account_email"
                v-model="form.account_email"
                type="email"
                :invalid="!!errors.account_email"
              />
              <small v-if="errors.account_email" class="text-red-500">
                {{ errors.account_email }}
              </small>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title><span class="text-base">Cơ sở</span></template>
        <template #content>
          <div v-if="profile.houses.length" class="flex flex-wrap gap-2">
            <Tag
              v-for="house in profile.houses"
              :key="house.id"
              :value="`${house.name} · ${house.via_display}`"
              :severity="VIA_SEVERITY[house.via]"
            />
          </div>
          <p v-else class="text-sm text-surface-500">Chưa gắn với cơ sở nào.</p>

          <p class="text-sm text-surface-500 mt-3">
            Bạn thuộc cơ sở nào là quyết định của tổ chức, không phải tùy chọn cá nhân —
            chỉ quản trị viên cấp cao mới đổi được.
          </p>
        </template>
      </Card>

      <Card>
        <template #title><span class="text-base">Thông tin cá nhân</span></template>
        <template #content>
          <Message
            v-if="!profile.person"
            severity="info"
            :closable="false"
            class="mb-4"
          >
            Tài khoản này chưa có hồ sơ nhân thân. Điền họ tên rồi lưu để tạo.
          </Message>

          <form id="profile-form" class="flex flex-col gap-5" @submit.prevent="save">
            <section class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1 md:col-span-2">
                <label for="full_name" class="text-sm font-medium">Họ và tên *</label>
                <InputText
                  id="full_name"
                  v-model="form.person.full_name"
                  :invalid="!!errors.full_name"
                  required
                />
                <small v-if="errors.full_name" class="text-red-500">{{ errors.full_name }}</small>
              </div>

              <div class="flex flex-col gap-1">
                <label for="gender" class="text-sm font-medium">Giới tính</label>
                <Select
                  id="gender"
                  v-model="form.person.gender"
                  :options="GENDERS"
                  option-label="label"
                  option-value="value"
                  placeholder="Chọn"
                  show-clear
                />
              </div>

              <div class="flex flex-col gap-1">
                <label for="dob" class="text-sm font-medium">Ngày sinh</label>
                <DatePicker
                  id="dob"
                  v-model="form.person.date_of_birth"
                  date-format="dd/mm/yy"
                  show-icon
                />
              </div>

              <div class="flex flex-col gap-1">
                <label for="phone" class="text-sm font-medium">Điện thoại</label>
                <InputText id="phone" v-model="form.person.phone" />
              </div>

              <div class="flex flex-col gap-1">
                <label for="contact_email" class="text-sm font-medium">Email liên hệ</label>
                <InputText
                  id="contact_email"
                  v-model="form.person.email"
                  type="email"
                  :invalid="!!errors.email"
                />
                <small v-if="errors.email" class="text-red-500">{{ errors.email }}</small>
              </div>

              <div class="flex flex-col gap-1">
                <label for="id_number" class="text-sm font-medium">Số CCCD/CMND</label>
                <InputText id="id_number" v-model="form.person.id_number" />
              </div>

              <div class="flex flex-col gap-1">
                <label for="id_issued_date" class="text-sm font-medium">Ngày cấp</label>
                <DatePicker
                  id="id_issued_date"
                  v-model="form.person.id_issued_date"
                  date-format="dd/mm/yy"
                  show-icon
                />
              </div>

              <div class="flex flex-col gap-1 md:col-span-2">
                <label for="id_issued_place" class="text-sm font-medium">Nơi cấp</label>
                <InputText id="id_issued_place" v-model="form.person.id_issued_place" />
              </div>

              <div class="flex flex-col gap-1 md:col-span-2">
                <label for="permanent_address" class="text-sm font-medium">
                  Hộ khẩu thường trú
                </label>
                <InputText id="permanent_address" v-model="form.person.permanent_address" />
              </div>

              <div class="flex flex-col gap-1 md:col-span-2">
                <label for="current_address" class="text-sm font-medium">Chỗ ở hiện tại</label>
                <InputText id="current_address" v-model="form.person.current_address" />
              </div>
            </section>

            <div>
              <Button
                type="submit"
                label="Lưu thay đổi"
                icon="pi pi-check"
                :loading="saving"
                :disabled="!form.person.full_name"
              />
            </div>
          </form>
        </template>
      </Card>

      <Card>
        <template #title><span class="text-base">Đổi mật khẩu</span></template>
        <template #content>
          <form class="flex flex-col gap-4 max-w-sm" @submit.prevent="submitPassword">
            <div class="flex flex-col gap-1">
              <label for="current_password" class="text-sm font-medium">Mật khẩu hiện tại</label>
              <Password
                id="current_password"
                v-model="password.current_password"
                :feedback="false"
                toggle-mask
                autocomplete="current-password"
                class="w-full"
                input-class="w-full"
                :invalid="!!passwordErrors.current_password"
              />
              <small v-if="passwordErrors.current_password" class="text-red-500">
                {{ passwordErrors.current_password }}
              </small>
            </div>

            <div class="flex flex-col gap-1">
              <label for="new_password" class="text-sm font-medium">Mật khẩu mới</label>
              <Password
                id="new_password"
                v-model="password.new_password"
                toggle-mask
                autocomplete="new-password"
                class="w-full"
                input-class="w-full"
                :invalid="!!passwordErrors.new_password"
                prompt-label="Nhập mật khẩu mới"
                weak-label="Yếu"
                medium-label="Trung bình"
                strong-label="Mạnh"
              />
              <small v-if="passwordErrors.new_password" class="text-red-500">
                {{ passwordErrors.new_password }}
              </small>
            </div>

            <div class="flex flex-col gap-1">
              <label for="confirm" class="text-sm font-medium">Nhập lại mật khẩu mới</label>
              <Password
                id="confirm"
                v-model="password.confirm"
                :feedback="false"
                toggle-mask
                autocomplete="new-password"
                class="w-full"
                input-class="w-full"
                :invalid="!!passwordErrors.confirm"
              />
              <small v-if="passwordErrors.confirm" class="text-red-500">
                {{ passwordErrors.confirm }}
              </small>
            </div>

            <div>
              <Button
                type="submit"
                label="Đổi mật khẩu"
                icon="pi pi-key"
                severity="secondary"
                :loading="changingPassword"
                :disabled="!password.current_password || !password.new_password"
              />
            </div>
          </form>
        </template>
      </Card>
    </template>
  </div>
</template>
