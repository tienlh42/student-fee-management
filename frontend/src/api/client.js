// Same-origin + session auth => chỉ cần gửi kèm CSRF token cho request ghi.
// Không có baseURL tuyệt đối, không CORS, không lưu token ở localStorage.

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export async function request(path, { method = "GET", body, ...rest } = {}) {
  const headers = { Accept: "application/json", ...(rest.headers ?? {}) };

  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (UNSAFE.has(method.toUpperCase())) {
    const token = getCookie("csrftoken");
    if (token) headers["X-CSRFToken"] = token;
  }

  const response = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    ...rest,
  });

  if (response.status === 204) return null;

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(`API ${response.status} ${path}`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export const api = {
  get: (path, options) => request(path, { ...options, method: "GET" }),
  post: (path, body, options) => request(path, { ...options, method: "POST", body }),
  patch: (path, body, options) => request(path, { ...options, method: "PATCH", body }),
  put: (path, body, options) => request(path, { ...options, method: "PUT", body }),
  delete: (path, options) => request(path, { ...options, method: "DELETE" }),
};

/** Gom lỗi DRF (`{field: [msg]}`, `{detail: msg}`) thành một chuỗi hiển thị được. */
export function errorMessage(error, fallback = "Có lỗi xảy ra, vui lòng thử lại.") {
  const payload = error?.payload;
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (payload.detail) return payload.detail;

  const parts = Object.values(payload).flat().filter((v) => typeof v === "string");
  return parts.length ? parts.join(" ") : fallback;
}

/** Lỗi theo từng field, để gắn vào input trong form. */
export function fieldErrors(error) {
  const payload = error?.payload;
  if (!payload || typeof payload !== "object") return {};

  return Object.fromEntries(
    Object.entries(payload)
      .filter(([key]) => key !== "detail")
      .map(([key, value]) => [key, Array.isArray(value) ? value.join(" ") : String(value)]),
  );
}
