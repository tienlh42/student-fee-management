from django.db import models


class Person(models.Model):
    """Thông tin định danh dùng chung cho Student / Teacher / Guardian."""

    class Gender(models.TextChoices):
        MALE = "male", "Nam"
        FEMALE = "female", "Nữ"
        OTHER = "other", "Khác"

    full_name = models.CharField("Họ và tên", max_length=255)
    gender = models.CharField("Giới tính", max_length=10, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField("Ngày sinh", null=True, blank=True)
    place_of_birth = models.CharField("Nơi sinh", max_length=255, blank=True)
    nationality = models.CharField("Quốc tịch", max_length=100, blank=True, default="Việt Nam")
    ethnicity = models.CharField("Dân tộc", max_length=100, blank=True)

    id_number = models.CharField("Số CCCD/CMND", max_length=20, blank=True)
    id_issued_date = models.DateField("Ngày cấp", null=True, blank=True)
    id_issued_place = models.CharField("Nơi cấp", max_length=255, blank=True)

    permanent_address = models.CharField("Hộ khẩu thường trú", max_length=500, blank=True)
    current_address = models.CharField("Chỗ ở hiện tại", max_length=500, blank=True)
    phone = models.CharField("Điện thoại", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)
    avatar_url = models.URLField("Ảnh đại diện", max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Nhân thân"
        verbose_name_plural = "Nhân thân"
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self) -> str:
        return self.full_name


class Student(models.Model):
    """Person đóng vai trò học sinh. person_id là khóa chính (1-1 với Person)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Đang học"
        PAUSED = "paused", "Tạm nghỉ"
        GRADUATED = "graduated", "Đã tốt nghiệp"
        WITHDRAWN = "withdrawn", "Đã nghỉ"

    person = models.OneToOneField(
        Person, on_delete=models.CASCADE, primary_key=True, related_name="student"
    )
    house = models.ForeignKey(
        "tenancy.House", on_delete=models.PROTECT, related_name="students", verbose_name="Cơ sở"
    )
    class_grade = models.CharField("Lớp", max_length=50, blank=True)
    status = models.CharField(
        "Trạng thái", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    enrolled_date = models.DateField("Ngày nhập học", null=True, blank=True)

    class Meta:
        verbose_name = "Học sinh"
        verbose_name_plural = "Học sinh"
        ordering = ["person__full_name"]
        indexes = [models.Index(fields=["house", "status"])]

    def __str__(self) -> str:
        return self.person.full_name


class Teacher(models.Model):
    person = models.OneToOneField(
        Person, on_delete=models.CASCADE, primary_key=True, related_name="teacher"
    )
    house = models.ForeignKey(
        "tenancy.House", on_delete=models.PROTECT, related_name="teachers", verbose_name="Cơ sở"
    )

    class Meta:
        verbose_name = "Giáo viên"
        verbose_name_plural = "Giáo viên"
        ordering = ["person__full_name"]

    def __str__(self) -> str:
        return self.person.full_name


class Guardian(models.Model):
    person = models.OneToOneField(
        Person, on_delete=models.CASCADE, primary_key=True, related_name="guardian"
    )
    occupation = models.CharField("Nghề nghiệp", max_length=255, blank=True)

    class Meta:
        verbose_name = "Phụ huynh"
        verbose_name_plural = "Phụ huynh"
        ordering = ["person__full_name"]

    def __str__(self) -> str:
        return self.person.full_name


class StudentGuardian(models.Model):
    class Relationship(models.TextChoices):
        MOTHER = "mother", "Mẹ"
        FATHER = "father", "Bố"
        GRANDPARENT = "grandparent", "Ông/Bà"
        SIBLING = "sibling", "Anh/Chị/Em"
        OTHER = "other", "Khác"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardian_links")
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="student_links")
    relationship_type = models.CharField(
        "Quan hệ", max_length=20, choices=Relationship.choices, default=Relationship.OTHER
    )
    is_primary_contact = models.BooleanField("Liên hệ chính", default=False)

    class Meta:
        verbose_name = "Phụ huynh của học sinh"
        verbose_name_plural = "Phụ huynh của học sinh"
        constraints = [
            models.UniqueConstraint(fields=["student", "guardian"], name="uniq_student_guardian")
        ]

    def __str__(self) -> str:
        return f"{self.guardian} - {self.get_relationship_type_display()} của {self.student}"


class TeachingAssignment(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="assignments")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="assignments")
    is_primary = models.BooleanField("Giáo viên chính", default=False)
    assigned_from = models.DateField("Từ ngày")
    assigned_until = models.DateField("Đến ngày", null=True, blank=True)

    class Meta:
        verbose_name = "Phân công giảng dạy"
        verbose_name_plural = "Phân công giảng dạy"
        ordering = ["-assigned_from"]
        indexes = [models.Index(fields=["student", "assigned_from"])]

    def __str__(self) -> str:
        return f"{self.teacher} -> {self.student}"
