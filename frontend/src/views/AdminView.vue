<script setup>
import { computed, onMounted, ref } from "vue";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import Tag from "primevue/tag";
import Toolbar from "primevue/toolbar";

import { errorMessage } from "@/api/client";
import { housesApi, usersApi } from "@/api/accounts";
import { bankAccountsApi } from "@/api/payments";
import BankAccountFormDialog from "@/components/BankAccountFormDialog.vue";
import HouseFormDialog from "@/components/HouseFormDialog.vue";
import UserFormDialog from "@/components/UserFormDialog.vue";
import { useAuthStore } from "@/stores/auth";
import { useHouseScopeStore } from "@/stores/houseScope";

const auth = useAuthStore();
const houseScope = useHouseScopeStore();
const toast = useToast();
const confirm = useConfirm();

const activeTab = ref("houses");

/* ---------- Cơ sở ---------- */
const houseRows = ref([]);
const houseLoading = ref(false);
const houseSearch = ref("");
const houseFormVisible = ref(false);
const selectedHouse = ref(null);

const houseOptions = computed(() => houseRows.value.map((h) => ({ value: h.id, label: h.name })));

const filteredHouseRows = computed(() => {
  const term = houseSearch.value.trim().toLowerCase();
  return houseRows.value.filter((row) => {
    if (houseScope.houseId && row.id !== houseScope.houseId) return false;
    if (term && !row.name.toLowerCase().includes(term)) return false;
    return true;
  });
});

async function loadHouses() {
  houseLoading.value = true;
  try {
    const page = await housesApi.list({ page_size: 200 });
    houseRows.value = page.results ?? page;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    houseLoading.value = false;
  }
}

function openCreateHouse() {
  selectedHouse.value = null;
  houseFormVisible.value = true;
}

function openEditHouse(row) {
  selectedHouse.value = row;
  houseFormVisible.value = true;
}

async function onHouseSaved(_row, wasEdit) {
  toast.add({
    severity: "success",
    summary: wasEdit ? "Đã cập nhật cơ sở" : "Đã thêm cơ sở",
    life: 2500,
  });
  await loadHouses();
}

function confirmDeleteHouse(row) {
  confirm.require({
    header: "Xóa cơ sở",
    message: `Xóa cơ sở "${row.name}"? Thao tác này không hoàn tác được.`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await housesApi.remove(row.id);
        toast.add({ severity: "success", summary: "Đã xóa cơ sở", life: 2500 });
        await loadHouses();
      } catch (err) {
        toast.add({
          severity: "error",
          summary: errorMessage(err, "Không xóa được — cơ sở còn học sinh/giáo viên."),
          life: 5000,
        });
      }
    },
  });
}

/* ---------- Tài khoản ---------- */
const userRows = ref([]);
const userLoading = ref(false);
const userSearch = ref("");
const userFormVisible = ref(false);
const selectedUser = ref(null);

const ROLE_LABELS = { teacher: "Giáo viên", guardian: "Phụ huynh", "": "Không" };

const filteredUserRows = computed(() => {
  const term = userSearch.value.trim().toLowerCase();
  return userRows.value.filter((row) => {
    if (houseScope.houseId && row.current_role?.house !== houseScope.houseId) return false;
    if (
      term &&
      !(
        row.username.toLowerCase().includes(term) ||
        (row.email || "").toLowerCase().includes(term) ||
        (row.person_full_name || "").toLowerCase().includes(term)
      )
    )
      return false;
    return true;
  });
});

async function loadUsers() {
  userLoading.value = true;
  try {
    const page = await usersApi.list({ page_size: 200 });
    userRows.value = page.results ?? page;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    userLoading.value = false;
  }
}

function openCreateUser() {
  selectedUser.value = null;
  userFormVisible.value = true;
}

function openEditUser(row) {
  selectedUser.value = row;
  userFormVisible.value = true;
}

async function onUserSaved(_row, wasEdit) {
  toast.add({
    severity: "success",
    summary: wasEdit ? "Đã cập nhật tài khoản" : "Đã thêm tài khoản",
    life: 2500,
  });
  await loadUsers();
}

function confirmDeleteUser(row) {
  confirm.require({
    header: "Xóa tài khoản",
    message: `Xóa tài khoản "${row.username}"? Thao tác này không hoàn tác được.`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await usersApi.remove(row.id);
        toast.add({ severity: "success", summary: "Đã xóa tài khoản", life: 2500 });
        await loadUsers();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 5000 });
      }
    },
  });
}

/* ---------- Tài khoản ngân hàng ---------- */
const bankAccountRows = ref([]);
const bankAccountLoading = ref(false);
const bankAccountSearch = ref("");
const bankAccountFormVisible = ref(false);
const selectedBankAccount = ref(null);

