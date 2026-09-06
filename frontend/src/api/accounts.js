// Endpoint của app `accounts`. Hồ sơ luôn là của chính request.user —
// không có tham số id, nên không thể vô tình sửa hồ sơ người khác.
import { api } from "./client";

export const accountsApi = {
  profile: () => api.get("/accounts/profile/"),
  updateProfile: (payload) => api.patch("/accounts/profile/", payload),
  changePassword: (payload) => api.post("/accounts/change-password/", payload),
};

export const housesApi = {
  list: () => api.get("/tenancy/houses/"),
};
