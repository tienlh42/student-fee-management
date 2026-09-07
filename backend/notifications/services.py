"""Đọc/ghi thông báo theo phạm vi của người dùng."""

from __future__ import annotations

from django.db.models import Q, QuerySet
from django.utils import timezone

from people.services import accessible_students

from .models import Notification, NotificationRead


def visible_notifications(user) -> QuerySet[Notification]:
    """Thông báo đã đăng mà user được thấy.

    Thông báo toàn cơ sở (student=None) chỉ hiện với người thuộc cơ sở đó;
    thông báo riêng chỉ hiện với người có quyền trên học sinh tương ứng.
    """
    students = accessible_students(user)
    house_ids = set(students.values_list("house_id", flat=True))
    student_ids = set(students.values_list("person_id", flat=True))

    return (
        Notification.objects.filter(published_at__isnull=False)
        .filter(
            Q(student_id__in=student_ids)
            | Q(student__isnull=True, house_id__in=house_ids)
        )
        .distinct()
    )


def publish(notification: Notification) -> Notification:
    if notification.published_at is None:
        notification.published_at = timezone.now()
        notification.save(update_fields=["published_at", "updated_at"])
    return notification


def mark_read(notification: Notification, user) -> NotificationRead:
    obj, _created = NotificationRead.objects.get_or_create(notification=notification, user=user)
    return obj


def unread_count(user) -> int:
    return (
        visible_notifications(user)
        .exclude(reads__user=user)
        .count()
    )
