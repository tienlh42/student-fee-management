from rest_framework.routers import DefaultRouter

from .views import (
    GuardianViewSet,
    StudentViewSet,
    TeacherViewSet,
    TeachingAssignmentViewSet,
)

app_name = "people"

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("teachers", TeacherViewSet, basename="teacher")
router.register("assignments", TeachingAssignmentViewSet, basename="assignment")

urlpatterns = router.urls
