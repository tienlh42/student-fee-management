<script setup>
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";

import BrandLogo from "@/components/BrandLogo.vue";
import { errorMessage, fieldErrors } from "@/api/client";
import { accountsApi } from "@/api/accounts";

const router = useRouter();
const toast = useToast();

// step 1 = nhập username/email để nhận OTP; step 2 = nhập OTP + mật khẩu mới.
const step = ref(1);

const lookup = ref({ username: "", email: "" });
const lookupError = ref("");
const requesting = ref(false);
const resending = ref(false);

const reset = ref({ code: "", new_password: "", confirm: "" });
const resetErrors = ref({});
const confirming = ref(false);

async function requestOtp() {
  lookupError.value = "";
  requesting.value = true;
  try {
    await accountsApi.requestPasswordReset({
      username: lookup.value.username.trim(),
      email: lookup.value.email.trim(),
    });
    step.value = 2;
    toast.add({ severity: "success", summary: "Đã gửi mã OTP tới email.", life: 3000 });
  } catch (err) {
    lookupError.value = errorMessage(err, "Không gửi được mã OTP.");
  } finally {
    requesting.value = false;
  }
}

async function resend() {
  resending.value = true;
  try {
    await accountsApi.requestPasswordReset({
      username: lookup.value.username.trim(),
      email: lookup.value.email.trim(),
    });
    toast.add({ severity: "success", summary: "Đã gửi lại mã OTP.", life: 3000 });
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err, "Không gửi lại được mã."), life: 4000 });
  } finally {
    resending.value = false;
  }
}

async function confirmReset() {
  resetErrors.value = {};
  if (reset.value.new_password !== reset.value.confirm) {
    resetErrors.value = { confirm: "Hai lần nhập mật khẩu mới không khớp." };
    return;
  }

  confirming.value = true;
  try {
    await accountsApi.confirmPasswordReset({
      username: lookup.value.username.trim(),
      email: lookup.value.email.trim(),
      code: reset.value.code.trim(),
      new_password: reset.value.new_password,
    });
    toast.add({ severity: "success", summary: "Đã đặt lại mật khẩu, mời đăng nhập.", life: 3000 });
    router.replace({ name: "login" });
  } catch (err) {
    resetErrors.value = fieldErrors(err);
  } finally {
    confirming.value = false;
  }
}

function backToStep1() {
  step.value = 1;
  reset.value = { code: "", new_password: "", confirm: "" };
  resetErrors.value = {};
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-100 dark:bg-surface-950 p-4">
    <Card class="w-full max-w-sm">
      <template #title>
        <div class="text-center">
          <BrandLogo variant="red" class="w-16 h-16 mx-auto mb-2" />
          <div class="text-xl font-display font-bold">EduFi</div>
          <div class="text-sm font-normal text-surface-500 mt-1">
            {{ step === 1 ? "Quên mật khẩu" : "Nhập mã OTP & mật khẩu mới" }}
          </div>
        </div>
      </template>

      <template #content>
        <form v-if="step === 1" class="flex flex-col gap-4" @submit.prevent="requestOtp">
          <Message v-if="lookupError" severity="error" :closable="false">{{ lookupError }}</Message>
          <p class="text-sm text-surface-500">
            Nhập tên đăng nhập và email đã đăng ký, hệ thống sẽ gửi mã OTP qua email để đặt lại
            mật khẩu.
          </p>

          <div class="flex flex-col gap-1">
            <label for="fp-username" class="text-sm font-medium">Tên đăng nhập</label>
            <InputText
              id="fp-username"
              v-model="lookup.username"
              autocomplete="username"
              autofocus
              required
            />
          </div>

          <div class="flex flex-col gap-1">
            <label for="fp-email" class="text-sm font-medium">Email (Gmail)</label>
            <InputText
              id="fp-email"
              v-model="lookup.email"
              type="email"
              autocomplete="email"
              required
            />
          </div>

          <Button
            type="submit"
            label="Gửi mã OTP"
            icon="pi pi-send"
            :loading="requesting"
            :disabled="!lookup.username || !lookup.email"
          />

          <RouterLink to="/login" class="text-sm text-center text-surface-500 hover:underline">
            Quay lại đăng nhập
          </RouterLink>
        </form>

        <form v-else class="flex flex-col gap-4" @submit.prevent="confirmReset">
          <Message severity="info" :closable="false">
            Đã gửi mã OTP tới {{ lookup.email }}. Mã có hiệu lực trong 5 phút.
          </Message>
          <Message v-if="resetErrors.non_field_errors" severity="error" :closable="false">
            {{ resetErrors.non_field_errors }}
          </Message>

          <div class="flex flex-col gap-1">
            <label for="fp-code" class="text-sm font-medium">Mã OTP</label>
            <InputText
              id="fp-code"
              v-model="reset.code"
              inputmode="numeric"
              maxlength="6"
              autofocus
              required
              :invalid="!!resetErrors.code"
            />
            <small v-if="resetErrors.code" class="text-red-500">{{ resetErrors.code }}</small>
          </div>

          <div class="flex flex-col gap-1">
            <label for="fp-new-password" class="text-sm font-medium">Mật khẩu mới</label>
            <Password
              id="fp-new-password"
              v-model="reset.new_password"
              toggle-mask
              autocomplete="new-password"
              class="w-full"
              input-class="w-full"
              :invalid="!!resetErrors.new_password"
              prompt-label="Nhập mật khẩu mới"
              weak-label="Yếu"
              medium-label="Trung bình"
              strong-label="Mạnh"
              required
            />
            <small v-if="resetErrors.new_password" class="text-red-500">
              {{ resetErrors.new_password }}
            </small>
          </div>

          <div class="flex flex-col gap-1">
            <label for="fp-confirm" class="text-sm font-medium">Nhập lại mật khẩu mới</label>
            <Password
              id="fp-confirm"
              v-model="reset.confirm"
              :feedback="false"
              toggle-mask
              autocomplete="new-password"
              class="w-full"
              input-class="w-full"
              :invalid="!!resetErrors.confirm"
              required
            />
            <small v-if="resetErrors.confirm" class="text-red-500">{{ resetErrors.confirm }}</small>
          </div>

          <Button
            type="submit"
            label="Đặt lại mật khẩu"
            icon="pi pi-check"
            :loading="confirming"
            :disabled="!reset.code || !reset.new_password"
          />

          <div class="flex justify-between text-sm">
            <button
              type="button"
              class="text-surface-500 hover:underline"
              @click="backToStep1"
            >
              Đổi lại thông tin
            </button>
            <button
              type="button"
              class="text-surface-500 hover:underline"
              :disabled="resending"
              @click="resend"
            >
              Gửi lại mã
            </button>
          </div>
        </form>
      </template>
    </Card>
  </div>
</template>
