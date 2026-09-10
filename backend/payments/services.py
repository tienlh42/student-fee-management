"""Khớp giao dịch tiền vào với hóa đơn.

Ở quy mô này webhook xử lý đồng bộ ngay trong view (không Celery) — nên mọi
thứ ở đây phải nhanh và idempotent.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from urllib.parse import quote

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from billing.models import Invoice, Refund
from billing.services import recalculate_status
from notifications.models import Notification
from people.models import Student

from .models import BankAccount, IncomingTransaction, Payment

ZERO = Decimal("0")
REFERENCE_RE = re.compile(r"HP[ACDEFGHJKLMNPQRTUVWXY3456789]{8}", re.IGNORECASE)


def extract_reference_codes(transfer_content: str) -> list[str]:
    """Rút mã hóa đơn khỏi nội dung chuyển khoản.

    Ngân hàng hay bỏ dấu, chèn ký tự lạ và viết hoa/thường lẫn lộn — chỉ dựa
    vào pattern cố định của mã, không dựa vào tên người chuyển.
    """
    normalized = re.sub(r"[^A-Za-z0-9]", "", transfer_content or "")
    return [m.group(0).upper() for m in REFERENCE_RE.finditer(normalized)]


@transaction.atomic
def try_auto_match(incoming: IncomingTransaction) -> list[Payment]:
    """Tự khớp giao dịch vào hóa đơn tìm được qua mã tham chiếu.

    Idempotent: gọi lại trên giao dịch đã khớp hết sẽ không tạo Payment mới.
    Trả về danh sách Payment vừa tạo (rỗng nếu không khớp được gì).
    """
    remaining = incoming.unallocated_amount
    if remaining <= ZERO or incoming.status == IncomingTransaction.Status.IGNORED:
        return []

    codes = extract_reference_codes(incoming.transfer_content)
    if not codes:
        return []

    invoices = list(
        Invoice.objects.select_for_update()
        .filter(house=incoming.house, qr_reference_code__in=codes)
        .exclude(status=Invoice.Status.VOID)
        .order_by("due_date")
    )
    if not invoices:
        return []

    created: list[Payment] = []
    for invoice in invoices:
        if remaining <= ZERO:
            break
        outstanding = invoice.outstanding_amount
        if outstanding <= ZERO:
            continue

        applied = min(remaining, outstanding)
        created.append(
            Payment.objects.create(
                transaction=incoming,
                invoice=invoice,
                amount_applied=applied,
                payment_method=Payment.Method.BANK_TRANSFER,
                matched_by=Payment.MatchedBy.AUTO,
            )
        )
        remaining -= applied
        recalculate_status(invoice)

    _refresh_transaction_status(incoming)
    return created


@transaction.atomic
def allocate_manually(
    incoming: IncomingTransaction, invoice: Invoice, amount: Decimal, *, user
) -> Payment:
    """Kế toán tự tay gán một phần giao dịch vào hóa đơn."""
    if amount <= ZERO:
        raise ValueError("Số tiền phân bổ phải lớn hơn 0.")
    if amount > incoming.unallocated_amount:
        raise ValueError("Số tiền phân bổ vượt quá phần chưa khớp của giao dịch.")

    payment = Payment.objects.create(
        transaction=incoming,
        invoice=invoice,
        amount_applied=amount,
        payment_method=Payment.Method.BANK_TRANSFER,
        matched_by=Payment.MatchedBy.MANUAL,
        recorded_by_user=user,
    )
    recalculate_status(invoice)
    _refresh_transaction_status(incoming)
    return payment


@transaction.atomic
def record_manual_payment(
    invoice: Invoice, amount: Decimal, *, method: str, user, note: str = ""
) -> Payment:
    """Ghi nhận thanh toán thủ công — không qua khớp giao dịch ngân hàng tự động
    (tiền mặt, hoặc chuyển khoản không tới qua webhook). Bắt buộc ghi người thu
    để truy trách nhiệm.

    Gọi nhiều lần cho cùng một hóa đơn để chia thành nhiều đợt thanh toán —
    mỗi lần gọi là một `Payment` riêng, `recalculate_status` tự cộng dồn.
    """
    if amount <= ZERO:
        raise ValueError("Số tiền thu phải lớn hơn 0.")
    if user is None:
        raise ValueError("Ghi nhận thanh toán bắt buộc kèm người thu.")
    if method not in Payment.Method.values:
        raise ValueError("Hình thức thanh toán không hợp lệ.")

    payment = Payment.objects.create(
        transaction=None,
        invoice=invoice,
        amount_applied=amount,
        payment_method=method,
        matched_by=Payment.MatchedBy.MANUAL,
        recorded_by_user=user,
        note=note,
    )
    recalculate_status(invoice)
    return payment


@transaction.atomic
def process_refund(
    invoice: Invoice,
    amount: Decimal,
    *,
    cancel_obligation: bool,
    method: str,
    user,
    reason: str = "",
    payment: Payment | None = None,
) -> Refund:
    """Hoàn tiền cho một hóa đơn — chỉ ghi thêm một `Refund`, không sửa/xóa
    Payment cũ. Quy trình tối giản (chưa có bước duyệt), hai lựa chọn độc
    lập ở đầu vào (amount, cancel_obligation) bao quát cả 4 tổ hợp
    đóng đủ/một phần × hoàn hết/hoàn một phần:

    - `cancel_obligation=True`: học sinh không còn nợ khoản này nữa (nghỉ
      học, hủy dịch vụ...) — đưa hóa đơn về VOID kèm lý do, KHÔNG đổi
      `total_amount`. `void`/`restore` tay vẫn là một action riêng, độc lập.
    - `cancel_obligation=False`: khoản phí vẫn còn hiệu lực, chỉ điều chỉnh
      lại số đã nộp (đóng nhầm, thu dư...) — status tự suy lại theo
      `net_paid` qua `recalculate_status`, không có state riêng cho "đã hoàn
      tiền".
    - `method=Refund.Method.CREDIT`: không chuyển tiền ra ngoài — cộng vào
      `credit_balance` của học sinh để trừ dần vào hóa đơn kỳ sau.

    Khóa hàng `Invoice` (`select_for_update`) trước khi đọc `net_paid` — hai
    yêu cầu hoàn tiền cùng lúc cho cùng hóa đơn (double-click, hai người cùng
    thao tác) phải xếp hàng chứ không được cùng đọc `net_paid` cũ rồi cùng
    vượt qua kiểm tra, khiến tổng hoàn vượt quá số đã thực nhận.
    """
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)

    if amount <= ZERO:
        raise ValueError("Số tiền hoàn phải lớn hơn 0.")
    if amount > invoice.net_paid:
        raise ValueError("Số tiền hoàn không được vượt quá số đã thực nhận.")
    if user is None:
        raise ValueError("Hoàn tiền bắt buộc ghi người thực hiện.")
    if method not in Refund.Method.values:
        raise ValueError("Phương thức hoàn không hợp lệ.")

    refund = Refund.objects.create(
        invoice=invoice,
        payment=payment,
        amount=amount,
        method=method,
        reason=reason,
        refunded_at=timezone.now(),
        refunded_by_user=user,
        # Hệ thống chưa theo dõi hóa đơn điện tử — luôn False cho tới khi có
        # tính năng đó (xem help_text trên field). Không chặn luồng ở đây.
        needs_adjustment_invoice=False,
    )

    if method == Refund.Method.CREDIT:
        Student.objects.filter(pk=invoice.student_id).update(
            credit_balance=F("credit_balance") + amount
        )

    if cancel_obligation:
        invoice.status = Invoice.Status.VOID
        invoice.cancel_reason = reason
        invoice.save(update_fields=["status", "cancel_reason", "updated_at"])
    else:
        recalculate_status(invoice)

    Notification.objects.create(
        house=invoice.house,
        student=invoice.student,
        title=f"Xác nhận hoàn tiền hóa đơn {invoice.qr_reference_code}",
        body=(
            f"Đã hoàn {amount} cho hóa đơn kỳ {invoice.period:%m/%Y} "
            f"({Refund.Method(method).label})."
            + (f" Lý do: {reason}" if reason else "")
        ),
        created_by_user=user,
        published_at=timezone.now(),
    )

    return refund


def _refresh_transaction_status(incoming: IncomingTransaction) -> None:
    unallocated = incoming.unallocated_amount
    if unallocated <= ZERO:
        incoming.status = IncomingTransaction.Status.MATCHED
    elif unallocated < incoming.amount:
        incoming.status = IncomingTransaction.Status.PARTIALLY_MATCHED
    else:
        incoming.status = IncomingTransaction.Status.UNMATCHED
    incoming.save(update_fields=["status", "updated_at"])


def _strip_accents(text: str) -> str:
    """VietQR yêu cầu tên chủ tài khoản không dấu."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def build_vietqr_url(invoice: Invoice) -> str | None:
    """URL ảnh VietQR (quick-link của VietQR.io) cho hóa đơn.

    None nếu house chưa cấu hình BankAccount, hoặc hóa đơn không còn số tiền
    phải thu (đã thanh toán đủ) — không có lý do gì để hiện QR nữa.
    """
    try:
        bank_account = invoice.house.bank_account
    except BankAccount.DoesNotExist:
        return None

    amount = invoice.outstanding_amount
    if amount <= ZERO:
        return None

    account_number = bank_account.get_account_number()
    account_name = quote(_strip_accents(bank_account.account_holder_name).upper())
    content = quote(invoice.qr_reference_code)
    return (
        f"https://img.vietqr.io/image/{bank_account.bank_code}-{account_number}-compact2.png"
        f"?amount={int(amount)}&addInfo={content}&accountName={account_name}"
    )
