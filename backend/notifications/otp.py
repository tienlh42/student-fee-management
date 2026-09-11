"""Sinh & xác thực mã OTP gửi qua email.

Lưu ở Postgres (bảng `OtpCode`), không dùng Redis — xem README/thảo luận:
gunicorn chạy nhiều worker (`--workers 3`) nên cache mặc định (LocMemCache,
không dùng chung giữa các worker) không verify được xuyên process; còn thêm
Redis chỉ để lưu OTP là thừa hạ tầng so với quy mô app hiện tại (< 100 user).
"""

from __future__ import annotations

import secrets
import string
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .mail import send_html_mail
from .models import OtpCode

OTP_TTL = timedelta(minutes=5)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5


def request_otp(user, *, purpose: str) -> OtpCode:
    if purpose not in OtpCode.Purpose.values:
        raise ValueError("Mục đích OTP không hợp lệ.")
    if not user.email:
        raise ValueError("Tài khoản chưa có email để nhận mã.")

    cooldown_cutoff = timezone.now() - RESEND_COOLDOWN
    if OtpCode.objects.filter(
        user=user, purpose=purpose, consumed_at__isnull=True, created_at__gt=cooldown_cutoff
    ).exists():
        raise ValueError("Vui lòng đợi ít nhất 60 giây trước khi yêu cầu gửi lại mã.")

    code = "".join(secrets.choice(string.digits) for _ in range(6))
    otp = OtpCode.objects.create(
        user=user,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=timezone.now() + OTP_TTL,
    )

    purpose_display = OtpCode.Purpose(purpose).label
    send_html_mail(
        to_email=user.email,
        subject=f"Mã xác thực EduFi — {purpose_display}",
        template_name="emails/otp.html",
        context={
            "full_name": user.get_full_name() or user.username,
            "purpose_display": purpose_display,
            "code": code,
            "ttl_minutes": int(OTP_TTL.total_seconds() // 60),
        },
        user=user,
        purpose=purpose,
    )
    return otp


def verify_otp(user, *, purpose: str, code: str) -> None:
    otp = (
        OtpCode.objects.filter(
            user=user,
            purpose=purpose,
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )
    if otp is None:
        raise ValueError("Mã đã hết hạn hoặc không tồn tại, vui lòng yêu cầu gửi lại.")
    if otp.attempts >= MAX_ATTEMPTS:
        raise ValueError("Đã nhập sai quá số lần cho phép, vui lòng yêu cầu gửi lại mã.")

    if not check_password(code, otp.code_hash):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise ValueError("Mã không đúng.")

    otp.consumed_at = timezone.now()
    otp.save(update_fields=["consumed_at"])
