<script setup>
import Card from "primevue/card";
import Message from "primevue/message";
</script>

<template>
  <div class="space-y-4">
    <Message severity="info" :closable="false">
      Scaffold đã chạy. Models của 6 app đã sẵn sàng — bước tiếp theo là viết API
      (<code>serializers.py</code> + <code>urls.py</code> trong từng app) rồi thay các
      màn hình placeholder này bằng DataTable thật.
    </Message>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card v-for="n in 3" :key="n">
        <template #title>Chỉ số {{ n }}</template>
        <template #content>
          <p class="text-surface-500 text-sm">Chờ dữ liệu từ API.</p>
        </template>
      </Card>
    </div>
  </div>
</template>
