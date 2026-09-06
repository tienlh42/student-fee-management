<script setup>
import { useRoute } from "vue-router";
import Card from "primevue/card";

const route = useRoute();
</script>

<template>
  <Card>
    <template #title>{{ route.meta.title }}</template>
    <template #content>
      <p class="text-surface-500 text-sm">
        Màn hình chưa được cài đặt. Route: <code>{{ route.path }}</code>
      </p>
    </template>
  </Card>
</template>
