"""API cho app billing. View chỉ điều phối — logic nằm ở `services.py`."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.db.models.deletion import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import CanSeeBankData, IsTeacher, IsTeacherOrReadOnly
from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.services import process_refund, record_manual_payment
from people.models import Student
from people.permissions import WritableWithinOwnHouse
from people.services import accessible_students, default_house_id, teacher_house_ids

from .models import FeeItem, FeePackage, Invoice, Refund, StudentDiscount, StudentFeePackage
from .serializers import (
    FeeItemSerializer,
    FeePackageSerializer,
    InvoiceSerializer,
    StudentDiscountSerializer,
    StudentFeePackageSerializer,
)
from .services import generate_invoice, period_start, recalculate_status


class CatalogModelViewSet(viewsets.ModelViewSet):
    """Nền chung cho các model cấu hình biểu phí — chỉ teacher/staff được đụng vào."""

    permission_classes = [IsAuthenticated, IsTeacher, WritableWithinOwnHouse]
    filter_backends = [SearchFilter, OrderingFilter]


class FeeItemViewSet(CatalogModelViewSet):
    serializer_class = FeeItemSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "category", "default_amount"]
    ordering = ["category", "name"]

    def get_queryset(self):
        return FeeItem.objects.filter(house_id__in=teacher_house_ids(self.request.user))

    @action(detail=False, methods=["get"], url_path="meta")
    def options_meta(self, request):
        return Response(
            {
                "categories": [
                    {"value": value, "label": label} for value, label in FeeItem.Category.choices
                ],
                "default_house": default_house_id(request.user),
            }
        )


class FeePackageViewSet(CatalogModelViewSet):
    serializer_class = FeePackageSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "due_day_of_month"]
    ordering = ["name"]

    def get_queryset(self):
        return FeePackage.objects.filter(
            house_id__in=teacher_house_ids(self.request.user)
        ).prefetch_related("items__fee_item")

    @action(detail=False, methods=["get"], url_path="meta")
    def options_meta(self, request):
        return Response(
            {
                "billing_timings": [
                    {"value": value, "label": label}
                    for value, label in FeePackage.BillingTiming.choices
                ],
                "fee_items": [
                    {"value": item.id, "label": item.name, "house": item.house_id}
                    for item in FeeItem.objects.filter(
                        house_id__in=teacher_house_ids(request.user), is_active=True
                    )
                ],
                "default_house": default_house_id(request.user),
            }
        )


class StudentFeePackageViewSet(CatalogModelViewSet):
    serializer_class = StudentFeePackageSerializer
    ordering = ["-effective_from"]

    def get_queryset(self):
        queryset = StudentFeePackage.objects.filter(
            student__in=accessible_students(self.request.user)
        ).select_related("student__person", "fee_package")
        if student := self.request.query_params.get("student"):
            queryset = queryset.filter(student_id=student)
        return queryset


class StudentDiscountViewSet(CatalogModelViewSet):
    serializer_class = StudentDiscountSerializer
    search_fields = ["name", "student__person__full_name"]
    ordering = ["-effective_from"]

    def get_queryset(self):
        queryset = StudentDiscount.objects.filter(
            student__in=accessible_students(self.request.user)
        ).select_related("student__person", "fee_item")
        if student := self.request.query_params.get("student"):
            queryset = queryset.filter(student_id=student)
        return queryset


class InvoiceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Hóa đơn sinh qua `generate`/lệnh `generate_invoices` — không tạo tay qua POST."""

    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly, WritableWithinOwnHouse]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["qr_reference_code", "student__person__full_name"]
    ordering_fields = ["period", "due_date", "status", "total_amount"]
    ordering = ["-period"]

    def get_queryset(self):
        queryset = Invoice.objects.filter(
            student__in=accessible_students(self.request.user)
        ).select_related("student__person", "house").prefetch_related("items")

        params = self.request.query_params
        if period := params.get("period"):
            queryset = queryset.filter(period=period)
        if status_filter := params.get("status"):
            queryset = queryset.filter(status=status_filter)
        if student := params.get("student"):
            queryset = queryset.filter(student_id=student)
        if house := params.get("house"):
            queryset = queryset.filter(house_id=house)
        return queryset

    def destroy(self, request, *args, **kwargs):
        """Xóa hẳn hóa đơn — để sinh lại hóa đơn khác cho cùng học sinh/kỳ đó
        (bị chặn bởi `uniq_invoice_student_period` nếu bản cũ còn tồn tại).

        Đã có thanh toán/hoàn tiền thì không xóa được (Payment/Refund trỏ về
        Invoice qua on_delete=PROTECT) — dùng `void` thay vì xóa trong trường
        hợp đó.
        """
        invoice = self.get_object()
        try:
            invoice.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": "Hóa đơn đã có thanh toán hoặc hoàn tiền, không xóa được — "
                    "hủy hóa đơn thay vì xóa."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="meta")
    def options_meta(self, request):
        return Response(
            {
                "statuses": [
                    {"value": value, "label": label} for value, label in Invoice.Status.choices
                ],
            }
        )

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """Sinh hóa đơn nháp cho toàn bộ/một học sinh trong một kỳ.

        Chỉ chạy trên các cơ sở request.user *ghi* được — kể cả khi truy vấn
        được phép đọc rộng hơn (staff xem tất cả nhưng generate vẫn tôn trọng
        `teacher_house_ids`, để nhất quán với quyền ghi ở nơi khác).
        """
        period_raw = request.data.get("period")
        if not period_raw:
            return Response(
                {"period": ["Bắt buộc, dạng YYYY-MM hoặc YYYY-MM-DD."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            parts = period_raw.split("-")
            if len(parts) == 2:
                period = date(int(parts[0]), int(parts[1]), 1)
            else:
                period = period_start(date.fromisoformat(period_raw))
        except (ValueError, TypeError):
            return Response(
                {"period": ["Không đọc được ngày."]}, status=status.HTTP_400_BAD_REQUEST
            )

        writable_house_ids = set(teacher_house_ids(request.user))
        students = (
            accessible_students(request.user)
            .filter(status=Student.Status.ACTIVE, house_id__in=writable_house_ids)
            .select_related("house")
        )
        if student_id := request.data.get("student"):
            students = students.filter(pk=student_id)
        if house_id := request.data.get("house"):
            students = students.filter(house_id=house_id)

        created = existing = 0
        for student in students:
            already_had = Invoice.objects.filter(student=student, period=period).exists()
            generate_invoice(student, period)
            if already_had:
                existing += 1
            else:
                created += 1

        return Response({"period": period.isoformat(), "created": created, "existing": existing})

    @action(detail=True, methods=["post"], url_path="void")
    def void(self, request, pk=None):
        invoice = self.get_object()
        invoice.status = Invoice.Status.VOID
        invoice.cancel_reason = request.data.get("reason", "")
        invoice.save(update_fields=["status", "cancel_reason", "updated_at"])
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != Invoice.Status.VOID:
            return Response(
                {"detail": "Hóa đơn này chưa bị hủy."}, status=status.HTTP_400_BAD_REQUEST
            )
        # Đưa tạm về ISSUED rồi để recalculate_status suy lại đúng trạng thái
        # theo số tiền đã thu (có thể đã thu một phần trước khi bị hủy).
        invoice.status = Invoice.Status.ISSUED
        invoice.cancel_reason = ""
        invoice.save(update_fields=["status", "cancel_reason", "updated_at"])
        recalculate_status(invoice)
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        """Ghi nhận một đợt thanh toán thủ công (tiền mặt/chuyển khoản/khác).

        Gọi nhiều lần cho cùng hóa đơn để chia thành nhiều đợt — mỗi lần là
        một `Payment` riêng, cộng dồn vào `paid_amount`.
        """
        invoice = self.get_object()
        if invoice.status == Invoice.Status.VOID:
            return Response(
                {"detail": "Hóa đơn đã hủy — khôi phục trước khi ghi nhận thanh toán."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            amount = Decimal(str(request.data.get("amount", "")))
        except InvalidOperation:
            return Response({"detail": "Không đọc được số tiền."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            record_manual_payment(
                invoice,
                amount,
                method=request.data.get("method", Payment.Method.CASH),
                user=request.user,
                note=request.data.get("note", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        invoice.refresh_from_db()
        return Response(InvoiceSerializer(invoice).data)

    @action(
        detail=True,
        methods=["get"],
        url_path="payments",
        permission_classes=[IsAuthenticated, CanSeeBankData],
    )
    def payments(self, request, pk=None):
        invoice = self.get_object()
        return Response(PaymentSerializer(invoice.payments.all(), many=True).data)

    @action(detail=True, methods=["post"], url_path="refund")
    def refund(self, request, pk=None):
        """Hoàn tiền — xem `payments.services.process_refund` cho toàn bộ quy tắc.

        Hai lựa chọn độc lập ở input (`amount`, `cancel_obligation`) bao quát
        cả 4 tổ hợp đóng đủ/một phần × hoàn hết/hoàn một phần, không cần biết
        trước hóa đơn đang ở tổ hợp nào.
        """
        invoice = self.get_object()
        try:
            amount = Decimal(str(request.data.get("amount", "")))
        except InvalidOperation:
            return Response({"detail": "Không đọc được số tiền."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            process_refund(
                invoice,
                amount,
                cancel_obligation=bool(request.data.get("cancel_obligation")),
                method=request.data.get("method", Refund.Method.BANK_TRANSFER),
                user=request.user,
                reason=request.data.get("reason", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        invoice.refresh_from_db()
        return Response(InvoiceSerializer(invoice).data)
