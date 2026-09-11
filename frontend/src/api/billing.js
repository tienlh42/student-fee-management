// Bọc các endpoint của app `billing` để view không phải tự ghép query string.
import { api } from "./client";

function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.append(key, value);
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const feeItemsApi = {
  list: (params = {}) => api.get(`/billing/fee-items/${query(params)}`),
  meta: () => api.get("/billing/fee-items/meta/"),
  create: (payload) => api.post("/billing/fee-items/", payload),
  update: (id, payload) => api.patch(`/billing/fee-items/${id}/`, payload),
  remove: (id) => api.delete(`/billing/fee-items/${id}/`),
};

export const feePackagesApi = {
  list: (params = {}) => api.get(`/billing/fee-packages/${query(params)}`),
  meta: () => api.get("/billing/fee-packages/meta/"),
  create: (payload) => api.post("/billing/fee-packages/", payload),
  update: (id, payload) => api.patch(`/billing/fee-packages/${id}/`, payload),
  remove: (id) => api.delete(`/billing/fee-packages/${id}/`),
};

export const studentFeePackagesApi = {
  list: (params = {}) => api.get(`/billing/student-fee-packages/${query(params)}`),
  create: (payload) => api.post("/billing/student-fee-packages/", payload),
  update: (id, payload) => api.patch(`/billing/student-fee-packages/${id}/`, payload),
  remove: (id) => api.delete(`/billing/student-fee-packages/${id}/`),
};

export const studentDiscountsApi = {
  list: (params = {}) => api.get(`/billing/student-discounts/${query(params)}`),
  create: (payload) => api.post("/billing/student-discounts/", payload),
  update: (id, payload) => api.patch(`/billing/student-discounts/${id}/`, payload),
  remove: (id) => api.delete(`/billing/student-discounts/${id}/`),
};

export const invoicesApi = {
  list: (params = {}) => api.get(`/billing/invoices/${query(params)}`),
  meta: () => api.get("/billing/invoices/meta/"),
  update: (id, payload) => api.patch(`/billing/invoices/${id}/`, payload),
  generate: (payload) => api.post("/billing/invoices/generate/", payload),
  void: (id) => api.post(`/billing/invoices/${id}/void/`),
  restore: (id) => api.post(`/billing/invoices/${id}/restore/`),
  remove: (id) => api.delete(`/billing/invoices/${id}/`),
  payments: (id) => api.get(`/billing/invoices/${id}/payments/`),
  vietqr: (id) => api.get(`/billing/invoices/${id}/vietqr/`),
  // Mở trực tiếp bằng window.open — trang HTML server-render (không phải JSON),
  // dùng chung session cookie có sẵn của trình duyệt, không qua fetch wrapper.
  printUrl: (id) => `/api/billing/invoices/${id}/print/`,
  recordPayment: (id, payload) => api.post(`/billing/invoices/${id}/record-payment/`, payload),
  refund: (id, payload) => api.post(`/billing/invoices/${id}/refund/`, payload),
};
