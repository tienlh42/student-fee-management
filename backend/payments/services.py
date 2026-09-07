"""Khớp giao dịch tiền vào với hóa đơn.

Ở quy mô này webhook xử lý đồng bộ ngay trong view (không Celery) — nên mọi
thứ ở đây phải nhanh và idempotent.
"""

from __future__ import annotations

import re
from decimal import Decimal

from django.db import transaction

from billing.models import Invoice
from billing.services import recalculate_status

from .models import IncomingTransaction, Payment

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
def record_cash_payment(invoice: Invoice, amount: Decimal, *, user, note: str = "") -> Payment:
    """Thu tiền mặt — không có IncomingTransaction, bắt buộc ghi người thu."""
    if amount <= ZERO:
        raise ValueError("Số tiền thu phải lớn hơn 0.")
    if user is None:
        raise ValueError("Thu tiền mặt bắt buộc ghi nhận người thu.")

    payment = Payment.objects.create(
        transaction=None,
        invoice=invoice,
        amount_applied=amount,
        payment_method=Payment.Method.CASH,
        matched_by=Payment.MatchedBy.MANUAL,
        recorded_by_user=user,
        note=note,
    )
    recalculate_status(invoice)
    return payment


def _refresh_transaction_status(incoming: IncomingTransaction) -> None:
    unallocated = incoming.unallocated_amount
    if unallocated <= ZERO:
        incoming.status = IncomingTransaction.Status.MATCHED
    elif unallocated < incoming.amount:
        incoming.status = IncomingTransaction.Status.PARTIALLY_MATCHED
    else:
        incoming.status = IncomingTransaction.Status.UNMATCHED
    incoming.save(update_fields=["status", "updated_at"])


def build_vietqr_url(invoice: Invoice) -> str | None:
    """URL ảnh VietQR cho hóa đơn.

    Cần số tài khoản đầy đủ, mà BankAccount cố tình chỉ lưu 4 số cuối —
    nên hàm này chưa dùng được cho tới khi quyết định nơi lưu số đầy đủ
    (biến môi trường, hoặc field mã hóa riêng). Xem README.
    """
    return None
