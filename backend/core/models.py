"""Base model dùng chung cho toàn bộ app nghiệp vụ.

Chỉ chứa abstract base class — không có bảng riêng, không cần migration
cho chính app này. Field trùng tên/kiểu với field cũ nên gắn vào model đã có
sẵn `created_at`/`updated_at` không sinh ra migration nào.
"""

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """created_at + updated_at — dùng cho model có thể bị sửa sau khi tạo."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CreatedAtModel(models.Model):
    """Chỉ created_at — dùng cho bản ghi bất biến/append-only (log giao dịch,
    thanh toán đã ghi nhận, hoàn tiền...). Sửa bản ghi loại này nên là tạo bản
    ghi mới, không phải update tại chỗ."""

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Xóa hàng loạt qua queryset — soft delete, không đụng DB row."""
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        """Xóa thật — chỉ dùng khi chắc chắn không cần khôi phục."""
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """Manager mặc định — chỉ thấy bản ghi còn sống, giống hành vi query thường."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """is_deleted + deleted_at — xóa "mềm" để không mất dữ liệu liên kết
    (hóa đơn, thanh toán cũ của một học sinh đã ngừng học vẫn phải còn nguyên).

    `objects` (mặc định) chỉ trả bản ghi còn sống — dùng cho toàn bộ code
    nghiệp vụ/API như bình thường. `all_objects` không lọc gì — chỉ dùng cho
    admin/audit/khôi phục. Gọi `.delete()` trên instance là xóa mềm; muốn xóa
    thật phải gọi tường minh `.delete(hard=True)`.
    """

    is_deleted = models.BooleanField(default=False, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, hard=False):
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=["is_deleted", "deleted_at"])
        return (1, {self._meta.label: 1})

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class UserTrackingModel(models.Model):
    """created_by_user + updated_by_user — audit user nào tạo/sửa bản ghi.

    Đặt tên theo đúng convention đã có sẵn trong app (`refunded_by_user`,
    `recorded_by_user`, `created_by_user`) thay vì `created_by`/`updated_by`
    kiểu generic.

    Cố tình KHÔNG tự set qua signal/middleware/thread-local: `services.py`
    trong repo này chủ đích thuần nghiệp vụ, không chạm HTTP request (xem
    README). View là nơi duy nhất biết `request.user` — set qua
    `core.views.UserTrackingViewSetMixin`, hoặc truyền tay xuống service như
    `billing.services.record_cash_payment` đang làm với `recorded_by_user`.
    """

    created_by_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_by_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True
