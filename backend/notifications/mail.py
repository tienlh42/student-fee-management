"""Gửi email HTML qua SMTP (Gmail cá nhân, cấu hình EMAIL_* trong settings).

Mọi lần gọi đều ghi lại `EmailLog` — kể cả khi gửi lỗi — để tra soát sau này.
"""

from __future__ import annotations

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import EmailLog


def send_html_mail(
    to_email: str,
    subject: str,
    template_name: str,
    context: dict,
    *,
    user=None,
    purpose: str = "",
) -> EmailLog:
    html_body = render_to_string(template_name, context)
    message = EmailMultiAlternatives(subject, strip_tags(html_body), to=[to_email])
    message.attach_alternative(html_body, "text/html")

    try:
        message.send()
    except Exception as exc:
        EmailLog.objects.create(
            to_email=to_email,
            subject=subject,
            purpose=purpose,
            user=user,
            status=EmailLog.Status.FAILED,
            error_message=str(exc),
        )
        raise

    return EmailLog.objects.create(
        to_email=to_email,
        subject=subject,
        purpose=purpose,
        user=user,
        status=EmailLog.Status.SENT,
    )
