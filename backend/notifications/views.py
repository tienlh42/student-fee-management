from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .otp import request_otp, verify_otp


class RequestOtpView(APIView):
    """Gửi mã OTP tới email của chính người đang đăng nhập."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        purpose = request.data.get("purpose", "")
        try:
            request_otp(request.user, purpose=purpose)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyOtpView(APIView):
    """Xác thực mã OTP vừa gửi cho chính người đang đăng nhập."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        purpose = request.data.get("purpose", "")
        code = request.data.get("code", "")
        try:
            verify_otp(request.user, purpose=purpose, code=code)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
