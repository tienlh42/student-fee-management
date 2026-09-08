from rest_framework.routers import DefaultRouter

from .views import IncomingTransactionViewSet, PaymentViewSet

app_name = "payments"

router = DefaultRouter()
router.register("incoming-transactions", IncomingTransactionViewSet, basename="incoming-transaction")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = router.urls
