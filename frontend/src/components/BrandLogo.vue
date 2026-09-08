<script setup>
import { computed } from "vue";

import logoRed from "@/assets/brand/logo-red.svg?raw";
import logoWhite from "@/assets/brand/logo-white.svg?raw";
import logoMono from "@/assets/brand/logo-mono.svg?raw";

// "mono" kế thừa `color` CSS (dùng chung với text-* của Tailwind) nên cần
// inline SVG (v-html) thay vì <img src>, vốn không cho SVG con đọc currentColor.
const VARIANTS = { red: logoRed, white: logoWhite, mono: logoMono };

const props = defineProps({
  variant: {
    type: String,
    default: "red",
    validator: (v) => ["red", "white", "mono"].includes(v),
  },
});

const svg = computed(() => VARIANTS[props.variant]);
</script>

<template>
  <span class="edufi-logo inline-block" v-html="svg" />
</template>

<style scoped>
.edufi-logo :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
