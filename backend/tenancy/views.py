"""API cho cơ sở. Đọc: ai cũng thấy cơ sở của mình. Ghi: chỉ superuser."""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import CanManageHouses
from accounts.services import role_for

from .models import House
from .serializers import HouseSerializer


class HouseViewSet(viewsets.ModelViewSet):
    serializer_class = HouseSerializer
    permission_classes = [IsAuthenticated, CanManageHouses]

    def get_queryset(self):
        """Superuser thấy tất cả; người khác chỉ thấy cơ sở mình gắn với.

        Danh sách cơ sở lộ ra quy mô tổ chức — không có lý do để một giáo viên
        biết cơ sở khác tồn tại.
        """
        from people.services import houses_of

        if role_for(self.request.user).is_superuser:
            return House.objects.all()
        return House.objects.filter(id__in=[h["id"] for h in houses_of(self.request.user)])
