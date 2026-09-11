from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ChangePasswordView,
    CurrentUserView,
    ForgotPasswordConfirmView,
    ForgotPasswordRequestView,
    LoginView,
    LogoutView,
    ProfileView,
    UserViewSet,
)

app_name = "accounts"

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path(
        "forgot-password/request/",
        ForgotPasswordRequestView.as_view(),
        name="forgot-password-request",
    ),
    path(
        "forgot-password/confirm/",
        ForgotPasswordConfirmView.as_view(),
        name="forgot-password-confirm",
    ),
] + router.urls
