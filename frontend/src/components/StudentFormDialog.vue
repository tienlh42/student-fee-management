<script setup>
import { computed, reactive, ref, watch } from "vue";

import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";

import { errorMessage, fieldErrors } from "@/api/client";
import { studentsApi } from "@/api/people";
import { fromIsoDate, toIsoDate } from "@/utils/date";

const props = defineProps({
  visible: { type: Boolean, default: false },
  student: { type: Object, default: null }, // null = tạo mới
  meta: { type: Object, required: true },
});
const emit = defineEmits(["update:visible", "saved"]);

const DATE_FIELDS = ["date_of_birth", "id_issued_date"];

function blankForm() {
  return {
    person: {
      full_name: "",
      gender: "",
      date_of_birth: null,
      place_of_birth: "",
      nationality: "Việt Nam",
      ethnicity: "",
      id_number: "",
      id_issued_date: null,
      id_issued_place: "",
      permanent_address: "",
      current_address: "",
      phone: "",
      email: "",
    },
    house: props.meta.default_house ?? null,
    class_grade: "",
    status: "active",
    enrolled_date: null,
  };
}

const form = reactive(blankForm());
const saving = ref(false);
const error = ref("");
const errors = ref({});

const isEdit = computed(() => props.student !== null);
const title = computed(() => (isEdit.value ? "Sửa thông tin học sinh" : "Thêm học sinh"));

// Cơ sở chỉ cho chọn khi thực sự có nhiều — quy mô hiện tại thường chỉ một.
const showHousePicker = computed(() => (props.meta.houses?.length ?? 0) > 1);

watch(
  () => props.visible,
  (open) => {
    if (!open) return;
    error.value = "";
    errors.value = {};
    Object.assign(form, blankForm());

    if (props.student) {
      Object.assign(form.person, props.student.person);
      for (const field of DATE_FIELDS) {
        form.person[field] = fromIsoDate(props.student.person[field]);
      }
      form.house = props.student.house;
      form.class_grade = props.student.class_grade;
      form.status = props.student.status;
      form.enrolled_date = fromIsoDate(props.student.enrolled_date);
    }
  },
);

function buildPayload() {
  const person = { ...form.person };
  for (const field of DATE_FIELDS) person[field] = toIsoDate(person[field]);

  return {
    person,
    house: form.house,
    class_grade: form.class_grade,
    status: form.status,
    enrolled_date: toIsoDate(form.enrolled_date),
  };
}

async function submit() {
  error.value = "";
  errors.value = {};
  saving.value = true;
  try {
    const payload = buildPayload();
    const saved = isEdit.value
      ? await studentsApi.update(props.student.id, payload)
      : await studentsApi.create(payload);
    emit("saved", saved, isEdit.value);
    emit("update:visible", false);
  } catch (err) {
    error.value = errorMessage(err, "Không lưu được học sinh.");
    // DRF lồng lỗi của person vào {person: {full_name: [...]}}.
    errors.value = { ...fieldErrors(err), ...fieldErrors({ payload: err?.payload?.person }) };
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="title"
    modal
    :style="{ width: '46rem' }"
    :breakpoints="{ '960px': '95vw' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form id="student-form" class="flex flex-col gap-5" @submit.prevent="submit">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <section class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="flex flex-col gap-1 md:col-span-2">
          <label for="full_name" class="text-sm font-medium">Họ và tên *</label>
          <InputText
            id="full_name"
            v-model="form.person.full_name"
            :invalid="!!errors.full_name"
            required
            autofocus
          />
          <small v-if="errors.full_name" class="text-red-500">{{ errors.full_name }}</small>
        </div>

        <div class="flex flex-col gap-1">
          <label for="gender" class="text-sm font-medium">Giới tính</label>
          <Select
            id="gender"
            v-model="form.person.gender"
            :options="meta.genders"
            option-label="label"
            option-value="value"
            placeholder="Chọn"
            show-clear
          />
        </div>

        <div class="flex flex-col gap-1">
          <label for="dob" class="text-sm font-medium">Ngày sinh</label>
          <DatePicker id="dob" v-model="form.person.date_of_birth" date-format="dd/mm/yy" show-icon />
        </div>

        <div class="flex flex-col gap-1">
          <label for="phone" class="text-sm font-medium">Điện thoại</label>
          <InputText id="phone" v-model="form.person.phone" />
        </div>

        <div class="flex flex-col gap-1">
          <label for="email" class="text-sm font-medium">Email</label>
          <InputText id="email" v-model="form.person.email" type="email" :invalid="!!errors.email" />
          <small v-if="errors.email" class="text-red-500">{{ errors.email }}</small>
        </div>

        <div class="flex flex-col gap-1 md:col-span-2">
          <label for="current_address" class="text-sm font-medium">Chỗ ở hiện tại</label>
          <InputText id="current_address" v-model="form.person.current_address" />
        </div>
      </section>

      <section class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-surface-200 dark:border-surface-700">
        <div v-if="showHousePicker" class="flex flex-col gap-1 md:col-span-2">
          <label for="house" class="text-sm font-medium">Cơ sở *</label>
          <Select
            id="house"
            v-model="form.house"
            :options="meta.houses"
            option-label="label"
            option-value="value"
            :invalid="!!errors.house"
          />
          <small v-if="errors.house" class="text-red-500">{{ errors.house }}</small>
        </div>

        <div class="flex flex-col gap-1">
          <label for="class_grade" class="text-sm font-medium">Lớp</label>
          <InputText id="class_grade" v-model="form.class_grade" />
        </div>

        <div class="flex flex-col gap-1">
          <label for="status" class="text-sm font-medium">Trạng thái</label>
          <Select
            id="status"
            v-model="form.status"
            :options="meta.statuses"
            option-label="label"
            option-value="value"
          />
        </div>

        <div class="flex flex-col gap-1">
          <label for="enrolled" class="text-sm font-medium">Ngày nhập học</label>
          <DatePicker id="enrolled" v-model="form.enrolled_date" date-format="dd/mm/yy" show-icon />
        </div>
      </section>
    </form>

    <template #footer>
      <Button label="Hủy" severity="secondary" text @click="emit('update:visible', false)" />
      <Button
        type="submit"
        form="student-form"
        label="Lưu"
        icon="pi pi-check"
        :loading="saving"
        :disabled="!form.person.full_name"
      />
    </template>
  </Dialog>
</template>
