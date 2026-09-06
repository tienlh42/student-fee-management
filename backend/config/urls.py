from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from .views import IndexView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/tenancy/", include("tenancy.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/people/", include("people.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/notifications/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Catch-all phải nằm cuối cùng.
urlpatterns += [
    re_path(r"^(?!api/|admin/|static/|media/).*$", IndexView.as_view(), name="index"),
]
