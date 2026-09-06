<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import Button from "primevue/button";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";

import { errorMessage } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const username = ref("");
const password = ref("");
const error = ref("");

async function submit() {
  error.value = "";
  try {
    await auth.login(username.value.trim(), password.value);
    // `redirect` do router guard đặt khi chặn một route cần đăng nhập.
    await router.replace(route.query.redirect || "/");
  } catch (err) {
    error.value = errorMessage(err, "Đăng nhập không thành công.");
    password.value = "";
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-100 dark:bg-surface-950 p-4">
    <Card class="w-full max-w-sm">
      <template #title>
        <div class="text-center">
          <div class="text-xl font-semibold">Quản lý học phí</div>
          <div class="text-sm font-normal text-surface-500 mt-1">Đăng nhập để tiếp tục</div>
        </div>
      </template>

      <template #content>
        <form class="flex flex-col gap-4" @submit.prevent="submit">
          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

          <div class="flex flex-col gap-1">
            <label for="username" class="text-sm font-medium">Tên đăng nhập</label>
            <InputText
              id="username"
              v-model="username"
              autocomplete="username"
              autofocus
              required
            />
          </div>

          <div class="flex flex-col gap-1">
            <label for="password" class="text-sm font-medium">Mật khẩu</label>
            <Password
              id="password"
              v-model="password"
              input-id="password"
              :feedback="false"
              toggle-mask
              autocomplete="current-password"
              input-class="w-full"
              class="w-full"
              required
            />
          </div>

          <Button
            type="submit"
            label="Đăng nhập"
            icon="pi pi-sign-in"
            :loading="auth.pending"
            :disabled="!username || !password"
          />
        </form>
      </template>
    </Card>
  </div>
</template>
