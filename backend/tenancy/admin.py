from django.contrib import admin

from .models import House


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ("name", "inbound_email_slug", "address")
    search_fields = ("name", "inbound_email_slug")
