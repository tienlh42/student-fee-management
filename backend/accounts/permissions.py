from rest_framework.permissions import BasePermission

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
