"""Phạm vi truy cập dữ liệu học sinh theo vai trò."""

from django.db import transaction
from django.db.models import Q, QuerySet

from accounts.services import role_for

from .models import Guardian, Person, Student, StudentGuardian, Teacher


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


def teacher_house_ids(user) -> list[int]:
    """Cơ sở mà user được phép ghi dữ liệu. Staff admin: mọi cơ sở."""
    from tenancy.models import House

    if role_for(user).is_staff_admin:
        return list(House.objects.values_list("id", flat=True))

    person_id = getattr(user, "person_id", None)
    if person_id is None:
        return []
    return list(
        Teacher.objects.filter(person_id=person_id).values_list("house_id", flat=True)
    )


def default_house_id(user) -> int | None:
    """Cơ sở mặc định khi tạo học sinh — quy mô hiện tại chỉ có một."""
    houses = teacher_house_ids(user)
    return houses[0] if houses else None


def can_write_in_house(user, house_id) -> bool:
    """Teacher chỉ toàn quyền *trong house của mình* — chặn ghi chéo cơ sở."""
    return house_id in teacher_house_ids(user)


def accessible_guardians(user) -> QuerySet[Guardian]:
    """Phụ huynh gắn với học sinh mà user được xem.

    Guardian tự xem được chính mình, kể cả khi chưa gắn học sinh nào.
    """
    role = role_for(user)
    if role.is_staff_admin:
        return Guardian.objects.all()

    students = accessible_students(user)
    query = Q(student_links__student__in=students)

    person_id = getattr(user, "person_id", None)
    if role.is_guardian and person_id is not None:
        query |= Q(person_id=person_id)

    return Guardian.objects.filter(query).distinct()


def accessible_teachers(user) -> QuerySet[Teacher]:
    if role_for(user).is_staff_admin:
        return Teacher.objects.all()
    return Teacher.objects.filter(house_id__in=teacher_house_ids(user))


@transaction.atomic
def create_student(*, person_data: dict, house, **student_fields) -> Student:
    """Tạo Person rồi Student trong cùng một transaction.

    Student.person là primary key nên không thể tạo Student trước Person.
    """
    person = Person.objects.create(**person_data)
    return Student.objects.create(person=person, house=house, **student_fields)


@transaction.atomic
def update_student(student: Student, *, person_data: dict | None = None, **student_fields) -> Student:
    if person_data:
        for field, value in person_data.items():
            setattr(student.person, field, value)
        student.person.save()

    if student_fields:
        for field, value in student_fields.items():
            setattr(student, field, value)
        student.save()

    return student


@transaction.atomic
def link_guardian(
    student: Student,
    *,
    guardian: Guardian,
    relationship_type: str = StudentGuardian.Relationship.OTHER,
    is_primary_contact: bool = False,
) -> StudentGuardian:
    """Gắn phụ huynh vào học sinh. Chỉ một liên hệ chính cho mỗi học sinh."""
    link, _created = StudentGuardian.objects.update_or_create(
        student=student,
        guardian=guardian,
        defaults={
            "relationship_type": relationship_type,
            "is_primary_contact": is_primary_contact,
        },
    )
    if is_primary_contact:
        StudentGuardian.objects.filter(student=student).exclude(pk=link.pk).update(
            is_primary_contact=False
        )
    return link
