"""Suy ra vai trò từ dữ liệu, không dùng field `role` riêng.

Quy tắc (xem SKILL.md): kiểm tra sự tồn tại của Teacher/Guardian gắn với
Person của request.user để suy ra phạm vi truy cập.
"""

from dataclasses import dataclass

from django.db import transaction


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

    @property
    def can_manage_users(self) -> bool:
        """CRUD tài khoản đăng nhập cũng là việc của riêng superuser.

        Tách riêng khỏi `can_manage_houses` dù hiện cùng bằng `is_superuser` —
        hai khả năng khái niệm khác nhau (cấu trúc cơ sở vs. tài khoản đăng
        nhập), có thể tách rời sau này.
        """
        return self.is_superuser

    @property
    def can_manage_bank_accounts(self) -> bool:
        """Cấu hình tài khoản nhận tiền (để sinh VietQR) — chỉ superuser, kể cả
        đọc: khác `can_manage_houses` (đọc mở cho mọi người đăng nhập), số tài
        khoản dù đã mã hoá vẫn không có lý do gì lộ ra cho teacher/guardian.
        """
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


@transaction.atomic
def save_user_role(user, *, kind: str, house_id: int | None, full_name: str) -> None:
    """Gán/gỡ vai trò Teacher/Guardian của `user` — dùng bởi màn Quản trị tài
    khoản (root). Chỉ gọi sau khi `CanManageUsers` đã chặn ở view — vì vậy
    KHÔNG gọi `people.services.can_write_in_house` (chặn teacher ghi chéo cơ
    sở, không áp dụng cho root, root được gán house bất kỳ).

    `kind` rỗng = gỡ vai trò hiện có (soft delete, giữ lịch sử). `"teacher"`/
    `"guardian"` = gán vai trò đó, tạo `Person` nếu user chưa có, và khôi phục
    lại bản ghi Teacher/Guardian cũ (qua `all_objects`) thay vì tạo mới —
    `person` là PK nên tạo mới đè lên bản ghi đã xóa mềm sẽ đụng IntegrityError.
    """
    from people.models import Guardian, Person, Teacher

    if kind not in ("teacher", "guardian", "", None):
        raise ValueError("Vai trò không hợp lệ.")

    if not kind:
        if user.person_id:
            Teacher.objects.filter(pk=user.person_id).delete()
            Guardian.objects.filter(pk=user.person_id).delete()
        return

    if not full_name:
        raise ValueError("Cần nhập họ tên khi gán vai trò.")

    if user.person_id:
        person = user.person
        person.full_name = full_name
        person.save(update_fields=["full_name"])
    else:
        person = Person.objects.create(full_name=full_name)
        user.person = person
        user.save(update_fields=["person"])

    if kind == "teacher":
        if not house_id:
            raise ValueError("Cần chọn cơ sở cho giáo viên.")
        Guardian.objects.filter(pk=person.pk).delete()
        teacher = Teacher.all_objects.filter(pk=person.pk).first()
        if teacher is None:
            Teacher.objects.create(person=person, house_id=house_id)
        else:
            if teacher.is_deleted:
                teacher.restore()
            teacher.house_id = house_id
            teacher.save(update_fields=["house_id"])
    else:
        Teacher.objects.filter(pk=person.pk).delete()
        guardian = Guardian.all_objects.filter(pk=person.pk).first()
        if guardian is None:
            Guardian.objects.create(person=person)
        elif guardian.is_deleted:
            guardian.restore()
