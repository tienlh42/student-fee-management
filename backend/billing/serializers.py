"""Serializer cho app billing.

Field bất biến sau khi hệ thống tự tính (house/student/period/total_amount/
qr_reference_code/status trên Invoice) đều read-only — sửa chúng qua API sẽ
làm lệch dữ liệu mà `services.py` đang giữ bất biến (net/paid/outstanding).
"""

from rest_framework import serializers

from people.services import can_write_in_house

from .models import (
    FeeItem,
    FeePackage,
    FeePackageItem,
    Invoice,
    InvoiceItem,
    StudentDiscount,
    StudentFeePackage,
)


class FeeItemSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = FeeItem
        fields = [
            "id",
            "house",
            "name",
            "category",
            "category_display",
            "default_amount",
            "is_active",
        ]

    def validate_house(self, house):
        user = self.context["request"].user
        if not can_write_in_house(user, house.pk):
            raise serializers.ValidationError("Bạn không có quyền trên cơ sở này.")
        return house


class FeePackageItemSerializer(serializers.ModelSerializer):
    fee_item_name = serializers.CharField(source="fee_item.name", read_only=True)
    effective_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = FeePackageItem
        fields = ["id", "fee_item", "fee_item_name", "amount", "effective_amount"]


class FeePackageSerializer(serializers.ModelSerializer):
    billing_timing_display = serializers.CharField(
        source="get_billing_timing_display", read_only=True
    )
    items = FeePackageItemSerializer(many=True)

    class Meta:
        model = FeePackage
        fields = [
            "id",
            "house",
            "name",
            "description",
            "due_day_of_month",
            "billing_timing",
            "billing_timing_display",
            "is_active",
            "items",
        ]

    def validate_house(self, house):
        user = self.context["request"].user
        if not can_write_in_house(user, house.pk):
            raise serializers.ValidationError("Bạn không có quyền trên cơ sở này.")
        return house

    def validate(self, attrs):
        house = attrs.get("house") or getattr(self.instance, "house", None)
        for item in attrs.get("items", []):
            fee_item = item["fee_item"]
            if house is not None and fee_item.house_id != house.pk:
                raise serializers.ValidationError(
                    {"items": "Khoản thu phải cùng cơ sở với gói phí."}
                )
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        package = FeePackage.objects.create(**validated_data)
        self._sync_items(package, items_data)
        return package

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        instance = super().update(instance, validated_data)
        if items_data is not None:
            self._sync_items(instance, items_data, replace=True)
        return instance

    def _sync_items(self, package, items_data, *, replace=False):
        if replace:
            package.items.all().delete()
        FeePackageItem.objects.bulk_create(
            FeePackageItem(
                fee_package=package,
                fee_item=item["fee_item"],
                amount=item.get("amount"),
            )
            for item in items_data
        )


class StudentFeePackageSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.person.full_name", read_only=True)
    fee_package_name = serializers.CharField(source="fee_package.name", read_only=True)

    class Meta:
        model = StudentFeePackage
        fields = [
            "id",
            "student",
            "student_name",
            "fee_package",
            "fee_package_name",
            "effective_from",
            "effective_until",
        ]

    def validate_student(self, student):
        user = self.context["request"].user
        if not can_write_in_house(user, student.house_id):
            raise serializers.ValidationError("Bạn không có quyền trên học sinh này.")
        return student

    def validate(self, attrs):
        student = attrs.get("student") or getattr(self.instance, "student", None)
        fee_package = attrs.get("fee_package") or getattr(self.instance, "fee_package", None)
        if student is not None and fee_package is not None and fee_package.house_id != student.house_id:
            raise serializers.ValidationError(
                {"fee_package": "Gói phí phải cùng cơ sở với học sinh."}
            )
        return attrs


class StudentDiscountSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.person.full_name", read_only=True)
    fee_item_name = serializers.CharField(source="fee_item.name", read_only=True, default="")
    discount_type_display = serializers.CharField(
        source="get_discount_type_display", read_only=True
    )

    class Meta:
        model = StudentDiscount
        fields = [
            "id",
            "student",
            "student_name",
            "fee_item",
            "fee_item_name",
            "name",
            "discount_type",
            "discount_type_display",
            "value",
            "effective_from",
            "effective_until",
            "is_active",
        ]

    def validate_student(self, student):
        user = self.context["request"].user
        if not can_write_in_house(user, student.house_id):
            raise serializers.ValidationError("Bạn không có quyền trên học sinh này.")
        return student

    def validate(self, attrs):
        student = attrs.get("student") or getattr(self.instance, "student", None)
        fee_item = attrs.get("fee_item") or getattr(self.instance, "fee_item", None)
        if student is not None and fee_item is not None and fee_item.house_id != student.house_id:
            raise serializers.ValidationError(
                {"fee_item": "Khoản thu phải cùng cơ sở với học sinh."}
            )
        return attrs


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "fee_item", "fee_item_name_snapshot", "amount"]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.person.full_name", read_only=True)
    house_name = serializers.CharField(source="house.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    refunded_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "house",
            "house_name",
            "student",
            "student_name",
            "period",
            "total_amount",
            "adjustment_amount",
            "adjustment_note",
            "net_amount",
            "paid_amount",
            "refunded_amount",
            "net_paid",
            "outstanding_amount",
            "status",
            "status_display",
            "cancel_reason",
            "due_date",
            "qr_reference_code",
            "items",
        ]
        # Sinh ra từ services.generate_invoice / recalculate_status — chỉ điều chỉnh
        # được adjustment_amount/adjustment_note/due_date qua API, không sửa tay phần còn lại.
        read_only_fields = [
            "house",
            "student",
            "period",
            "total_amount",
            "status",
            "cancel_reason",
            "qr_reference_code",
        ]
