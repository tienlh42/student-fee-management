<script setup>
import { RouterLink } from "vue-router";
</script>

<template>
  <div class="py-16 text-center space-y-3">
    <p class="text-4xl font-semibold">404</p>
    <p class="text-surface-500">Không tìm thấy trang.</p>
    <RouterLink to="/" class="text-primary underline">Về trang chủ</RouterLink>
  </div>
</template>
