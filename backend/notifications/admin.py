from django.contrib import admin

from .models import Notification, NotificationRead


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
