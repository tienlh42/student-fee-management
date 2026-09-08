"""API cho app payments — đối soát tiền vào + sổ quỹ thanh toán. View chỉ điều
phối, logic ở services.py.

Giai đoạn hiện tại: chỉ đọc/đối soát giao dịch tiền vào (được nhập qua Django
admin — chưa có webhook nhận tự động) + các thao tác thủ công (khớp lại, phân
bổ tay, bỏ qua). Ghi nhận thanh toán thủ công (`record-payment`) nằm ở
`billing.InvoiceViewSet` vì đó là thao tác trên hóa đơn, không đụng tới dữ liệu
ngân hàng — `PaymentViewSet` ở đây chỉ để xem lại (sổ quỹ), không tạo mới.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import CanSeeBankData
from billing.models import Invoice, Refund
from people.services import teacher_house_ids

from .models import IncomingTransaction, Payment
from .serializers import IncomingTransactionSerializer, PaymentSerializer, RefundSerializer
from .services import allocate_manually, try_auto_match


class IncomingTransactionViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Giao dịch tiền vào chỉ được tạo qua webhook (chưa cài) hoặc Django admin —
    view này chỉ phục vụ đối soát: xem, khớp lại, phân bổ tay, bỏ qua.
    """

    serializer_class = IncomingTransactionSerializer
    permission_classes = [IsAuthenticated, CanSeeBankData]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["transfer_content", "provider_transaction_id"]
    ordering = ["-transaction_time"]

    def get_queryset(self):
        queryset = IncomingTransaction.objects.filter(
            house_id__in=teacher_house_ids(self.request.user)
        ).prefetch_related("payments__invoice__student__person")

        if status_filter := self.request.query_params.get("status"):
            queryset = queryset.filter(status=status_filter)
        if house := self.request.query_params.get("house"):
            queryset = queryset.filter(house_id=house)
        return queryset

    @action(detail=False, methods=["get"], url_path="meta")
    def options_meta(self, request):
        return Response(
            {
                "statuses": [
                    {"value": value, "label": label}
                    for value, label in IncomingTransaction.Status.choices
                ],
            }
        )

    @action(detail=True, methods=["post"], url_path="retry-match")
    def retry_match(self, request, pk=None):
        incoming = self.get_object()
        created = try_auto_match(incoming)
        incoming.refresh_from_db()
        return Response(
            {
                "transaction": IncomingTransactionSerializer(incoming).data,
                "matched": len(created),
            }
        )

    @action(detail=True, methods=["post"], url_path="allocate")
    def allocate(self, request, pk=None):
        incoming = self.get_object()

        invoice_id = request.data.get("invoice")
        if not invoice_id:
            return Response({"invoice": ["Bắt buộc."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            invoice = Invoice.objects.get(pk=invoice_id, house_id=incoming.house_id)
        except Invoice.DoesNotExist:
            return Response(
                {"invoice": ["Không tìm thấy hóa đơn trong cùng cơ sở."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if invoice.status == Invoice.Status.VOID:
            # allocate_manually không tự chặn — recalculate_status coi VOID là
            # trạng thái sticky nên tiền phân bổ vào sẽ "biến mất" không rõ ràng.
            return Response(
                {"invoice": ["Hóa đơn đã hủy — khôi phục trước khi phân bổ."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(str(request.data.get("amount", "")))
        except InvalidOperation:
            return Response({"amount": ["Không đọc được số tiền."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            allocate_manually(incoming, invoice, amount, user=request.user)
        except ValueError as exc:
            return Response({"amount": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        incoming.refresh_from_db()
        return Response(IncomingTransactionSerializer(incoming).data)

    @action(detail=True, methods=["post"], url_path="ignore")
    def ignore(self, request, pk=None):
        incoming = self.get_object()
        if incoming.status != IncomingTransaction.Status.UNMATCHED:
            return Response(
                {"detail": "Chỉ bỏ qua được giao dịch chưa khớp."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        incoming.status = IncomingTransaction.Status.IGNORED
        incoming.save(update_fields=["status", "updated_at"])
        return Response(IncomingTransactionSerializer(incoming).data)


class PaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Sổ quỹ — toàn bộ khoản đã thu, dù khớp tự động hay ghi tay. Chỉ đọc:
    Payment tạo qua services.py (record_manual_payment/allocate_manually/
    try_auto_match), không qua create/update chung chung.
    """

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, CanSeeBankData]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "invoice__qr_reference_code",
        "invoice__student__person__full_name",
        "note",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Payment.objects.filter(
            invoice__house_id__in=teacher_house_ids(self.request.user)
        ).select_related("invoice__student__person", "recorded_by_user")

        params = self.request.query_params
        if method := params.get("payment_method"):
            queryset = queryset.filter(payment_method=method)
        if matched_by := params.get("matched_by"):
            queryset = queryset.filter(matched_by=matched_by)
        if invoice := params.get("invoice"):
            queryset = queryset.filter(invoice_id=invoice)
        return queryset

    @action(detail=False, methods=["get"], url_path="meta")
    def options_meta(self, request):
        return Response(
            {
                "payment_methods": [
                    {"value": value, "label": label} for value, label in Payment.Method.choices
                ],
                "matched_by": [
                    {"value": value, "label": label} for value, label in Payment.MatchedBy.choices
                ],
            }
        )


class RefundViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Sổ hoàn tiền — chỉ đọc. Tạo qua `billing.InvoiceViewSet.refund`
    (`payments.services.process_refund`), không qua create/update chung chung.
    """

    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated, CanSeeBankData]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "invoice__qr_reference_code",
        "invoice__student__person__full_name",
        "reason",
    ]
    ordering = ["-refunded_at"]

    def get_queryset(self):
        queryset = Refund.objects.filter(
            invoice__house_id__in=teacher_house_ids(self.request.user)
        ).select_related("invoice__student__person", "refunded_by_user")

        params = self.request.query_params
        if method := params.get("method"):
            queryset = queryset.filter(method=method)
        if invoice := params.get("invoice"):
            queryset = queryset.filter(invoice_id=invoice)
        return queryset

    @action(detail=False, methods=["get"], url_path="meta")
    def options_meta(self, request):
        return Response(
            {
                "methods": [
                    {"value": value, "label": label} for value, label in Refund.Method.choices
                ],
            }
        )
