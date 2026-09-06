from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserOAuthAccount


class OAuthInline(admin.TabularInline):
    model = UserOAuthAccount
    extra = 0
    fields = ("provider", "provider_uid", "created_at")
    readonly_fields = ("created_at",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [OAuthInline]
    list_display = ("username", "email", "person", "is_active", "is_staff")
    autocomplete_fields = ("person",)
    fieldsets = BaseUserAdmin.fieldsets + (("Liên kết", {"fields": ("person",)}),)
