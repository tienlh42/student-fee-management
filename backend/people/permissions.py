"""Kiểm tra quyền ở mức từng bản ghi cho app people.

`accounts.permissions.IsTeacherOrReadOnly` chỉ chặn theo *động từ* (guardian
không được ghi). Ở đây chặn theo *cơ sở*: teacher của cơ sở A không được sửa
bản ghi thuộc cơ sở B, kể cả khi payload không gửi kèm field `house`.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .services import can_write_in_house


def house_ids_of(obj) -> set[int]:
    """Cơ sở mà một bản ghi thuộc về.

    Không phải model nào cũng có FK `house` trực tiếp — Guardian suy ra qua
    các học sinh liên kết, TeachingAssignment suy ra qua học sinh được phân công.
    """
    if (house_id := getattr(obj, "house_id", None)) is not None:
        return {house_id}
    if (student := getattr(obj, "student", None)) is not None:
        return {student.house_id}
    if hasattr(obj, "student_links"):
        return set(obj.student_links.values_list("student__house_id", flat=True))
    return set()


class WritableWithinOwnHouse(BasePermission):
    message = "Bản ghi này thuộc cơ sở khác."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        house_ids = house_ids_of(obj)
        if not house_ids:
            # Bản ghi chưa gắn cơ sở nào (vd phụ huynh mới tạo, chưa có học sinh):
            # chỉ cần là teacher ở đâu đó — điều kiện đó IsTeacherOrReadOnly đã lo.
            return True
        return all(can_write_in_house(request.user, hid) for hid in house_ids)
