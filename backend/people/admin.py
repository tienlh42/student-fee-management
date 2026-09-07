from django.contrib import admin

from .models import Guardian, Person, Student, StudentGuardian, Teacher, TeachingAssignment


@admin.action(description="Khôi phục bản ghi đã xóa mềm")
def restore_selected(modeladmin, request, queryset):
    queryset.update(is_deleted=False, deleted_at=None)


class SoftDeleteAdminMixin:
    """Cho admin thấy cả bản ghi đã xóa mềm (mặc định `objects` sẽ ẩn đi) +
    action khôi phục. `delete_selected` mặc định của Django gọi
    `queryset.delete()`, đã bị override thành soft delete ở `core.models`."""

    list_filter = ("is_deleted",)
    actions = (restore_selected,)

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("full_name", "gender", "date_of_birth", "phone", "email")
    search_fields = ("full_name", "phone", "email", "id_number")
    list_filter = ("gender",)


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    extra = 0
    autocomplete_fields = ("guardian",)


@admin.register(Student)
class StudentAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("person", "house", "class_grade", "status", "enrolled_date", "is_deleted")
    list_filter = ("house", "status", "class_grade") + SoftDeleteAdminMixin.list_filter
    search_fields = ("person__full_name",)
    autocomplete_fields = ("person",)
    inlines = [StudentGuardianInline]


@admin.register(Teacher)
class TeacherAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("person", "house", "is_deleted")
    list_filter = ("house",) + SoftDeleteAdminMixin.list_filter
    search_fields = ("person__full_name",)
    autocomplete_fields = ("person",)


@admin.register(Guardian)
class GuardianAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("person", "occupation", "is_deleted")
    list_filter = SoftDeleteAdminMixin.list_filter
    search_fields = ("person__full_name",)
    autocomplete_fields = ("person",)


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "student", "is_primary", "assigned_from", "assigned_until")
    list_filter = ("is_primary",)
    autocomplete_fields = ("teacher", "student")
