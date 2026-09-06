"""API cho app people. View chỉ điều phối — logic nằm ở `services.py`."""

from django.db.models import Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsTeacherOrReadOnly

from .models import (
    Guardian,
    Person,
    Student,
    StudentGuardian,
    TeachingAssignment,
)
from .permissions import WritableWithinOwnHouse
from .serializers import (
    GuardianSerializer,
    StudentGuardianSerializer,
    StudentSerializer,
    TeacherSerializer,
    TeachingAssignmentSerializer,
)
from .services import (
    accessible_guardians,
    accessible_students,
    accessible_teachers,
    default_house_id,
    link_guardian,
)


class ScopedModelViewSet(viewsets.ModelViewSet):
    """Nền chung: queryset đã lọc theo vai trò + ghi chỉ dành cho teacher."""

    # IsAuthenticated phải liệt kê tường minh: khai báo permission_classes ở view
    # sẽ *thay thế* DEFAULT_PERMISSION_CLASSES, không cộng dồn vào nó.
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly, WritableWithinOwnHouse]
    filter_backends = [SearchFilter, OrderingFilter]


class StudentViewSet(ScopedModelViewSet):
    serializer_class = StudentSerializer
    search_fields = ["person__full_name", "person__phone", "class_grade"]
    ordering_fields = ["person__full_name", "class_grade", "enrolled_date", "status"]
    ordering = ["person__full_name"]

    def get_queryset(self):
        queryset = (
            accessible_students(self.request.user)
            .select_related("person", "house")
            .prefetch_related(
                Prefetch(
                    "guardian_links",
                    queryset=StudentGuardian.objects.select_related(
                        "guardian", "guardian__person"
                    ).order_by("-is_primary_contact"),
                )
            )
        )

        params = self.request.query_params
        if status_filter := params.get("status"):
            queryset = queryset.filter(status=status_filter)
        if class_grade := params.get("class_grade"):
            queryset = queryset.filter(class_grade=class_grade)
        if house := params.get("house"):
            queryset = queryset.filter(house_id=house)
        return queryset

    @action(detail=False, methods=["get"], url_path="meta")
    def options_meta(self, request):
        """Dữ liệu để dựng dropdown ở form/filter — gộp 1 request thay vì 4."""
        from tenancy.models import House

        grades = (
            accessible_students(request.user)
            .exclude(class_grade="")
            .order_by("class_grade")
            .values_list("class_grade", flat=True)
            .distinct()
        )
        houses = House.objects.filter(
            id__in=accessible_students(request.user).values_list("house_id", flat=True)
        )
        return Response(
            {
                "statuses": [
                    {"value": value, "label": label} for value, label in Student.Status.choices
                ],
                "genders": [
                    {"value": value, "label": label}
                    for value, label in Person.Gender.choices
                ],
                "relationships": [
                    {"value": value, "label": label}
                    for value, label in StudentGuardian.Relationship.choices
                ],
                "class_grades": list(grades),
                "houses": [{"value": h.id, "label": h.name} for h in houses],
                "default_house": default_house_id(request.user),
            }
        )

    @action(detail=True, methods=["get", "post"], url_path="guardians")
    def guardians(self, request, pk=None):
        """GET: liên kết phụ huynh của học sinh. POST: gắn thêm/cập nhật một liên kết."""
        student = self.get_object()

        if request.method == "GET":
            links = student.guardian_links.select_related("guardian__person")
            return Response(StudentGuardianSerializer(links, many=True).data)

        guardian = self._resolve_guardian(request.data.get("guardian"))
        if guardian is None:
            return Response(
                {"guardian": ["Không tìm thấy phụ huynh."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        link = link_guardian(
            student,
            guardian=guardian,
            relationship_type=request.data.get(
                "relationship_type", StudentGuardian.Relationship.OTHER
            ),
            is_primary_contact=bool(request.data.get("is_primary_contact")),
        )
        return Response(
            StudentGuardianSerializer(link).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["delete"], url_path=r"guardians/(?P<guardian_id>\d+)")
    def unlink_guardian(self, request, pk=None, guardian_id=None):
        student = self.get_object()
        deleted, _ = StudentGuardian.objects.filter(
            student=student, guardian_id=guardian_id
        ).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _resolve_guardian(self, guardian_id) -> Guardian | None:
        return Guardian.objects.filter(person_id=guardian_id).first()


class GuardianViewSet(ScopedModelViewSet):
    serializer_class = GuardianSerializer
    search_fields = ["person__full_name", "person__phone"]
    ordering_fields = ["person__full_name"]
    ordering = ["person__full_name"]

    def get_queryset(self):
        return accessible_guardians(self.request.user).select_related("person")


class TeacherViewSet(ScopedModelViewSet):
    serializer_class = TeacherSerializer
    search_fields = ["person__full_name", "person__phone"]
    ordering = ["person__full_name"]

    def get_queryset(self):
        return accessible_teachers(self.request.user).select_related("person", "house")


class TeachingAssignmentViewSet(ScopedModelViewSet):
    serializer_class = TeachingAssignmentSerializer
    ordering = ["-assigned_from"]

    def get_queryset(self):
        return TeachingAssignment.objects.filter(
            student__in=accessible_students(self.request.user)
        ).select_related("teacher__person", "student__person")
