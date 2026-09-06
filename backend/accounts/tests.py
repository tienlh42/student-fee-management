"""Test hồ sơ cá nhân và quyền trên cơ sở.

Ranh giới quan trọng nhất: `house` đọc được nhưng KHÔNG sửa được qua hồ sơ cá
nhân, và chỉ superuser mới CRUD được `House`.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from people.models import Guardian, Person, Student, Teacher
from people.services import houses_of, link_guardian
from tenancy.models import House

from .services import role_for

User = get_user_model()


class ProfileFixtureMixin:
    def setUp(self):
        self.house_a = House.objects.create(name="Cơ sở A", inbound_email_slug="co-so-a")
        self.house_b = House.objects.create(name="Cơ sở B", inbound_email_slug="co-so-b")

        teacher_person = Person.objects.create(full_name="Cô Lan", phone="0900000001")
        Teacher.objects.create(person=teacher_person, house=self.house_a)
        self.teacher = User.objects.create_user(
            username="colan", password="matkhau-rat-dai", person=teacher_person
        )

        guardian_person = Person.objects.create(full_name="Chị Hoa")
        guardian = Guardian.objects.create(person=guardian_person)
        self.guardian = User.objects.create_user(
            username="phuhuynh", password="matkhau-rat-dai", person=guardian_person
        )
        child = Student.objects.create(
            person=Person.objects.create(full_name="Bé An"), house=self.house_b
        )
        link_guardian(child, guardian=guardian, is_primary_contact=True)

        self.superuser = User.objects.create_superuser(
            username="sep", password="matkhau-rat-dai"
        )
        self.client = APIClient()


class RoleTests(ProfileFixtureMixin, TestCase):
    def test_only_superuser_can_manage_houses(self):
        self.assertTrue(role_for(self.superuser).can_manage_houses)
        self.assertFalse(role_for(self.teacher).can_manage_houses)
        self.assertFalse(role_for(self.guardian).can_manage_houses)

    def test_staff_admin_is_not_automatically_superuser(self):
        staff = User.objects.create_user(
            username="nhanvien", password="matkhau-rat-dai", is_staff=True
        )
        role = role_for(staff)
        self.assertTrue(role.is_staff_admin)
        self.assertFalse(role.can_manage_houses)

    def test_houses_of_teacher_and_guardian_differ_in_via(self):
        self.assertEqual(
            houses_of(self.teacher),
            [{"id": self.house_a.pk, "name": "Cơ sở A", "via": "teacher", "via_display": "Giáo viên"}],
        )
        self.assertEqual(
            houses_of(self.guardian),
            [{"id": self.house_b.pk, "name": "Cơ sở B", "via": "guardian", "via_display": "Phụ huynh"}],
        )

    def test_houses_of_superuser_lists_everything(self):
        self.assertEqual(len(houses_of(self.superuser)), 2)


class ProfileApiTests(ProfileFixtureMixin, TestCase):
    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get("/api/accounts/profile/").status_code, 403)

    def test_get_returns_person_houses_and_role(self):
        self.client.force_authenticate(self.teacher)
        data = self.client.get("/api/accounts/profile/").data

        self.assertEqual(data["username"], "colan")
        self.assertEqual(data["person"]["full_name"], "Cô Lan")
        self.assertEqual(data["houses"][0]["name"], "Cơ sở A")
        self.assertTrue(data["role"]["is_teacher"])

    def test_patch_updates_own_person(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.patch(
            "/api/accounts/profile/",
            {"person": {"full_name": "Nguyễn Thị Lan", "phone": "0988888888"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        self.teacher.person.refresh_from_db()
        self.assertEqual(self.teacher.person.full_name, "Nguyễn Thị Lan")
        self.assertEqual(self.teacher.person.phone, "0988888888")

    def test_patch_updates_account_email(self):
        self.client.force_authenticate(self.teacher)
        self.client.patch(
            "/api/accounts/profile/", {"account_email": "lan@truong.vn"}, format="json"
        )
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.email, "lan@truong.vn")

    def test_patch_ignores_house_field(self):
        # House không nằm trong serializer -> gửi lên cũng không đổi được gì.
        self.client.force_authenticate(self.teacher)
        self.client.patch(
            "/api/accounts/profile/",
            {"house": self.house_b.pk, "houses": [{"id": self.house_b.pk}]},
            format="json",
        )
        teacher_row = Teacher.objects.get(person=self.teacher.person)
        self.assertEqual(teacher_row.house, self.house_a)

    def test_patch_cannot_touch_another_user(self):
        """Không có route nào nhận id — hồ sơ luôn là của request.user."""
        self.client.force_authenticate(self.guardian)
        self.client.patch(
            "/api/accounts/profile/", {"person": {"full_name": "Kẻ mạo danh"}}, format="json"
        )
        self.teacher.person.refresh_from_db()
        self.assertEqual(self.teacher.person.full_name, "Cô Lan")

    def test_patch_creates_person_for_account_without_one(self):
        self.client.force_authenticate(self.superuser)
        self.assertIsNone(self.superuser.person_id)

        response = self.client.patch(
            "/api/accounts/profile/",
            {"person": {"full_name": "Sếp Tổng", "phone": "0911111111"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        self.superuser.refresh_from_db()
        self.assertIsNotNone(self.superuser.person_id)
        self.assertEqual(self.superuser.person.full_name, "Sếp Tổng")

    def test_creating_person_requires_full_name(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.patch(
            "/api/accounts/profile/", {"person": {"phone": "0911111111"}}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.superuser.refresh_from_db()
        self.assertIsNone(self.superuser.person_id)

    def test_invalid_email_is_rejected(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.patch(
            "/api/accounts/profile/", {"account_email": "khong-phai-email"}, format="json"
        )
        self.assertEqual(response.status_code, 400)


class ChangePasswordTests(ProfileFixtureMixin, TestCase):
    def test_requires_correct_current_password(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            "/api/accounts/change-password/",
            {"current_password": "sai-roi", "new_password": "mat-khau-moi-dai-ngoang"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("current_password", response.data)

    def test_rejects_weak_password(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            "/api/accounts/change-password/",
            {"current_password": "matkhau-rat-dai", "new_password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_password", response.data)

    def test_changes_password_and_keeps_session(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            "/api/accounts/change-password/",
            {"current_password": "matkhau-rat-dai", "new_password": "mat-khau-moi-dai-ngoang"},
            format="json",
        )
        self.assertEqual(response.status_code, 204)

        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("mat-khau-moi-dai-ngoang"))


class HouseApiTests(ProfileFixtureMixin, TestCase):
    def test_teacher_sees_only_own_house(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.get("/api/tenancy/houses/")
        self.assertEqual([h["name"] for h in response.data["results"]], ["Cơ sở A"])

    def test_superuser_sees_every_house(self):
        self.client.force_authenticate(self.superuser)
        self.assertEqual(self.client.get("/api/tenancy/houses/").data["count"], 2)

    def test_teacher_cannot_create_house(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            "/api/tenancy/houses/",
            {"name": "Cơ sở lậu", "inbound_email_slug": "co-so-lau"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(House.objects.count(), 2)

    def test_teacher_cannot_rename_own_house(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.patch(
            f"/api/tenancy/houses/{self.house_a.pk}/", {"name": "Tên mới"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_delete_house(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.delete(f"/api/tenancy/houses/{self.house_a.pk}/")
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_crud_house(self):
        self.client.force_authenticate(self.superuser)

        created = self.client.post(
            "/api/tenancy/houses/",
            {"name": "Cơ sở C", "inbound_email_slug": "co-so-c"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)

        renamed = self.client.patch(
            f"/api/tenancy/houses/{created.data['id']}/", {"name": "Cơ sở C2"}, format="json"
        )
        self.assertEqual(renamed.data["name"], "Cơ sở C2")

        self.assertEqual(
            self.client.delete(f"/api/tenancy/houses/{created.data['id']}/").status_code, 204
        )

    def test_house_with_students_is_protected_from_deletion(self):
        self.client.force_authenticate(self.superuser)
        # Student.house dùng on_delete=PROTECT — xóa cơ sở còn học sinh phải nổ,
        # không được lặng lẽ kéo theo dữ liệu.
        with self.assertRaises(Exception):
            self.client.delete(f"/api/tenancy/houses/{self.house_b.pk}/")
