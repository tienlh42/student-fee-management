from django.contrib import admin

from .models import (
    BankAccount,
    BankAccountRevealLog,
    BankIntegration,
    IncomingTransaction,
    Payment,
)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("house", "bank_code", "account_number_last4", "account_holder_name")
    # Số tài khoản đầy đủ chỉ nhập/xem qua trang Quản trị (API `set_account_number`/
    # `reveal`) — ở đây chỉ hiển thị ciphertext thô, không sửa được.
    readonly_fields = ("account_number_encrypted",)


@admin.register(BankAccountRevealLog)
class BankAccountRevealLogAdmin(admin.ModelAdmin):
    list_display = ("bank_account", "revealed_by_user", "created_at")
    readonly_fields = ("bank_account", "revealed_by_user", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BankIntegration)
class BankIntegrationAdmin(admin.ModelAdmin):
    list_display = ("house", "provider", "sepay_account_id")
    # Không đưa secret vào list_display / search_fields.


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    autocomplete_fields = ("invoice",)


@admin.register(IncomingTransaction)
class IncomingTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_time",
        "amount",
        "allocated_amount",
        "status",
        "transfer_content",
        "house",
    )
    list_filter = ("house", "status", "source")
    search_fields = ("transfer_content", "provider_transaction_id")
    date_hierarchy = "transaction_time"
    readonly_fields = ("raw_payload", "created_at")
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "invoice",
        "amount_applied",
        "payment_method",
        "matched_by",
        "recorded_by_user",
    )
    list_filter = ("payment_method", "matched_by")
    search_fields = ("invoice__qr_reference_code",)
    autocomplete_fields = ("invoice", "transaction", "recorded_by_user")
