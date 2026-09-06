from django.contrib import admin

from .models import Guardian, Person, Student, StudentGuardian, Teacher, TeachingAssignment


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
class StudentAdmin(admin.ModelAdmin):
    list_display = ("person", "house", "class_grade", "status", "enrolled_date")
    list_filter = ("house", "status", "class_grade")
    search_fields = ("person__full_name",)
    autocomplete_fields = ("person",)
    inlines = [StudentGuardianInline]


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("person", "house")
    list_filter = ("house",)
    search_fields = ("person__full_name",)
    autocomplete_fields = ("person",)


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("person", "occupation")
    search_fields = ("person__full_name",)
    autocomplete_fields = ("person",)


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "student", "is_primary", "assigned_from", "assigned_until")
    list_filter = ("is_primary",)
    autocomplete_fields = ("teacher", "student")
