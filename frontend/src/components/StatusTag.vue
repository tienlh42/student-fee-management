<script setup>
// Tag trạng thái dùng chung — icon đi kèm theo severity, không phải theo domain
// (paid/pending/overdue, active/paused/..., matched/unmatched/... đều tự map đúng
// icon miễn là truyền đúng severity chuẩn PrimeVue).
import Tag from "primevue/tag";

const ICON_BY_SEVERITY = {
  success: "pi pi-check-circle",
  info: "pi pi-info-circle",
  warn: "pi pi-exclamation-triangle",
  danger: "pi pi-times-circle",
  secondary: "pi pi-minus-circle",
  contrast: "pi pi-circle",
};

const props = defineProps({
  value: { type: String, required: true },
  severity: { type: String, default: "secondary" },
  icon: { type: String, default: null },
});
</script>

<template>
  <Tag :value="value" :severity="severity" :icon="icon ?? ICON_BY_SEVERITY[props.severity] ?? ICON_BY_SEVERITY.secondary" />
</template>
