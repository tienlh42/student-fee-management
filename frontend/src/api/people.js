// Bọc các endpoint của app `people` để view không phải tự ghép query string.
import { api } from "./client";

function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.append(key, value);
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const studentsApi = {
  list: (params = {}) => api.get(`/people/students/${query(params)}`),
  retrieve: (id) => api.get(`/people/students/${id}/`),
  meta: () => api.get("/people/students/meta/"),
  create: (payload) => api.post("/people/students/", payload),
  update: (id, payload) => api.patch(`/people/students/${id}/`, payload),
  remove: (id) => api.delete(`/people/students/${id}/`),
  guardians: (id) => api.get(`/people/students/${id}/guardians/`),
  linkGuardian: (id, payload) => api.post(`/people/students/${id}/guardians/`, payload),
  unlinkGuardian: (id, guardianId) =>
    api.delete(`/people/students/${id}/guardians/${guardianId}/`),
};

export const guardiansApi = {
  list: (params = {}) => api.get(`/people/guardians/${query(params)}`),
  create: (payload) => api.post("/people/guardians/", payload),
};

export const teachersApi = {
  list: (params = {}) => api.get(`/people/teachers/${query(params)}`),
};
