<script setup>
import Dialog from "primevue/dialog";
import ProgressSpinner from "primevue/progressspinner";

import { useCloseGuard } from "@/utils/dirty";

const props = defineProps({
  visible: { type: Boolean, default: false },
  header: { type: String, default: undefined },
  // Hiện overlay mờ + spinner đè lên nội dung, dùng khi form đang submit.
  loading: { type: Boolean, default: false },
  // Có thay đổi chưa lưu — đóng (X/Esc/click ra ngoài) sẽ hỏi xác nhận trước.
  dirty: { type: Boolean, default: false },
  draggable: { type: Boolean, default: true },
  maximizable: { type: Boolean, default: true },
  style: { type: Object, default: () => ({ width: "34rem" }) },
  breakpoints: { type: Object, default: () => ({ "960px": "95vw" }) },
});
const emit = defineEmits(["update:visible"]);
const { guardedClose } = useCloseGuard();

function onUpdateVisible(next) {
  if (next) {
    emit("update:visible", true);
    return;
  }
  guardedClose(props.dirty, () => emit("update:visible", false));
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="header"
    modal
    :draggable="draggable"
    :maximizable="maximizable"
    :style="style"
    :breakpoints="breakpoints"
    @update:visible="onUpdateVisible"
  >
    <template v-if="$slots.header" #header>
      <slot name="header" />
    </template>

    <div class="relative">
      <div
        v-if="loading"
        class="absolute inset-0 z-10 flex items-center justify-center rounded bg-surface-0/70 dark:bg-surface-900/70"
      >
        <ProgressSpinner style="width: 2.5rem; height: 2.5rem" stroke-width="4" />
      </div>
      <slot />
    </div>

    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </Dialog>
</template>
