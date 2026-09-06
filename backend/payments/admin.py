from django.contrib import admin

from .models import BankAccount, BankIntegration, IncomingTransaction, Payment


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("house", "bank_code", "account_number_last4", "account_holder_name")


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
