"""Logic nghiệp vụ thuần cho tenancy — không phụ thuộc HTTP request."""

from .models import House


def get_default_house() -> House | None:
    """Ở quy mô 1 cơ sở, nhiều màn hình chỉ cần House duy nhất."""
    return House.objects.order_by("id").first()
