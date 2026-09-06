"""Billing trả lời câu hỏi: "học sinh nợ bao nhiêu".

Không quan tâm tiền đã thực về hay chưa — đó là việc của app `payments`.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class FeeItem(models.Model):
    """Một khoản thu đơn lẻ: học phí, tiền ăn, phí xe..."""

    class Category(models.TextChoices):
        TUITION = "tuition", "Học phí"
        MEAL = "meal", "Tiền ăn"
        TRANSPORT = "transport", "Phí xe"
        OTHER = "other", "Khác"

    house = models.ForeignKey("tenancy.House", on_delete=models.CASCADE, related_name="fee_items")
    name = models.CharField("Tên khoản thu", max_length=255)
    category = models.CharField(
        "Nhóm", max_length=20, choices=Category.choices, default=Category.OTHER
    )
    default_amount = models.DecimalField("Số tiền mặc định", max_digits=12, decimal_places=2)
    is_active = models.BooleanField("Đang áp dụng", default=True)

    class Meta:
        verbose_name = "Khoản thu"
        verbose_name_plural = "Khoản thu"
        ordering = ["category", "name"]

    def __str__(self) -> str:
        return self.name


class FeePackage(models.Model):
    """Gói phí gộp nhiều khoản thu, gắn kỳ hạn đóng."""

    class BillingTiming(models.TextChoices):
        PREPAID = "prepaid", "Thu trước"
        POSTPAID = "postpaid", "Thu sau"

    house = models.ForeignKey(
        "tenancy.House", on_delete=models.CASCADE, related_name="fee_packages"
    )
    name = models.CharField("Tên gói", max_length=255)
    description = models.TextField("Mô tả", blank=True)
    due_day_of_month = models.PositiveSmallIntegerField(
        "Hạn đóng (ngày trong tháng)",
        default=5,
        validators=[MinValueValidator(1)],
        help_text="1-31. Nếu tháng không có ngày này thì lùi về ngày cuối tháng.",
    )
    billing_timing = models.CharField(
        "Thời điểm thu", max_length=10, choices=BillingTiming.choices, default=BillingTiming.PREPAID
    )
    is_active = models.BooleanField("Đang áp dụng", default=True)

    class Meta:
        verbose_name = "Gói phí"
        verbose_name_plural = "Gói phí"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_day_of_month__gte=1, due_day_of_month__lte=31),
                name="fee_package_due_day_in_range",
            )
        ]

    def __str__(self) -> str:
        return self.name


class FeePackageItem(models.Model):
    fee_package = models.ForeignKey(FeePackage, on_delete=models.CASCADE, related_name="items")
    fee_item = models.ForeignKey(FeeItem, on_delete=models.PROTECT, related_name="package_links")
    amount = models.DecimalField(
        "Số tiền", max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Bỏ trống để dùng default_amount của khoản thu.",
    )

    class Meta:
        verbose_name = "Khoản thu trong gói"
        verbose_name_plural = "Khoản thu trong gói"
        constraints = [
            models.UniqueConstraint(
                fields=["fee_package", "fee_item"], name="uniq_package_item"
            )
        ]

    @property
    def effective_amount(self) -> Decimal:
        return self.amount if self.amount is not None else self.fee_item.default_amount

    def __str__(self) -> str:
        return f"{self.fee_package} / {self.fee_item}"


class StudentFeePackage(models.Model):
    """Học sinh đăng ký gói phí trong một khoảng thời gian."""

    student = models.ForeignKey(
        "people.Student", on_delete=models.CASCADE, related_name="fee_packages"
    )
    fee_package = models.ForeignKey(
        FeePackage, on_delete=models.PROTECT, related_name="subscriptions"
    )
    effective_from = models.DateField("Áp dụng từ")
    effective_until = models.DateField("Áp dụng đến", null=True, blank=True)

    class Meta:
        verbose_name = "Gói phí của học sinh"
        verbose_name_plural = "Gói phí của học sinh"
        ordering = ["-effective_from"]
        indexes = [models.Index(fields=["student", "effective_from"])]

    def __str__(self) -> str:
        return f"{self.student} · {self.fee_package}"


class StudentDiscount(models.Model):
    """Giảm trừ: học bổng, giảm giá anh em ruột..."""

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Theo phần trăm"
        FIXED = "fixed_amount", "Số tiền cố định"

    student = models.ForeignKey(
        "people.Student", on_delete=models.CASCADE, related_name="discounts"
    )
    fee_item = models.ForeignKey(
        FeeItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="discounts",
        help_text="Bỏ trống = áp dụng trên toàn hóa đơn.",
    )
    name = models.CharField("Tên giảm trừ", max_length=255)
    discount_type = models.CharField(
        "Kiểu", max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE
    )
    value = models.DecimalField("Giá trị", max_digits=12, decimal_places=2)
    effective_from = models.DateField("Áp dụng từ")
    effective_until = models.DateField("Áp dụng đến", null=True, blank=True)
    is_active = models.BooleanField("Đang áp dụng", default=True)

    class Meta:
        verbose_name = "Giảm trừ"
        verbose_name_plural = "Giảm trừ"
        ordering = ["-effective_from"]

    def __str__(self) -> str:
        return f"{self.name} · {self.student}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Nháp"
        ISSUED = "issued", "Đã phát hành"
        PARTIALLY_PAID = "partially_paid", "Thanh toán một phần"
        PAID = "paid", "Đã thanh toán"
        VOID = "void", "Đã hủy"

    house = models.ForeignKey("tenancy.House", on_delete=models.PROTECT, related_name="invoices")
    student = models.ForeignKey(
        "people.Student", on_delete=models.PROTECT, related_name="invoices"
    )
    period = models.DateField("Kỳ", help_text="Dùng ngày đầu tháng của kỳ, vd 2026-09-01.")
    total_amount = models.DecimalField("Tổng tiền", max_digits=12, decimal_places=2, default=0)
    adjustment_amount = models.DecimalField(
        "Điều chỉnh", max_digits=12, decimal_places=2, default=0,
        help_text="Dương = cộng thêm, âm = trừ bớt.",
    )
    adjustment_note = models.CharField("Lý do điều chỉnh", max_length=500, blank=True)
    status = models.CharField(
        "Trạng thái", max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    due_date = models.DateField("Hạn thanh toán")
    qr_reference_code = models.CharField(
        "Mã tham chiếu QR",
        max_length=40,
        unique=True,
        help_text="Chuỗi xuất hiện trong nội dung chuyển khoản, dùng để tự khớp giao dịch.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hóa đơn"
        verbose_name_plural = "Hóa đơn"
        ordering = ["-period", "student__person__full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "period"], name="uniq_invoice_student_period"
            )
        ]
        indexes = [
            models.Index(fields=["house", "period"]),
            models.Index(fields=["status", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"HD {self.qr_reference_code} · {self.student}"

    @property
    def net_amount(self) -> Decimal:
        """Số phải thu thực tế = tổng dòng hóa đơn + điều chỉnh thủ công."""
        return self.total_amount + self.adjustment_amount

    @property
    def paid_amount(self) -> Decimal:
        agg = self.payments.aggregate(total=models.Sum("amount_applied"))
        return agg["total"] or Decimal("0")

    @property
    def refunded_amount(self) -> Decimal:
        agg = self.refunds.aggregate(total=models.Sum("amount"))
        return agg["total"] or Decimal("0")

    @property
    def outstanding_amount(self) -> Decimal:
        return self.net_amount - self.paid_amount + self.refunded_amount


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    fee_item = models.ForeignKey(
        FeeItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_items"
    )
    fee_item_name_snapshot = models.CharField(
        "Tên khoản thu (snapshot)", max_length=255,
        help_text="Chốt tại thời điểm phát hành để hóa đơn cũ không đổi khi FeeItem đổi tên.",
    )
    amount = models.DecimalField("Số tiền", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Dòng hóa đơn"
        verbose_name_plural = "Dòng hóa đơn"

    def __str__(self) -> str:
        return f"{self.fee_item_name_snapshot}: {self.amount}"


class Refund(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField("Số tiền hoàn", max_digits=12, decimal_places=2)
    reason = models.CharField("Lý do", max_length=500, blank=True)
    refunded_at = models.DateTimeField("Thời điểm hoàn")
    refunded_by_user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="refunds_made"
    )

    class Meta:
        verbose_name = "Hoàn tiền"
        verbose_name_plural = "Hoàn tiền"
        ordering = ["-refunded_at"]

    def __str__(self) -> str:
        return f"Hoàn {self.amount} · {self.invoice}"
