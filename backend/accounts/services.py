"""Suy ra vai trò từ dữ liệu, không dùng field `role` riêng.

Quy tắc (xem SKILL.md): kiểm tra sự tồn tại của Teacher/Guardian gắn với
Person của request.user để suy ra phạm vi truy cập.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    # `is_superuser` tách khỏi `is_staff_admin` có chủ đích: staff vào được Django
    # admin, còn superuser mới là người duy nhất được sửa cấu trúc cơ sở (House).
    is_superuser: bool
    is_staff_admin: bool
    is_teacher: bool
    is_guardian: bool

    @property
    def can_see_bank_data(self) -> bool:
        """Guardian KHÔNG BAO GIỜ được thấy BankAccount/BankIntegration/IncomingTransaction."""
        return self.is_staff_admin or (self.is_teacher and not self.is_guardian)

    @property
    def can_manage_houses(self) -> bool:
        """Đổi/thêm/xóa cơ sở là việc của riêng superuser — teacher không đụng vào."""
        return self.is_superuser


def role_for(user) -> Role:
    base = {
        "is_superuser": bool(getattr(user, "is_superuser", False)),
        "is_staff_admin": bool(getattr(user, "is_staff", False)),
    }

    person_id = getattr(user, "person_id", None)
    if person_id is None:
        return Role(**base, is_teacher=False, is_guardian=False)

    from people.models import Guardian, Teacher

    return Role(
        **base,
        is_teacher=Teacher.objects.filter(person_id=person_id).exists(),
        is_guardian=Guardian.objects.filter(person_id=person_id).exists(),
    )
