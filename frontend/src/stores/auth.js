import { defineStore } from "pinia";
import { ref, computed } from "vue";

import { api } from "@/api/client";

// Vai trò do backend suy ra từ dữ liệu (accounts/services.py:role_for), không
// phải field trong DB — frontend chỉ đọc, không bao giờ tự suy diễn lại.
const EMPTY_ROLE = {
  is_superuser: false,
  is_staff_admin: false,
  is_teacher: false,
  is_guardian: false,
  can_see_bank_data: false,
  can_manage_houses: false,
  can_manage_users: false,
};

export const useAuthStore = defineStore("auth", () => {
  const user = ref(null);
  const resolved = ref(false); // đã hỏi /me lần nào chưa
  const pending = ref(false);

  const isAuthenticated = computed(() => user.value !== null);
  const role = computed(() => user.value?.role ?? EMPTY_ROLE);
  const canEdit = computed(() => role.value.is_teacher || role.value.is_staff_admin);
  const displayName = computed(() => user.value?.full_name ?? "");

  /** Gọi một lần lúc khởi động: vừa lấy user, vừa nhận cookie csrftoken. */
  async function fetchMe() {
    try {
      const data = await api.get("/accounts/me/");
      user.value = data.authenticated ? data.user : null;
    } catch {
      // Mất mạng hoặc backend chết — coi như chưa đăng nhập, guard sẽ đẩy về /login.
      user.value = null;
    } finally {
      resolved.value = true;
    }
  }

  /** Đảm bảo đã biết trạng thái đăng nhập trước khi router quyết định điều hướng. */
  async function ensureResolved() {
    if (!resolved.value) await fetchMe();
    return user.value;
  }

  async function login(username, password) {
    pending.value = true;
    try {
      user.value = await api.post("/accounts/login/", { username, password });
      resolved.value = true;
      return user.value;
    } finally {
      pending.value = false;
    }
  }

  async function logout() {
    try {
      await api.post("/accounts/logout/");
    } finally {
      // Kể cả khi request lỗi vẫn xóa state phía client rồi đẩy về /login.
      user.value = null;
      resolved.value = true;
    }
  }

  return {
    user,
    resolved,
    pending,
    isAuthenticated,
    role,
    canEdit,
    displayName,
    fetchMe,
    ensureResolved,
    login,
    logout,
  };
});