const filteredBankAccountRows = computed(() => {
  const term = bankAccountSearch.value.trim().toLowerCase();
  return bankAccountRows.value.filter((row) => {
    if (houseScope.houseId && row.house !== houseScope.houseId) return false;
    if (
      term &&
      !(
        row.house_name.toLowerCase().includes(term) ||
        row.account_holder_name.toLowerCase().includes(term)
      )
    )
      return false;
    return true;
  });
});

async function loadBankAccounts() {
  bankAccountLoading.value = true;
  try {
    const page = await bankAccountsApi.list({ page_size: 200 });
    bankAccountRows.value = page.results ?? page;
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 4000 });
  } finally {
    bankAccountLoading.value = false;
  }
}

function openCreateBankAccount() {
  selectedBankAccount.value = null;
  bankAccountFormVisible.value = true;
}

function openEditBankAccount(row) {
  selectedBankAccount.value = row;
  bankAccountFormVisible.value = true;
}

async function onBankAccountSaved(_row, wasEdit) {
  toast.add({
    severity: "success",
    summary: wasEdit ? "Đã cập nhật tài khoản ngân hàng" : "Đã thêm tài khoản ngân hàng",
    life: 2500,
  });
  await loadBankAccounts();
}

async function setPrimaryBankAccount(row) {
  try {
    await bankAccountsApi.update(row.id, { is_primary: true });
    toast.add({ severity: "success", summary: "Đã đặt làm tài khoản chính", life: 2500 });
    await loadBankAccounts();
  } catch (err) {
    toast.add({ severity: "error", summary: errorMessage(err), life: 5000 });
  }
}

function confirmDeleteBankAccount(row) {
  confirm.require({
    header: "Xóa tài khoản ngân hàng",
    message: `Xóa tài khoản ngân hàng của "${row.house_name}"? Thao tác này không hoàn tác được.`,
    icon: "pi pi-exclamation-triangle",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptProps: { severity: "danger" },
    accept: async () => {
      try {
        await bankAccountsApi.remove(row.id);
        toast.add({ severity: "success", summary: "Đã xóa tài khoản ngân hàng", life: 2500 });
        await loadBankAccounts();
      } catch (err) {
        toast.add({ severity: "error", summary: errorMessage(err), life: 5000 });
      }
    },
  });
}

