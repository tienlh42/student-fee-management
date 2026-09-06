from rest_framework.permissions import SAFE_METHODS, BasePermission

from .services import role_for


class IsTeacher(BasePermission):
    """Teacher: toàn quyền trong house của mình."""

    def has_permission(self, request, view):
        role = role_for(request.user)
        return role.is_teacher or role.is_staff_admin


class CanSeeBankData(BasePermission):
    """Chặn Guardian khỏi mọi dữ liệu ngân hàng nội bộ của house."""

    def has_permission(self, request, view):
        return role_for(request.user).can_see_bank_data


class IsTeacherOrReadOnly(BasePermission):
    """Guardian chỉ đọc; mọi thao tác ghi đòi Teacher (hoặc staff admin).

    Phạm vi *dòng dữ liệu* nào được đọc vẫn do queryset của view giới hạn
    (`people.services.accessible_students`) — permission này chỉ chặn theo động từ.
    """

    message = "Chỉ giáo viên mới được thay đổi dữ liệu này."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        role = role_for(request.user)
        return role.is_teacher or role.is_staff_admin


class CanManageHouses(BasePermission):
    """Đọc: mọi người đã đăng nhập. Ghi: chỉ superuser.

    Cơ sở là gốc của toàn bộ dữ liệu — đổi tên hay xóa nhầm sẽ kéo theo học sinh,
    hóa đơn, giao dịch. Teacher không có lý do gì phải sửa nó.
    """

    message = "Chỉ quản trị viên cấp cao mới được thay đổi cơ sở."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return role_for(request.user).can_manage_houses
