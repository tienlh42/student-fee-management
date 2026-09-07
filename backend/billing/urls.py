from rest_framework.routers import DefaultRouter

from .views import (
    FeeItemViewSet,
    FeePackageViewSet,
    InvoiceViewSet,
    StudentDiscountViewSet,
    StudentFeePackageViewSet,
)

app_name = "billing"

router = DefaultRouter()
router.register("fee-items", FeeItemViewSet, basename="fee-item")
router.register("fee-packages", FeePackageViewSet, basename="fee-package")
router.register("student-fee-packages", StudentFeePackageViewSet, basename="student-fee-package")
router.register("student-discounts", StudentDiscountViewSet, basename="student-discount")
router.register("invoices", InvoiceViewSet, basename="invoice")

urlpatterns = router.urls
