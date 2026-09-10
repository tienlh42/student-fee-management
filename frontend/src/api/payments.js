// Bọc các endpoint của app `payments` để view không phải tự ghép query string.
import { api } from "./client";

function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.append(key, value);
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const incomingTransactionsApi = {
  list: (params = {}) => api.get(`/payments/incoming-transactions/${query(params)}`),
  meta: () => api.get("/payments/incoming-transactions/meta/"),
  retryMatch: (id) => api.post(`/payments/incoming-transactions/${id}/retry-match/`),
  allocate: (id, payload) => api.post(`/payments/incoming-transactions/${id}/allocate/`, payload),
  ignore: (id) => api.post(`/payments/incoming-transactions/${id}/ignore/`),
};

export const paymentsApi = {
  list: (params = {}) => api.get(`/payments/payments/${query(params)}`),
  meta: () => api.get("/payments/payments/meta/"),
};

export const refundsApi = {
  list: (params = {}) => api.get(`/payments/refunds/${query(params)}`),
  meta: () => api.get("/payments/refunds/meta/"),
};
