from rest_framework.routers import DefaultRouter

from .views import HouseViewSet

app_name = "tenancy"

router = DefaultRouter()
router.register("houses", HouseViewSet, basename="house")

urlpatterns = router.urls
