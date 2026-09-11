"""Serializer cho đăng nhập, thông tin người dùng hiện tại và hồ sơ cá nhân."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.crypto import get_random_string
from rest_framework import serializers

from .models import User
from .services import email_taken, role_for, save_user_role


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


class ForgotPasswordLookupSerializer(serializers.Serializer):
    """Xác nhận username + email khớp cùng một tài khoản — dùng chung cho cả
    bước gửi OTP và bước xác thực/đổi mật khẩu. Gộp lỗi "sai username" và "sai
    email" thành một thông báo, giống `LoginSerializer`, để không lộ tài khoản
    nào tồn tại."""

    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)

    default_error_messages = {
        "not_found": "Không tìm thấy tài khoản khớp với thông tin đã nhập.",
    }

    def validate(self, attrs):
        user = User.objects.filter(
            username=attrs["username"], email__iexact=attrs["email"], is_active=True
        ).first()
        if user is None:
            self.fail("not_found")
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
    can_manage_users = serializers.BooleanField()


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

    def validate_account_email(self, value):
        if email_taken(value, exclude_user_id=self.instance.pk):
            raise serializers.ValidationError("Email này đã được dùng cho tài khoản khác.")
        return value

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


class UserSerializer(serializers.ModelSerializer):
    """CRUD tài khoản đăng nhập cho màn Quản trị (root/superuser).

    `role_kind`/`role_house`/`role_full_name` không phải field của `User` —
    chỉ input để `save_user_role` (accounts/services.py) gán/gỡ Teacher hay
    Guardian gắn với `person` của tài khoản, trong cùng một request.
    """

    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={"input_type": "password"}
    )
    person_id = serializers.IntegerField(read_only=True)
    person_full_name = serializers.CharField(
        source="person.full_name", read_only=True, default=""
    )
    role_kind = serializers.ChoiceField(
        choices=["teacher", "guardian", ""], write_only=True, required=False, allow_blank=True
    )
    role_house = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    role_full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    current_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "password",
            "person_id",
            "person_full_name",
            "current_role",
            "role_kind",
            "role_house",
            "role_full_name",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

    def get_current_role(self, obj) -> dict:
        """Vai trò *hiện tại* (đọc) — khác `role_kind` (input để đổi vai trò).
        Dùng để điền sẵn form sửa và hiển thị cột "Vai trò" ở danh sách."""
        from people.models import Guardian, Teacher

        if obj.person_id is None:
            return {"kind": "", "house": None, "house_name": ""}

        teacher = Teacher.objects.filter(pk=obj.person_id).select_related("house").first()
        if teacher is not None:
            return {"kind": "teacher", "house": teacher.house_id, "house_name": teacher.house.name}

        if Guardian.objects.filter(pk=obj.person_id).exists():
            return {"kind": "guardian", "house": None, "house_name": ""}

        return {"kind": "", "house": None, "house_name": ""}

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def validate_email(self, value):
        if email_taken(value, exclude_user_id=self.instance.pk if self.instance else None):
            raise serializers.ValidationError("Email này đã được dùng cho tài khoản khác.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        role_kind = validated_data.pop("role_kind", "")
        role_house = validated_data.pop("role_house", None)
        role_full_name = validated_data.pop("role_full_name", "")
        password = validated_data.pop("password", "") or None

        user = User(**validated_data)
        user.set_password(password or get_random_string(32))
        user.save()

        if role_kind:
            save_user_role(
                user, kind=role_kind, house_id=role_house, full_name=role_full_name
            )
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        role_kind = validated_data.pop("role_kind", None)
        role_house = validated_data.pop("role_house", None)
        role_full_name = validated_data.pop("role_full_name", "")
        password = validated_data.pop("password", "")

        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()

        if role_kind is not None:
            save_user_role(
                instance, kind=role_kind, house_id=role_house, full_name=role_full_name
            )
        return instance
