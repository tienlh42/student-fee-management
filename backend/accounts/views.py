"""Đăng nhập/đăng xuất bằng session — same-origin nên không cần JWT.

DRF `APIView` tự bọc `csrf_exempt`, và `SessionAuthentication` chỉ kiểm CSRF
với request đã đăng nhập. Login là request *chưa* đăng nhập nên phải tự gắn
`csrf_protect`, nếu không endpoint này hở CSRF.
"""

from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import OtpCode
from notifications.otp import request_otp, verify_otp

from .models import User
from .permissions import CanManageUsers
from .serializers import (
    CurrentUserSerializer,
    ForgotPasswordLookupSerializer,
    LoginSerializer,
    ProfileSerializer,
    UserSerializer,
)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        # Xoay session key sau khi xác thực -> chặn session fixation.
        django_login(request, serializer.validated_data["user"])
        return Response(CurrentUserSerializer(request.user).data)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name="dispatch")
class ForgotPasswordRequestView(APIView):
    """Bước 1 quên mật khẩu: khớp username+email rồi gửi OTP qua email.

    Request chưa đăng nhập nên cần tự gắn `csrf_protect`, giống `LoginView`.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        try:
            request_otp(user, purpose=OtpCode.Purpose.RESET_PASSWORD)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name="dispatch")
class ForgotPasswordConfirmView(APIView):
    """Bước 2: xác thực OTP rồi đặt mật khẩu mới — vẫn chưa cần đăng nhập.

    Gộp xác thực OTP + đổi mật khẩu trong một request duy nhất, không lưu
    trạng thái "đã xác thực" tạm ở giữa hai bước — đơn giản hơn và không hở
    thêm đường tấn công (VD: xác thực xong rồi bỏ dở, để trạng thái treo).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        code = request.data.get("code") or ""
        new_password = request.data.get("new_password") or ""

        # Kiểm tra mật khẩu mới TRƯỚC khi verify — verify_otp tiêu luôn mã nếu
        # đúng, nên nếu để sau, người nhập đúng mã nhưng mật khẩu yếu sẽ bị đốt
        # mất mã dù chưa đổi được gì, phải xin gửi lại mã mới cho lỗi không
        # liên quan tới mã.
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response({"new_password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        try:
            verify_otp(user, purpose=OtpCode.Purpose.RESET_PASSWORD, code=code)
        except ValueError as exc:
            return Response({"code": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CurrentUserView(APIView):
    """Frontend gọi lúc khởi động: vừa lấy user, vừa nhận cookie `csrftoken`.

    Trả 200 kèm `authenticated: false` thay vì 401 khi chưa đăng nhập — router
    guard chỉ cần biết trạng thái, không nên coi đó là lỗi.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"authenticated": False, "user": None})
        return Response(
            {"authenticated": True, "user": CurrentUserSerializer(request.user).data}
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        current = request.data.get("current_password") or ""
        new = request.data.get("new_password") or ""

        if not request.user.check_password(current):
            return Response(
                {"current_password": ["Mật khẩu hiện tại không đúng."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new, user=request.user)
        except ValidationError as exc:
            return Response({"new_password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new)
        request.user.save(update_fields=["password"])
        # Đổi mật khẩu làm session hash lệch -> giữ đăng nhập cho chính phiên này.
        django_login(request, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(APIView):
    """Hồ sơ của chính người đang đăng nhập.

    `GET` trả cả cơ sở đang thuộc về, nhưng `PATCH` không nhận field `house`:
    ai thuộc cơ sở nào là quyết định tổ chức, không phải tùy chọn cá nhân.
    Muốn đổi thì sửa bản ghi `Teacher` — việc của quản trị viên.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Đọc lại từ instance đã lưu để trả về đúng cả Person vừa được tạo.
        return Response(ProfileSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """CRUD tài khoản đăng nhập — chỉ superuser (`CanManageUsers`) đọc/ghi được.

    Tự khóa/tự hạ quyền chính mình, hay xóa/hạ quyền superuser cuối cùng còn
    hoạt động, đều bị chặn — mất quyền root là sự cố không tự cứu được ở một
    app quản lý tiền.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, CanManageUsers]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["username", "email", "person__full_name"]
    ordering = ["username"]

    def get_queryset(self):
        queryset = User.objects.select_related("person").order_by("username")
        if house := self.request.query_params.get("house"):
            # Chỉ khớp tài khoản có vai trò Giáo viên ở đúng cơ sở đó — Guardian/
            # tài khoản chưa gán vai trò không gắn với cơ sở nào nên bị loại khi lọc.
            queryset = queryset.filter(person__teacher__house_id=house)
        return queryset

    def _require_another_active_superuser(self, instance):
        still_has_one = (
            User.objects.filter(is_superuser=True, is_active=True)
            .exclude(pk=instance.pk)
            .exists()
        )
        if not still_has_one:
            raise ValidationError(
                "Phải còn ít nhất một quản trị viên cấp cao đang hoạt động."
            )

    def perform_update(self, serializer):
        instance = serializer.instance
        data = serializer.validated_data
        acting_on_self = instance.pk == self.request.user.pk
        will_deactivate = data.get("is_active") is False and instance.is_active
        will_demote = data.get("is_superuser") is False and instance.is_superuser

        if acting_on_self and (will_deactivate or will_demote):
            raise ValidationError(
                "Không thể tự khóa hoặc tự hạ quyền tài khoản đang đăng nhập."
            )
        if instance.is_superuser and (will_deactivate or will_demote):
            self._require_another_active_superuser(instance)
        serializer.save()

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ValidationError("Không thể tự xóa tài khoản đang đăng nhập.")
        if instance.is_superuser:
            self._require_another_active_superuser(instance)
        instance.delete()
