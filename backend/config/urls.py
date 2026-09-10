import re

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from .views import IndexView

urlpatterns = [
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    path("api/tenancy/", include("tenancy.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/people/", include("people.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/notifications/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Catch-all phải nằm cuối cùng. Trừ luôn path admin (đổi được qua
# DJANGO_ADMIN_URL) — không hardcode "admin/" ở đây kẻo lệch với urlpatterns.
urlpatterns += [
    re_path(
        rf"^(?!api/|{re.escape(settings.DJANGO_ADMIN_URL)}|static/|media/).*$",
        IndexView.as_view(),
        name="index",
    ),
]