onMounted(async () => {
  await Promise.all([loadHouses(), loadUsers(), loadBankAccounts()]);
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="houses">Cơ sở</Tab>
        <Tab value="users">Tài khoản</Tab>
        <Tab value="bankAccounts">Tài khoản ngân hàng</Tab>
      </TabList>

      <TabPanels>
        <!-- ===================== CƠ SỞ ===================== -->
        <TabPanel value="houses">
          <div class="flex flex-col gap-4">
            <Toolbar>
              <template #start>
                <IconField>
                  <InputIcon class="pi pi-search" />
                  <InputText v-model="houseSearch" placeholder="Tìm cơ sở…" />
                </IconField>
              </template>
              <template #end>
                <Button label="Thêm cơ sở" icon="pi pi-plus" @click="openCreateHouse" />
              </template>
            </Toolbar>

            <DataTable
              :value="filteredHouseRows"
              :loading="houseLoading"
              data-key="id"
              size="small"
              striped-rows
            >
              <template #empty>
                <div class="py-6 text-center text-surface-500 text-sm">Chưa có cơ sở nào.</div>
              </template>

              <Column field="name" header="Tên cơ sở" sortable />
              <Column field="address" header="Địa chỉ" />
              <Column field="inbound_email_slug" header="Slug email" style="width: 12rem" />
              <Column header="Số học sinh" style="width: 9rem">
                <template #body="{ data }">{{ data.student_count }}</template>
              </Column>
              <Column header="" style="width: 7rem">
                <template #body="{ data }">
                  <div class="flex justify-end gap-1">
                    <Button
                      v-tooltip.top="'Sửa'"
                      icon="pi pi-pencil"
                      text
                      rounded
                      aria-label="Sửa"
                      @click="openEditHouse(data)"
                    />
                    <Button
                      v-tooltip.top="'Xóa'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      aria-label="Xóa"
                      @click="confirmDeleteHouse(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>

        <!-- ===================== TÀI KHOẢN ===================== -->
        <TabPanel value="users">
          <div class="flex flex-col gap-4">
            <Toolbar>
              <template #start>
                <IconField>
                  <InputIcon class="pi pi-search" />
                  <InputText v-model="userSearch" placeholder="Tìm tên đăng nhập, email, họ tên…" />
                </IconField>
              </template>
              <template #end>
                <Button label="Thêm tài khoản" icon="pi pi-plus" @click="openCreateUser" />
              </template>
            </Toolbar>

            <DataTable
              :value="filteredUserRows"
              :loading="userLoading"
              data-key="id"
              size="small"
              striped-rows
            >
              <template #empty>
                <div class="py-6 text-center text-surface-500 text-sm">Chưa có tài khoản nào.</div>
              </template>

              <Column field="username" header="Tên đăng nhập" sortable />
              <Column field="email" header="Email" />
              <Column field="person_full_name" header="Họ tên" />
              <Column header="Vai trò" style="width: 8rem">
                <template #body="{ data }">
                  <Tag
                    v-if="data.current_role?.kind"
                    :value="ROLE_LABELS[data.current_role.kind]"
                    severity="info"
                  />
                  <span v-else class="text-surface-400">—</span>
                </template>
              </Column>
              <Column header="Trạng thái" style="width: 14rem">
                <template #body="{ data }">
                  <div class="flex flex-wrap gap-1">
                    <Tag
                      :value="data.is_active ? 'Hoạt động' : 'Đã khóa'"
                      :severity="data.is_active ? 'success' : 'secondary'"
                    />
                    <Tag v-if="data.is_superuser" value="Superuser" severity="warn" />
                    <Tag v-else-if="data.is_staff" value="Staff" severity="info" />
                  </div>
                </template>
              </Column>
              <Column header="" style="width: 7rem">
                <template #body="{ data }">
                  <div class="flex justify-end gap-1">
                    <Button
                      v-tooltip.top="'Sửa'"
                      icon="pi pi-pencil"
                      text
                      rounded
                      aria-label="Sửa"
                      @click="openEditUser(data)"
                    />
                    <Button
                      v-if="data.id !== auth.user?.id"
                      v-tooltip.top="'Xóa'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      aria-label="Xóa"
                      @click="confirmDeleteUser(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>

        <!-- ============= TÀI KHOẢN NGÂN HÀNG ============= -->
        <TabPanel value="bankAccounts">
          <div class="flex flex-col gap-4">
            <Toolbar>
              <template #start>
                <IconField>
                  <InputIcon class="pi pi-search" />
                  <InputText v-model="bankAccountSearch" placeholder="Tìm cơ sở, chủ tài khoản…" />
                </IconField>
              </template>
              <template #end>
                <Button
                  label="Thêm tài khoản ngân hàng"
                  icon="pi pi-plus"
                  :disabled="houseOptions.length === 0"
                  @click="openCreateBankAccount"
                />
              </template>
            </Toolbar>

            <DataTable
              :value="filteredBankAccountRows"
              :loading="bankAccountLoading"
              data-key="id"
              size="small"
              striped-rows
            >
              <template #empty>
                <div class="py-6 text-center text-surface-500 text-sm">
                  Chưa cơ sở nào có tài khoản ngân hàng.
                </div>
              </template>

              <Column field="house_name" header="Cơ sở" sortable />
              <Column field="bank_name" header="Ngân hàng" />
              <Column field="account_holder_name" header="Chủ tài khoản" />
              <Column header="Số tài khoản" style="width: 10rem">
                <template #body="{ data }">****{{ data.account_number_last4 }}</template>
              </Column>
              <Column header="Chính" style="width: 8rem">
                <template #body="{ data }">
                  <Tag v-if="data.is_primary" value="Chính" severity="info" />
                  <Button
                    v-else
                    label="Đặt làm chính"
                    text
                    size="small"
                    @click="setPrimaryBankAccount(data)"
                  />
                </template>
              </Column>
              <Column header="" style="width: 7rem">
                <template #body="{ data }">
                  <div class="flex justify-end gap-1">
                    <Button
                      v-tooltip.top="'Sửa'"
                      icon="pi pi-pencil"
                      text
                      rounded
                      aria-label="Sửa"
                      @click="openEditBankAccount(data)"
                    />
                    <Button
                      v-tooltip.top="'Xóa'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      aria-label="Xóa"
                      @click="confirmDeleteBankAccount(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <HouseFormDialog v-model:visible="houseFormVisible" :house="selectedHouse" @saved="onHouseSaved" />

    <UserFormDialog
      v-model:visible="userFormVisible"
      :user="selectedUser"
      :house-options="houseOptions"
      :is-self="selectedUser !== null && selectedUser.id === auth.user?.id"
      @saved="onUserSaved"
    />

    <BankAccountFormDialog
      v-model:visible="bankAccountFormVisible"
      :bank-account="selectedBankAccount"
      :house-options="houseOptions"
      @saved="onBankAccountSaved"
    />
  </div>
</template>
