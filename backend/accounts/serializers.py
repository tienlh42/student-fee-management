"""Serializer cho đăng nhập và thông tin người dùng hiện tại."""

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User
from .services import role_for


class LoginSerializer(serializers.Serializer):
    """Xác thực username/password. Việc gọi `login()` nằm ở view."""

    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    default_error_messages = {
        "invalid": "Tên đăng nhập hoặc mật khẩu không đúng.",
        "inactive": "Tài khoản đã bị vô hiệu hóa.",
    }

    def validate(self, attrs):
        # authenticate() cần request để các auth backend ghi log/rate-limit đúng.
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            self.fail("invalid")
        if not user.is_active:
            self.fail("inactive")
        attrs["user"] = user
        return attrs


class RoleSerializer(serializers.Serializer):
    """Vai trò suy ra từ dữ liệu (xem accounts/services.py), không phải field trong DB."""

    is_staff_admin = serializers.BooleanField()
    is_teacher = serializers.BooleanField()
    is_guardian = serializers.BooleanField()
    can_see_bank_data = serializers.BooleanField()


class CurrentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    house_ids = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "person_id", "role", "house_ids"]

    def get_full_name(self, user) -> str:
        """Tên hiển thị. Ưu tiên Person — đó mới là nơi nhập họ tên tiếng Việt đầy đủ;
        `first_name`/`last_name` của AbstractUser thường bỏ trống ở dự án này."""
        if user.person_id is not None and user.person.full_name:
            return user.person.full_name
        return user.get_full_name() or user.username

    def get_role(self, user) -> dict:
        return RoleSerializer(role_for(user)).data

    def get_house_ids(self, user) -> list[int]:
        """Cơ sở mà user thuộc về — frontend dùng để điền sẵn form tạo học sinh."""
        from people.models import Teacher

        if user.person_id is None:
            return []
        return list(
            Teacher.objects.filter(person_id=user.person_id).values_list("house_id", flat=True)
        )
