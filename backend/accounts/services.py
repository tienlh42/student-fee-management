"""Suy ra vai trò từ dữ liệu, không dùng field `role` riêng.

Quy tắc (xem SKILL.md): kiểm tra sự tồn tại của Teacher/Guardian gắn với
Person của request.user để suy ra phạm vi truy cập.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    is_staff_admin: bool
    is_teacher: bool
    is_guardian: bool

    @property
    def can_see_bank_data(self) -> bool:
        """Guardian KHÔNG BAO GIỜ được thấy BankAccount/BankIntegration/IncomingTransaction."""
        return self.is_staff_admin or (self.is_teacher and not self.is_guardian)


def role_for(user) -> Role:
    person_id = getattr(user, "person_id", None)
    if person_id is None:
        return Role(is_staff_admin=bool(user.is_staff), is_teacher=False, is_guardian=False)

    from people.models import Guardian, Teacher

    return Role(
        is_staff_admin=bool(user.is_staff),
        is_teacher=Teacher.objects.filter(person_id=person_id).exists(),
        is_guardian=Guardian.objects.filter(person_id=person_id).exists(),
    )
