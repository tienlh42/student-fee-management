"""Serializer cho app people.

Student/Teacher/Guardian đều lấy `person_id` làm khóa chính, nên `person`
luôn là object lồng có thể ghi — không thể tạo vai trò trước khi có Person.
"""

from rest_framework import serializers

from tenancy.models import House

from .models import Guardian, Person, Student, StudentGuardian, Teacher, TeachingAssignment
from .services import can_write_in_house

PERSON_FIELDS = [
    "id",
    "full_name",
    "gender",
    "date_of_birth",
    "place_of_birth",
    "nationality",
    "ethnicity",
    "id_number",
    "id_issued_date",
    "id_issued_place",
    "permanent_address",
    "current_address",
    "phone",
    "email",
    "avatar_url",
]


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = PERSON_FIELDS
        read_only_fields = ["id"]


class GuardianBriefSerializer(serializers.ModelSerializer):
    """Bản rút gọn dùng khi nhúng vào danh sách học sinh — tránh N+1 field thừa."""

    full_name = serializers.CharField(source="person.full_name", read_only=True)
    phone = serializers.CharField(source="person.phone", read_only=True)

    class Meta:
        model = Guardian
        fields = ["person_id", "full_name", "phone", "occupation"]


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.person.full_name", read_only=True)
    guardian_phone = serializers.CharField(source="guardian.person.phone", read_only=True)
    relationship_type_display = serializers.CharField(
        source="get_relationship_type_display", read_only=True
    )

    class Meta:
        model = StudentGuardian
        fields = [
            "id",
            "student",
            "guardian",
            "guardian_name",
            "guardian_phone",
            "relationship_type",
            "relationship_type_display",
            "is_primary_contact",
        ]


class StudentSerializer(serializers.ModelSerializer):
    person = PersonSerializer()
    # person_id là PK của Student; phơi ra dưới tên `id` cho frontend dùng làm row key.
    id = serializers.IntegerField(source="person_id", read_only=True)
    full_name = serializers.CharField(source="person.full_name", read_only=True)
    phone = serializers.CharField(source="person.phone", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    house_name = serializers.CharField(source="house.name", read_only=True)
    guardians = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "person",
            "full_name",
            "phone",
            "house",
            "house_name",
            "class_grade",
            "status",
            "status_display",
            "enrolled_date",
            "guardians",
        ]

    def get_guardians(self, student) -> list[dict]:
        return [
            {
                **GuardianBriefSerializer(link.guardian).data,
                "relationship_type": link.relationship_type,
                "relationship_type_display": link.get_relationship_type_display(),
                "is_primary_contact": link.is_primary_contact,
            }
            for link in student.guardian_links.all()
        ]

    def validate_house(self, house: House) -> House:
        """Teacher toàn quyền *trong house của mình* — chặn ghi sang cơ sở khác."""
        user = self.context["request"].user
        if not can_write_in_house(user, house.pk):
            raise serializers.ValidationError("Bạn không có quyền trên cơ sở này.")
        return house

    def create(self, validated_data):
        from .services import create_student

        person_data = validated_data.pop("person")
        house = validated_data.pop("house")
        return create_student(person_data=person_data, house=house, **validated_data)

    def update(self, instance, validated_data):
        from .services import update_student

        person_data = validated_data.pop("person", None)
        return update_student(instance, person_data=person_data, **validated_data)


class GuardianSerializer(serializers.ModelSerializer):
    person = PersonSerializer()
    id = serializers.IntegerField(source="person_id", read_only=True)
    full_name = serializers.CharField(source="person.full_name", read_only=True)
    phone = serializers.CharField(source="person.phone", read_only=True)

    class Meta:
        model = Guardian
        fields = ["id", "person", "full_name", "phone", "occupation"]

    def create(self, validated_data):
        person = Person.objects.create(**validated_data.pop("person"))
        return Guardian.objects.create(person=person, **validated_data)

    def update(self, instance, validated_data):
        person_data = validated_data.pop("person", None)
        if person_data:
            for field, value in person_data.items():
                setattr(instance.person, field, value)
            instance.person.save()
        return super().update(instance, validated_data)


class TeacherSerializer(serializers.ModelSerializer):
    person = PersonSerializer()
    id = serializers.IntegerField(source="person_id", read_only=True)
    full_name = serializers.CharField(source="person.full_name", read_only=True)
    house_name = serializers.CharField(source="house.name", read_only=True)

    class Meta:
        model = Teacher
        fields = ["id", "person", "full_name", "house", "house_name"]

    def validate_house(self, house: House) -> House:
        if not can_write_in_house(self.context["request"].user, house.pk):
            raise serializers.ValidationError("Bạn không có quyền trên cơ sở này.")
        return house

    def create(self, validated_data):
        person = Person.objects.create(**validated_data.pop("person"))
        return Teacher.objects.create(person=person, **validated_data)

    def update(self, instance, validated_data):
        person_data = validated_data.pop("person", None)
        if person_data:
            for field, value in person_data.items():
                setattr(instance.person, field, value)
            instance.person.save()
        return super().update(instance, validated_data)


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.person.full_name", read_only=True)
    student_name = serializers.CharField(source="student.person.full_name", read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "student",
            "student_name",
            "is_primary",
            "assigned_from",
            "assigned_until",
        ]
