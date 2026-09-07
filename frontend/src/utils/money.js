export function formatMoney(value) {
  const n = Number(value ?? 0);
  return `${n.toLocaleString("vi-VN")} đ`;
}

/** "2026-09-01" -> "09/2026" — Invoice.period luôn là ngày đầu tháng. */
export function formatPeriod(value) {
  if (!value) return "—";
  const [year, month] = value.split("-");
  return `${month}/${year}`;
}
