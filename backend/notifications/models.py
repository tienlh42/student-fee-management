"""Luồng nội dung/tin nhắn tới giáo viên & phụ huynh.

Tách khỏi `people` vì đây không phải thông tin định danh — thay đổi độc lập
với schema nhân khẩu học.
"""

from django.db import models

from core.models import CreatedAtModel, TimeStampedModel


class Notification(TimeStampedModel):
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


class EmailLog(CreatedAtModel):
    """Nhật ký mọi email đã gửi qua `notifications.mail.send_html_mail`.

    Append-only — ghi cả trường hợp gửi lỗi (status=FAILED) để tra soát, không
    sửa lại bản ghi cũ.
    """

    class Status(models.TextChoices):
        SENT = "sent", "Đã gửi"
        FAILED = "failed", "Gửi lỗi"

    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    purpose = models.CharField(max_length=50, blank=True)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_logs",
    )
    status = models.CharField(max_length=10, choices=Status.choices)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Nhật ký email"
        verbose_name_plural = "Nhật ký email"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["to_email", "created_at"])]

    def __str__(self) -> str:
        return f"{self.to_email} · {self.subject} · {self.get_status_display()}"


class OtpCode(TimeStampedModel):
    """Mã OTP dùng một lần, lưu ở Postgres (không dùng Redis — xem README/thảo
    luận: gunicorn chạy nhiều worker nên cache LocMemCache mặc định của app
    không dùng chung giữa các worker được, còn Redis là thừa hạ tầng so với
    quy mô hiện tại). `code_hash` dùng chung cơ chế hash mật khẩu của Django —
    không tự viết hàm băm riêng.
    """

    class Purpose(models.TextChoices):
        LOGIN = "login", "Đăng nhập"
        CHANGE_EMAIL = "change_email", "Đổi email"
        RESET_PASSWORD = "reset_password", "Đặt lại mật khẩu"

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="otp_codes"
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Mã OTP"
        verbose_name_plural = "Mã OTP"
        indexes = [models.Index(fields=["user", "purpose", "expires_at"])]

    def __str__(self) -> str:
        return f"OTP {self.get_purpose_display()} · {self.user}"
