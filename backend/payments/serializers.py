"""Serializer cho app payments.

Payment/IncomingTransaction chỉ đọc qua API — tạo/sửa đi qua services.py
(record_manual_payment/allocate_manually/try_auto_match), không qua create/update
chung chung, để mọi thay đổi đều kèm theo tính lại status của Invoice/giao dịch.
"""

from rest_framework import serializers

from .models import IncomingTransaction, Payment


class PaymentSerializer(serializers.ModelSerializer):
    invoice_reference = serializers.CharField(source="invoice.qr_reference_code", read_only=True)
    student_name = serializers.CharField(
        source="invoice.student.person.full_name", read_only=True
    )
    payment_method_display = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )
    matched_by_display = serializers.CharField(source="get_matched_by_display", read_only=True)
    recorded_by_username = serializers.CharField(
        source="recorded_by_user.username", read_only=True, default=""
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "invoice_reference",
            "student_name",
            "transaction",
            "amount_applied",
            "payment_method",
            "payment_method_display",
            "matched_by",
            "matched_by_display",
            "recorded_by_user",
            "recorded_by_username",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class IncomingTransactionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    allocated_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    unallocated_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = IncomingTransaction
        fields = [
            "id",
            "house",
            "amount",
            "transfer_content",
            "transaction_time",
            "status",
            "status_display",
            "source",
            "allocated_amount",
            "unallocated_amount",
            "payments",
            "created_at",
        ]
        read_only_fields = fields
