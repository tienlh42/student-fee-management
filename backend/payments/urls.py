from rest_framework.routers import DefaultRouter

from .views import BankAccountViewSet, IncomingTransactionViewSet, PaymentViewSet, RefundViewSet

app_name = "payments"

router = DefaultRouter()
router.register("bank-accounts", BankAccountViewSet, basename="bank-account")
router.register("incoming-transactions", IncomingTransactionViewSet, basename="incoming-transaction")
router.register("payments", PaymentViewSet, basename="payment")
router.register("refunds", RefundViewSet, basename="refund")

urlpatterns = router.urls
