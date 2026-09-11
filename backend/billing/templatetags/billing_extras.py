"""Filter dùng riêng cho `invoice_template.html` — khớp format tiền/kỳ của
frontend (`frontend/src/utils/money.js`) để 2 bên hiển thị giống hệt nhau.
"""

from django import template

register = template.Library()


@register.filter
def vnd(value) -> str:
    """1234567 -> "1.234.567 đ" — cùng cách `formatMoney()` bên frontend."""
    n = int(value or 0)
    return f"{n:,}".replace(",", ".") + " đ"


@register.filter
def period_label(value) -> str:
    """date(2026, 9, 1) -> "09/2026" — cùng cách `formatPeriod()` bên frontend."""
    if not value:
        return "—"
    return f"{value.month:02d}/{value.year}"
