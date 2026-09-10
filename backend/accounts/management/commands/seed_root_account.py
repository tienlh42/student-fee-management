"""Tạo/đồng bộ tài khoản root (superuser) từ biến môi trường.

    docker compose -f docker-compose.dev.yml exec web python manage.py seed_root_account

Đọc `ROOT_ACCOUNT_USERNAME`/`ROOT_ACCOUNT_PASSWORD` (khai ở `.env`, xem
`.env.example`). Idempotent nhưng KHÁC `seed_demo`: mỗi lần chạy đều đồng bộ
lại mật khẩu từ env — đây là tài khoản break-glass, đổi
`ROOT_ACCOUNT_PASSWORD` rồi chạy lại lệnh chính là cách reset. Không từ chối
chạy khi `DEBUG=False` (ngược với `seed_demo`) vì đây là lệnh bootstrap cần
dùng được ở production.
"""

from __future__ import annotations

from decouple import config as env
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Tạo/đồng bộ tài khoản root từ ROOT_ACCOUNT_USERNAME/ROOT_ACCOUNT_PASSWORD."

    def handle(self, *args, **options):
        username = env("ROOT_ACCOUNT_USERNAME", default="")
        password = env("ROOT_ACCOUNT_PASSWORD", default="")
        if not username or not password:
            raise CommandError(
                "Thiếu ROOT_ACCOUNT_USERNAME/ROOT_ACCOUNT_PASSWORD — khai ở .env "
                "(xem .env.example)."
            )

        # Ngoài DEBUG (production) thì không cho lọt mật khẩu mặc định/yếu —
        # trong DEBUG bỏ qua để bootstrap dev vẫn chạy được bằng một lệnh.
        if not settings.DEBUG:
            try:
                validate_password(password)
            except DjangoValidationError as exc:
                raise CommandError(
                    "ROOT_ACCOUNT_PASSWORD không đủ mạnh cho production: "
                    + " ".join(exc.messages)
                )

        with transaction.atomic():
            user, created = User.objects.get_or_create(username=username)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            # Luôn đồng bộ mật khẩu — không giữ nguyên như seed_demo, vì đây
            # là tài khoản break-glass điều khiển hoàn toàn qua env.
            user.set_password(password)
            user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Đã tạo tài khoản root '{username}'."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Tài khoản root '{username}' đã tồn tại — đã đồng bộ lại quyền và mật khẩu."
                )
            )
