// Theo dõi form (reactive object) có bị sửa so với lúc chụp snapshot hay chưa,
// và hỏi xác nhận trước khi đóng nếu còn thay đổi chưa lưu — dùng chung cho
// AppDialog (đóng qua X/Esc/click ra ngoài) và nút "Hủy" trong từng form.
import { computed, ref } from "vue";
import { useConfirm } from "primevue/useconfirm";

export function useDirtyTracking(form) {
  const snapshot = ref(null);

  function markClean() {
    snapshot.value = JSON.stringify(form);
  }

  const dirty = computed(() => snapshot.value !== null && JSON.stringify(form) !== snapshot.value);

  return { dirty, markClean };
}

export function useCloseGuard() {
  const confirm = useConfirm();

  function guardedClose(dirty, close) {
    if (!dirty) {
      close();
      return;
    }
    confirm.require({
      header: "Bỏ thay đổi?",
      message: "Các thay đổi chưa lưu sẽ mất nếu đóng lại bây giờ.",
      icon: "pi pi-exclamation-triangle",
      acceptLabel: "Đóng, bỏ thay đổi",
      rejectLabel: "Tiếp tục chỉnh sửa",
      acceptProps: { severity: "danger" },
      accept: close,
    });
  }

  return { guardedClose };
}
