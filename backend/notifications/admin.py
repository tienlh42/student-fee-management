from django.contrib import admin

from .models import EmailLog, Notification, NotificationRead, OtpCode


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "house", "student", "published_at", "created_by_user")
    list_filter = ("house", "category", "published_at")
    search_fields = ("title", "body")
    autocomplete_fields = ("student", "created_by_user")
    date_hierarchy = "created_at"


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("notification", "user", "read_at")
    autocomplete_fields = ("notification", "user")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """Chỉ đọc — đây là nhật ký, không sửa/tạo tay qua admin."""

    list_display = ("to_email", "subject", "purpose", "status", "created_at")
    list_filter = ("status", "purpose")
    search_fields = ("to_email", "subject")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    """Chỉ đọc — không hiện `code_hash`, chỉ để tra soát trạng thái gửi/xác thực."""

    list_display = ("user", "purpose", "attempts", "expires_at", "consumed_at", "created_at")
    list_filter = ("purpose",)
    autocomplete_fields = ("user",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
