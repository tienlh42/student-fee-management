from django.contrib import admin

from .models import (
    FeeItem,
    FeePackage,
    FeePackageItem,
    Invoice,
    InvoiceItem,
    Refund,
    StudentDiscount,
    StudentFeePackage,
)


@admin.register(FeeItem)
class FeeItemAdmin(admin.ModelAdmin):
    list_display = ("name", "house", "category", "default_amount", "is_active")
    list_filter = ("house", "category", "is_active")
    search_fields = ("name",)


class FeePackageItemInline(admin.TabularInline):
    model = FeePackageItem
    extra = 1
    autocomplete_fields = ("fee_item",)


@admin.register(FeePackage)
class FeePackageAdmin(admin.ModelAdmin):
    list_display = ("name", "house", "billing_timing", "due_day_of_month", "is_active")
    list_filter = ("house", "billing_timing", "is_active")
    search_fields = ("name",)
    inlines = [FeePackageItemInline]


@admin.register(StudentFeePackage)
class StudentFeePackageAdmin(admin.ModelAdmin):
    list_display = ("student", "fee_package", "effective_from", "effective_until")
    list_filter = ("fee_package",)
    autocomplete_fields = ("student", "fee_package")


@admin.register(StudentDiscount)
class StudentDiscountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "student",
        "fee_item",
        "discount_type",
        "value",
        "effective_from",
        "is_active",
    )
    list_filter = ("discount_type", "is_active")
    autocomplete_fields = ("student", "fee_item")
    search_fields = ("name", "student__person__full_name")


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    autocomplete_fields = ("fee_item",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "qr_reference_code",
        "student",
        "period",
        "net_amount",
        "paid_amount",
        "outstanding_amount",
        "status",
        "due_date",
    )
    list_filter = ("house", "status", "period")
    search_fields = ("qr_reference_code", "student__person__full_name")
    date_hierarchy = "period"
    autocomplete_fields = ("student",)
    readonly_fields = ("qr_reference_code", "created_at", "updated_at")
    inlines = [InvoiceItemInline]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "refunded_at", "refunded_by_user")
    autocomplete_fields = ("invoice", "refunded_by_user")
    search_fields = ("invoice__qr_reference_code",)
