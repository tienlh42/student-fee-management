<script setup>
import { computed } from "vue";

import Step from "primevue/step";
import StepItem from "primevue/stepitem";
import StepList from "primevue/steplist";
import StepPanel from "primevue/steppanel";
import StepPanels from "primevue/steppanels";
import Stepper from "primevue/stepper";
import Tag from "primevue/tag";

import AppDialog from "@/components/AppDialog.vue";

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, required: true },
  // [{ value, label, severity, description }] — thứ tự trong mảng dùng làm thứ tự hiển thị trên stepper.
  items: { type: Array, required: true },
});
const emit = defineEmits(["update:visible"]);

// Nhiều status quá thì stepper ngang tràn dòng, xếp dọc cho dễ đọc hơn.
const vertical = computed(() => props.items.length > 4);
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="title"
    :style="{ width: vertical ? '34rem' : '46rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <Stepper v-if="vertical" :value="1">
      <StepItem v-for="(item, index) in items" :key="item.value" :value="index + 1">
        <Step>{{ item.label }}</Step>
        <StepPanel>
          <div class="flex flex-col gap-2 pb-4 pl-2">
            <Tag :value="item.label" :severity="item.severity" class="self-start" />
            <p class="text-sm text-surface-600 dark:text-surface-300">{{ item.description }}</p>
          </div>
        </StepPanel>
      </StepItem>
    </Stepper>

    <Stepper v-else :value="1">
      <StepList>
        <Step v-for="(item, index) in items" :key="item.value" :value="index + 1">
          {{ item.label }}
        </Step>
      </StepList>
      <StepPanels>
        <StepPanel v-for="(item, index) in items" :key="item.value" :value="index + 1">
          <div class="flex flex-col gap-3 py-4">
            <Tag :value="item.label" :severity="item.severity" class="self-start" />
            <p class="text-sm text-surface-600 dark:text-surface-300">{{ item.description }}</p>
          </div>
        </StepPanel>
      </StepPanels>
    </Stepper>
  </AppDialog>
</template>
