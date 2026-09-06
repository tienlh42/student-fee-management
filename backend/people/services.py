"""Phạm vi truy cập dữ liệu học sinh theo vai trò."""

from django.db.models import QuerySet

from accounts.services import role_for

from .models import Student, Teacher


def accessible_students(user) -> QuerySet[Student]:
    """QuerySet học sinh mà user được phép xem.

    - staff/superuser: tất cả
    - teacher: toàn bộ học sinh trong house của mình
    - guardian: chỉ học sinh liên kết qua StudentGuardian
    - còn lại: rỗng
    """
    role = role_for(user)
    if role.is_staff_admin:
        return Student.objects.all()

    person_id = getattr(user, "person_id", None)
    if person_id is None:
        return Student.objects.none()

    if role.is_teacher:
        house_ids = Teacher.objects.filter(person_id=person_id).values_list("house_id", flat=True)
        return Student.objects.filter(house_id__in=house_ids)

    if role.is_guardian:
        return Student.objects.filter(guardian_links__guardian_id=person_id).distinct()

    return Student.objects.none()
