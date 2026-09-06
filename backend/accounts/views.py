"""Đăng nhập/đăng xuất bằng session — same-origin nên không cần JWT.

DRF `APIView` tự bọc `csrf_exempt`, và `SessionAuthentication` chỉ kiểm CSRF
với request đã đăng nhập. Login là request *chưa* đăng nhập nên phải tự gắn
`csrf_protect`, nếu không endpoint này hở CSRF.
"""

from django.contrib.auth import login as django_login, logout as django_logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import CurrentUserSerializer, LoginSerializer, ProfileSerializer


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
