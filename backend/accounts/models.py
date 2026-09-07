from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel


class User(AbstractUser):
    """Custom user. AUTH_USER_MODEL phải trỏ vào đây trước lần migrate đầu tiên."""

    person = models.OneToOneField(
        "people.Person",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user",
        verbose_name="Nhân thân",
    )

    class Meta(AbstractUser.Meta):
        verbose_name = "Người dùng"
        verbose_name_plural = "Người dùng"

    def __str__(self) -> str:
        return self.get_full_name() or self.username


class UserOAuthAccount(TimeStampedModel):
    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        FACEBOOK = "facebook", "Facebook"
        ZALO = "zalo", "Zalo"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="oauth_accounts")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_uid = models.CharField(max_length=255)
    access_token_encrypted = models.TextField(blank=True)

    class Meta:
        verbose_name = "Liên kết OAuth"
        verbose_name_plural = "Liên kết OAuth"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_uid"], name="uniq_oauth_provider_uid"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} · {self.user}"
