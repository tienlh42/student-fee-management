"""Logic nghiệp vụ billing — thuần Python/ORM, không chạm HTTP request.

View/API chỉ gọi vào đây; nhờ vậy test được mà không cần dựng request.
"""

from __future__ import annotations

import calendar
import secrets
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from people.models import Student

from .models import (
    FeePackageItem,
    Invoice,
    InvoiceItem,
    StudentDiscount,
    StudentFeePackage,
)

ZERO = Decimal("0")


@dataclass
class DraftLine:
    fee_item_id: int | None
    name: str
    amount: Decimal


def period_start(day: date) -> date:
    """Chuẩn hóa mọi ngày trong tháng về ngày đầu tháng — khóa duy nhất của kỳ."""
    return day.replace(day=1)


def due_date_for(period: date, due_day_of_month: int) -> date:
    last_day = calendar.monthrange(period.year, period.month)[1]
    return period.replace(day=min(due_day_of_month, last_day))


def generate_reference_code() -> str:
    """Mã tham chiếu ngắn, không nhầm lẫn, để phụ huynh gõ vào nội dung chuyển khoản."""
    alphabet = "ACDEFGHJKLMNPQRTUVWXY3456789"  # bỏ 0/O, 1/I, 2/Z, S/5, B/8
    return "HP" + "".join(secrets.choice(alphabet) for _ in range(8))


def still_open_in(period: date) -> Q:
    """Bản ghi có hiệu lực chưa kết thúc tính đến kỳ đang xét."""
    return Q(effective_until__isnull=True) | Q(effective_until__gte=period)


def active_package_items(student: Student, period: date) -> list[FeePackageItem]:
    """Các khoản thu áp dụng cho học sinh trong kỳ."""
    subs = (
        StudentFeePackage.objects.filter(student=student, effective_from__lte=period)
        .filter(still_open_in(period))
        .select_related("fee_package")
    )
    package_ids = [s.fee_package_id for s in subs if s.fee_package.is_active]
    return list(
        FeePackageItem.objects.filter(fee_package_id__in=package_ids)
        .select_related("fee_item", "fee_package")
        .order_by("fee_item__category", "fee_item__name")
    )


def active_discounts(student: Student, period: date) -> list[StudentDiscount]:
    return list(
        StudentDiscount.objects.filter(
            student=student, is_active=True, effective_from__lte=period
        ).filter(still_open_in(period))
    )


def build_draft_lines(student: Student, period: date) -> list[DraftLine]:
    """Dựng các dòng hóa đơn cho kỳ: khoản thu từ gói, rồi trừ giảm trừ.

    Giảm trừ gắn fee_item -> trừ trực tiếp vào dòng đó.
    Giảm trừ không gắn fee_item -> thành 1 dòng âm riêng trên toàn hóa đơn.
    """
    lines: list[DraftLine] = [
        DraftLine(
            fee_item_id=pi.fee_item_id,
            name=pi.fee_item.name,
            amount=pi.effective_amount,
        )
        for pi in active_package_items(student, period)
    ]

    discounts = active_discounts(student, period)
    subtotal = sum((line.amount for line in lines), ZERO)

    for discount in discounts:
        if discount.fee_item_id is None:
            base = subtotal
        else:
            base = sum(
                (line.amount for line in lines if line.fee_item_id == discount.fee_item_id), ZERO
            )
        if base <= ZERO:
            continue

        if discount.discount_type == StudentDiscount.DiscountType.PERCENTAGE:
            reduction = (base * discount.value / Decimal("100")).quantize(Decimal("1"))
        else:
            reduction = min(discount.value, base)

        lines.append(
            DraftLine(fee_item_id=discount.fee_item_id, name=discount.name, amount=-reduction)
        )

    return lines


@transaction.atomic
def generate_invoice(student: Student, period: date, *, due_day_of_month: int = 5) -> Invoice:
    """Tạo (hoặc trả về) hóa đơn nháp của học sinh cho kỳ đã cho.

    Idempotent: mỗi (student, period) chỉ có đúng 1 hóa đơn.
    """
    period = period_start(period)
    existing = Invoice.objects.filter(student=student, period=period).first()
    if existing is not None:
        return existing

    lines = build_draft_lines(student, period)
    total = sum((line.amount for line in lines), ZERO)

    invoice = Invoice.objects.create(
        house=student.house,
        student=student,
        period=period,
        total_amount=total,
        due_date=due_date_for(period, due_day_of_month),
        qr_reference_code=generate_reference_code(),
        status=Invoice.Status.DRAFT,
    )
    InvoiceItem.objects.bulk_create(
        InvoiceItem(
            invoice=invoice,
            fee_item_id=line.fee_item_id,
            fee_item_name_snapshot=line.name,
            amount=line.amount,
        )
        for line in lines
    )
    return invoice


def recalculate_status(invoice: Invoice) -> Invoice:
    """Đồng bộ status theo net_paid (đã thu - đã hoàn). Gọi sau mỗi lần ghi
    nhận Payment/Refund.

    Dùng `net_paid` (không phải `paid_amount` thô) để hoàn tiền toàn bộ sau
    khi đã thu đủ đưa hóa đơn về đúng lại ISSUED/DRAFT thay vì kẹt ở
    PARTIALLY_PAID (paid_amount vẫn dương dù đã hoàn hết).
    """
    if invoice.status == Invoice.Status.VOID:
        return invoice

    net_paid = invoice.net_paid
    if net_paid >= invoice.net_amount and invoice.net_amount > ZERO:
        invoice.status = Invoice.Status.PAID
    elif net_paid > ZERO:
        invoice.status = Invoice.Status.PARTIALLY_PAID
    elif invoice.status == Invoice.Status.DRAFT:
        return invoice
    else:
        invoice.status = Invoice.Status.ISSUED

    invoice.save(update_fields=["status", "updated_at"])
    return invoice
