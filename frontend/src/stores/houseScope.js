// Chọn một cơ sở để xem xuyên suốt các trang — không chọn thì xem toàn bộ cơ
// sở mà tài khoản đang đăng nhập được phép thấy. Dùng chung một store để chọn
// một lần ở header là áp dụng cho mọi trang, không phải chọn lại từng nơi.
import { defineStore } from "pinia";
import { ref } from "vue";

import { housesApi } from "@/api/accounts";

export const useHouseScopeStore = defineStore("houseScope", () => {
  const houseId = ref(null); // null = xem toàn bộ
  const options = ref([]); // [{value, label}]
  let loaded = false;

  /** Gọi lúc khởi động (sau khi đăng nhập) — chỉ tải danh sách cơ sở một lần. */
  async function ensureLoaded() {
    if (loaded) return;
    loaded = true;
    try {
      const page = await housesApi.list({ page_size: 200 });
      options.value = (page.results ?? page).map((h) => ({ value: h.id, label: h.name }));
    } catch {
      options.value = [];
    }
  }

  function reset() {
    houseId.value = null;
    options.value = [];
    loaded = false;
  }

  return { houseId, options, ensureLoaded, reset };
});
