from django.db import models

from core.models import TimeStampedModel


class House(TimeStampedModel):
    """Một hộ kinh doanh / cơ sở. Hầu hết model khác đều FK về đây."""

    name = models.CharField("Tên cơ sở", max_length=255)
    address = models.CharField("Địa chỉ", max_length=500, blank=True)
    inbound_email_slug = models.SlugField(
        "Slug email nhận thư",
        max_length=63,
        unique=True,
        help_text="Dùng cho địa chỉ nhận mail/webhook riêng của cơ sở.",
    )

    class Meta:
        verbose_name = "Cơ sở"
        verbose_name_plural = "Cơ sở"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
