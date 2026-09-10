// Endpoint của app `accounts`. Hồ sơ luôn là của chính request.user —
// không có tham số id, nên không thể vô tình sửa hồ sơ người khác.
import { api } from "./client";

function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.append(key, value);
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const accountsApi = {
  profile: () => api.get("/accounts/profile/"),
  updateProfile: (payload) => api.patch("/accounts/profile/", payload),
  changePassword: (payload) => api.post("/accounts/change-password/", payload),
};

export const housesApi = {
  list: (params = {}) => api.get(`/tenancy/houses/${query(params)}`),
  create: (payload) => api.post("/tenancy/houses/", payload),
  update: (id, payload) => api.patch(`/tenancy/houses/${id}/`, payload),
  remove: (id) => api.delete(`/tenancy/houses/${id}/`),
};

// Quản lý tài khoản đăng nhập — chỉ superuser gọi được (xem CanManageUsers).
export const usersApi = {
  list: (params = {}) => api.get(`/accounts/users/${query(params)}`),
  create: (payload) => api.post("/accounts/users/", payload),
  update: (id, payload) => api.patch(`/accounts/users/${id}/`, payload),
  remove: (id) => api.delete(`/accounts/users/${id}/`),
};
