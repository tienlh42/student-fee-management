from django.urls import path

from .views import RequestOtpView, VerifyOtpView

app_name = "notifications"

urlpatterns = [
    path("otp/request/", RequestOtpView.as_view(), name="otp-request"),
    path("otp/verify/", VerifyOtpView.as_view(), name="otp-verify"),
]
