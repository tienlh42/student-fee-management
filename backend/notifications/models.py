"""Luồng nội dung/tin nhắn tới giáo viên & phụ huynh.

Tách khỏi `people` vì đây không phải thông tin định danh — thay đổi độc lập
với schema nhân khẩu học.
"""

from django.db import models


class Notification(models.Model):
    class Category(models.TextChoices):
        LICH_NGHI = "lich_nghi", "Lịch nghỉ"
        SU_KIEN = "su_kien", "Sự kiện"
        VANG_MAT = "vang_mat", "Vắng mặt"
        HOC_TAP = "hoc_tap", "Học tập"
        KHAC = "khac", "Khác"

    house = models.ForeignKey(
        "tenancy.House", on_delete=models.CASCADE, related_name="notifications"
    )
    student = models.ForeignKey(
        "people.Student",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="Bỏ trống = thông báo cho toàn bộ cơ sở.",
    )
    title = models.CharField("Tiêu đề", max_length=255)
    body = models.TextField("Nội dung")
    category = models.CharField(
        "Phân loại", max_length=20, choices=Category.choices, default=Category.KHAC
    )
    created_by_user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="notifications_created"
    )
    published_at = models.DateTimeField(
        "Thời điểm đăng", null=True, blank=True, help_text="Bỏ trống = còn là nháp."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Thông báo"
        verbose_name_plural = "Thông báo"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["house", "published_at"]),
            models.Index(fields=["student", "published_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_published(self) -> bool:
        return self.published_at is not None


class NotificationRead(models.Model):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="reads"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notification_reads"
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lượt đọc thông báo"
        verbose_name_plural = "Lượt đọc thông báo"
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "user"], name="uniq_notification_read"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} đã đọc {self.notification}"
