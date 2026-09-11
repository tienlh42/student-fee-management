"""Serializer cho app payments.

Payment/IncomingTransaction chỉ đọc qua API — tạo/sửa đi qua services.py
(record_manual_payment/allocate_manually/try_auto_match), không qua create/update
chung chung, để mọi thay đổi đều kèm theo tính lại status của Invoice/giao dịch.
"""

from django.db import transaction
from rest_framework import serializers

from billing.models import Refund

from .models import BankAccount, IncomingTransaction, Payment


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


class RefundSerializer(serializers.ModelSerializer):
    invoice_reference = serializers.CharField(source="invoice.qr_reference_code", read_only=True)
    student_name = serializers.CharField(
        source="invoice.student.person.full_name", read_only=True
    )
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    refunded_by_username = serializers.CharField(
        source="refunded_by_user.username", read_only=True, default=""
    )
    invoice_status = serializers.CharField(source="invoice.status", read_only=True)

    class Meta:
        model = Refund
        fields = [
            "id",
            "invoice",
            "invoice_reference",
            "invoice_status",
            "student_name",
            "payment",
            "amount",
            "method",
            "method_display",
            "reason",
            "refunded_at",
            "refunded_by_user",
            "refunded_by_username",
            "needs_adjustment_invoice",
            "created_at",
        ]
        read_only_fields = fields


class BankAccountSerializer(serializers.ModelSerializer):
    """CRUD cấu hình tài khoản nhận tiền theo house — chỉ superuser (xem
    `CanManageBankAccounts`). Một house có thể có nhiều tài khoản; `is_primary`
    đánh dấu tài khoản dùng để sinh VietQR — chỉ một cái/house, giữ bất biến
    này ở `create`/`update` (cùng cách `people.services.link_guardian` xử lý
    `is_primary_contact`). `account_number` write-only: bỏ trống khi sửa
    house/ngân hàng/tên chủ tài khoản mà không muốn đổi số tài khoản; API
    không bao giờ trả số đầy đủ ở đây — xem qua action `reveal` riêng.
    """

    house_name = serializers.CharField(source="house.name", read_only=True)
    bank_name = serializers.CharField(source="get_bank_code_display", read_only=True)
    account_number_last4 = serializers.CharField(read_only=True)
    account_number = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = BankAccount
        fields = [
            "id",
            "house",
            "house_name",
            "bank_code",
            "bank_name",
            "account_holder_name",
            "account_number_last4",
            "account_number",
            "is_primary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_account_number(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("Số tài khoản chỉ gồm chữ số.")
        return value

    def validate(self, attrs):
        # Luôn phải còn đúng một primary/house — không cho bỏ tick primary
        # của tài khoản đang là chính mà không chọn tài khoản khác thay thế.
        if self.instance is not None and self.instance.is_primary and attrs.get("is_primary") is False:
            raise serializers.ValidationError(
                {"is_primary": ["Chọn tài khoản khác làm chính trước khi bỏ tài khoản này."]}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        account_number = validated_data.pop("account_number", "")
        if not account_number:
            raise serializers.ValidationError({"account_number": ["Bắt buộc."]})
        house = validated_data["house"]
        # Tài khoản đầu tiên của house luôn là primary, kể cả khi form không tick —
        # nếu không sẽ có house không có tài khoản nào sinh được VietQR.
        is_primary = validated_data.get("is_primary", False) or not BankAccount.objects.filter(
            house=house
        ).exists()
        validated_data["is_primary"] = is_primary
        if is_primary:
            # Bỏ primary cũ TRƯỚC khi lưu bản ghi mới — constraint DB không
            # cho hai primary cùng tồn tại dù chỉ trong một câu lệnh.
            BankAccount.objects.filter(house=house).update(is_primary=False)
        instance = BankAccount(**validated_data)
        instance.set_account_number(account_number)
        instance.save()
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        account_number = validated_data.pop("account_number", "")
        if validated_data.get("is_primary"):
            BankAccount.objects.filter(house=instance.house).exclude(pk=instance.pk).update(
                is_primary=False
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if account_number:
            instance.set_account_number(account_number)
        instance.save()
        return instance


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
