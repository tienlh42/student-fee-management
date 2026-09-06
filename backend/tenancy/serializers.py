from rest_framework import serializers

from .models import House


class HouseSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = House
        fields = ["id", "name", "address", "inbound_email_slug", "student_count", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_student_count(self, house) -> int:
        return house.students.count()
