"""Payments trả lời câu hỏi: "tiền về từ đâu, khớp vào hóa đơn nào".

Tách khỏi `billing` có chủ đích: billing đổi theo nghiệp vụ, payments đổi theo
API bên thứ ba (SePay). Guardian KHÔNG BAO GIỜ được đọc dữ liệu trong app này.
"""

from django.db import models

from core.models import CreatedAtModel, TimeStampedModel

from .bank_list import NAPAS_BANKS
from .crypto import decrypt_account_number, encrypt_account_number


class BankAccount(TimeStampedModel):
    """Tài khoản nhận tiền của một house — nguồn dữ liệu để sinh VietQR.

    Số tài khoản lưu mã hoá (`account_number_encrypted`), không bao giờ ở dạng
    thô trong DB. `bank_code` là mã BIN theo chuẩn Napas (xem `bank_list.py`),
    bắt buộc để VietQR định danh đúng ngân hàng.
    """

    house = models.OneToOneField(
        "tenancy.House", on_delete=models.CASCADE, related_name="bank_account"
    )
    bank_code = models.CharField("Ngân hàng", max_length=20, choices=NAPAS_BANKS)
    account_number_encrypted = models.TextField("Số tài khoản (mã hóa)")
    account_holder_name = models.CharField("Chủ tài khoản", max_length=255)

    class Meta:
        verbose_name = "Tài khoản ngân hàng"
        verbose_name_plural = "Tài khoản ngân hàng"

    def __str__(self) -> str:
        return f"{self.bank_code} ****{self.account_number_last4}"

    def set_account_number(self, raw: str) -> None:
        digits = raw.strip()
        if not digits.isdigit():
            raise ValueError("Số tài khoản chỉ gồm chữ số.")
        self.account_number_encrypted = encrypt_account_number(digits)

    def get_account_number(self) -> str:
        return decrypt_account_number(self.account_number_encrypted)

    @property
    def account_number_last4(self) -> str:
        return self.get_account_number()[-4:]


class BankAccountRevealLog(CreatedAtModel):
    """Ghi lại mỗi lần admin xem số tài khoản đầy đủ — append-only, không xoá."""

    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="reveal_logs"
    )
    revealed_by_user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="bank_account_reveals"
    )

    class Meta:
        verbose_name = "Lượt xem số tài khoản"
        verbose_name_plural = "Lượt xem số tài khoản"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.revealed_by_user} xem {self.bank_account} lúc {self.created_at:%d/%m/%Y %H:%M}"


class BankIntegration(TimeStampedModel):
    class Provider(models.TextChoices):
        SEPAY = "sepay", "SePay"

    house = models.OneToOneField(
        "tenancy.House", on_delete=models.CASCADE, related_name="bank_integration"
    )
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.SEPAY)
    sepay_account_id = models.CharField("SePay account id", max_length=100, blank=True)
    api_key_encrypted = models.TextField("API key (mã hóa)", blank=True)
    webhook_secret = models.CharField("Webhook secret", max_length=255, blank=True)

    class Meta:
        verbose_name = "Kết nối ngân hàng"
        verbose_name_plural = "Kết nối ngân hàng"

    def __str__(self) -> str:
        return f"{self.get_provider_display()} · {self.house}"


class IncomingTransaction(TimeStampedModel):
    """Một giao dịch tiền vào, nhận qua webhook SePay."""

    class Status(models.TextChoices):
        UNMATCHED = "unmatched", "Chưa khớp"
        PARTIALLY_MATCHED = "partially_matched", "Khớp một phần"
        MATCHED = "matched", "Đã khớp"
        IGNORED = "ignored", "Bỏ qua"

    house = models.ForeignKey(
        "tenancy.House", on_delete=models.CASCADE, related_name="incoming_transactions"
    )
    amount = models.DecimalField("Số tiền", max_digits=12, decimal_places=2)
    transfer_content = models.CharField("Nội dung chuyển khoản", max_length=500, blank=True)
    transaction_time = models.DateTimeField("Thời điểm giao dịch")
    status = models.CharField(
        "Trạng thái", max_length=20, choices=Status.choices, default=Status.UNMATCHED
    )
    source = models.CharField("Nguồn", max_length=50, default="webhook_sepay")
    provider_transaction_id = models.CharField(
        "Mã giao dịch bên cung cấp", max_length=100, unique=True,
        help_text="Khóa chống ghi trùng khi webhook gửi lại.",
    )
    raw_payload = models.JSONField("Payload gốc", default=dict, blank=True)

    class Meta:
        verbose_name = "Giao dịch tiền vào"
        verbose_name_plural = "Giao dịch tiền vào"
        ordering = ["-transaction_time"]
        indexes = [models.Index(fields=["house", "status", "transaction_time"])]

    def __str__(self) -> str:
        return f"{self.amount} · {self.transaction_time:%d/%m/%Y}"

    @property
    def allocated_amount(self):
        from decimal import Decimal

        agg = self.payments.aggregate(total=models.Sum("amount_applied"))
        return agg["total"] or Decimal("0")

    @property
    def unallocated_amount(self):
        return self.amount - self.allocated_amount


class Payment(CreatedAtModel):
    """Phân bổ tiền vào một hóa đơn. Một giao dịch có thể trả nhiều hóa đơn."""

    class Method(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Chuyển khoản"
        CASH = "cash", "Tiền mặt"
        OTHER = "other", "Khác"

    class MatchedBy(models.TextChoices):
        AUTO = "auto", "Tự động"
        MANUAL = "manual", "Thủ công"

    transaction = models.ForeignKey(
        IncomingTransaction,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
        help_text="Bỏ trống nếu thu tiền mặt.",
    )
    invoice = models.ForeignKey(
        "billing.Invoice", on_delete=models.PROTECT, related_name="payments"
    )
    amount_applied = models.DecimalField("Số tiền phân bổ", max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        "Hình thức", max_length=20, choices=Method.choices, default=Method.BANK_TRANSFER
    )
    matched_by = models.CharField(
        "Cách khớp", max_length=10, choices=MatchedBy.choices, default=MatchedBy.MANUAL
    )
    recorded_by_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments_recorded",
        help_text="Bắt buộc trên thực tế với thu tiền mặt — để truy trách nhiệm.",
    )
    note = models.CharField("Ghi chú", max_length=500, blank=True)

    class Meta:
        verbose_name = "Thanh toán"
        verbose_name_plural = "Thanh toán"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["invoice", "created_at"])]

    def __str__(self) -> str:
        return f"{self.amount_applied} -> {self.invoice}"
