// PrimeVue DatePicker làm việc với Date; Django/DRF nhận và trả "YYYY-MM-DD".
// Dùng getFullYear/getMonth/getDate (giờ địa phương) thay vì toISOString() —
// toISOString() quy về UTC nên ở múi giờ +07 sẽ lùi ngày sinh đi một ngày.

export function toIsoDate(value) {
  if (!value) return null;
  if (typeof value === "string") return value;

  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function fromIsoDate(value) {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function formatDate(value) {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}
