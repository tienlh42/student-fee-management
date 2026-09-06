"""Serializer cho đăng nhập, thông tin người dùng hiện tại và hồ sơ cá nhân."""

from django.contrib.auth import authenticate
from django.db import transaction
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

    is_superuser = serializers.BooleanField()
    is_staff_admin = serializers.BooleanField()
    is_teacher = serializers.BooleanField()
    is_guardian = serializers.BooleanField()
    can_see_bank_data = serializers.BooleanField()
    can_manage_houses = serializers.BooleanField()


class HouseMembershipSerializer(serializers.Serializer):
    """Cơ sở của user — luôn chỉ đọc, kể cả trên màn hình hồ sơ cá nhân."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    via = serializers.CharField()
    via_display = serializers.CharField()


def display_name(user) -> str:
    """Tên hiển thị. Ưu tiên Person — đó mới là nơi nhập họ tên tiếng Việt đầy đủ;
    `first_name`/`last_name` của AbstractUser thường bỏ trống ở dự án này."""
    if user.person_id is not None and user.person.full_name:
        return user.person.full_name
    return user.get_full_name() or user.username


class CurrentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    house_ids = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "person_id", "role", "house_ids"]

    def get_full_name(self, user) -> str:
        return display_name(user)

    def get_role(self, user) -> dict:
        return RoleSerializer(role_for(user)).data

    def get_house_ids(self, user) -> list[int]:
        """Cơ sở mà user được phép *ghi* — frontend dùng để điền sẵn form tạo học sinh.

        Khác với `houses` ở hồ sơ cá nhân: chỗ đó liệt kê cả cơ sở chỉ-đọc mà
        phụ huynh nhìn thấy qua con mình.
        """
        from people.services import teacher_house_ids

        return teacher_house_ids(user)


class ProfileSerializer(serializers.Serializer):
    """Hồ sơ của chính người đang đăng nhập.

    Gộp hai bản ghi vào một payload: `User` (đăng nhập) và `Person` (nhân thân).
    `house` **không** nằm trong danh sách ghi được — xem `CanManageHouses`.
    """

    username = serializers.CharField(read_only=True)
    account_email = serializers.EmailField(source="email", required=False, allow_blank=True)
    person = serializers.SerializerMethodField()
    houses = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    def get_person(self, user) -> dict | None:
        from people.serializers import PersonSerializer

        if user.person_id is None:
            return None
        return PersonSerializer(user.person).data

    def get_houses(self, user) -> list[dict]:
        from people.services import houses_of

        return HouseMembershipSerializer(houses_of(user), many=True).data

    def get_role(self, user) -> dict:
        return RoleSerializer(role_for(user)).data

    def to_internal_value(self, data):
        from people.serializers import PersonSerializer

        validated = super().to_internal_value(data)

        if "person" in data:
            existing = self.instance.person if self.instance.person_id else None
            person_serializer = PersonSerializer(
                instance=existing,
                data=data["person"],
                # Chưa có Person thì đây là lần tạo mới -> `full_name` phải bắt buộc,
                # partial=True sẽ cho lọt một Person không tên.
                partial=self.partial and existing is not None,
            )
            person_serializer.is_valid(raise_exception=True)
            validated["person"] = person_serializer.validated_data

        return validated

    @transaction.atomic
    def update(self, user, validated_data):
        from people.models import Person

        person_data = validated_data.pop("person", None)
        if person_data:
            if user.person_id is None:
                # Tài khoản tạo bằng createsuperuser chưa có Person nào — lần
                # đầu tự điền hồ sơ thì tạo luôn, không bắt vào Django admin.
                user.person = Person.objects.create(**person_data)
            else:
                for field, value in person_data.items():
                    setattr(user.person, field, value)
                user.person.save()

        if "email" in validated_data:
            user.email = validated_data["email"]

        user.save()
        return user
