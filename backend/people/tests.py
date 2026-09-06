"""Test phạm vi dữ liệu và phân quyền của app people.

Trọng tâm là ranh giới: guardian chỉ thấy con mình và không ghi được gì;
teacher chỉ toàn quyền *trong house của mình*, không lan sang cơ sở khác.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.models import House

from .models import Guardian, Person, Student, StudentGuardian, Teacher
from .services import accessible_students, can_write_in_house, link_guardian

User = get_user_model()


class PeopleFixtureMixin:
    def setUp(self):
        self.house_a = House.objects.create(name="Cơ sở A", inbound_email_slug="co-so-a")
        self.house_b = House.objects.create(name="Cơ sở B", inbound_email_slug="co-so-b")

        self.student_a = self._student("Học sinh A", self.house_a)
        self.student_b = self._student("Học sinh B", self.house_b)

        self.teacher_user = self._user(
            "co_giao_a", Teacher(house=self.house_a), full_name="Cô giáo A"
        )
        self.guardian_user = self._user("phu_huynh", Guardian(), full_name="Phụ huynh A")
        link_guardian(
            self.student_a,
            guardian=Guardian.objects.get(person=self.guardian_user.person),
            relationship_type=StudentGuardian.Relationship.MOTHER,
            is_primary_contact=True,
        )

    def _student(self, full_name: str, house: House) -> Student:
        person = Person.objects.create(full_name=full_name)
        return Student.objects.create(person=person, house=house, class_grade="1A")

    def _user(self, username: str, role_obj, *, full_name: str) -> User:
        person = Person.objects.create(full_name=full_name)
        role_obj.person = person
        role_obj.save()
        return User.objects.create_user(username=username, password="matkhau-rat-dai", person=person)


class AccessScopeTests(PeopleFixtureMixin, TestCase):
    def test_teacher_sees_only_own_house(self):
        students = accessible_students(self.teacher_user)
        self.assertEqual(list(students), [self.student_a])

    def test_guardian_sees_only_linked_students(self):
        students = accessible_students(self.guardian_user)
        self.assertEqual(list(students), [self.student_a])

    def test_user_without_person_sees_nothing(self):
        stranger = User.objects.create_user(username="la_mat", password="matkhau-rat-dai")
        self.assertEqual(list(accessible_students(stranger)), [])

    def test_staff_sees_every_house(self):
        admin = User.objects.create_user(
            username="admin", password="matkhau-rat-dai", is_staff=True
        )
        self.assertEqual(accessible_students(admin).count(), 2)

    def test_teacher_cannot_write_in_other_house(self):
        self.assertTrue(can_write_in_house(self.teacher_user, self.house_a.pk))
        self.assertFalse(can_write_in_house(self.teacher_user, self.house_b.pk))

    def test_link_guardian_keeps_single_primary_contact(self):
        other_person = Person.objects.create(full_name="Bố A")
        other = Guardian.objects.create(person=other_person)
        link_guardian(self.student_a, guardian=other, is_primary_contact=True)

        primaries = StudentGuardian.objects.filter(
            student=self.student_a, is_primary_contact=True
        )
        self.assertEqual(primaries.count(), 1)
        self.assertEqual(primaries.first().guardian, other)


class AuthEndpointTests(PeopleFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient(enforce_csrf_checks=True)

    def _csrf_token(self) -> str:
        """Đọc lại cookie mỗi lần dùng — `login()` xoay token nên bản cũ hết hiệu lực."""
        if "csrftoken" not in self.client.cookies:
            self.client.get("/api/accounts/me/")
        return self.client.cookies["csrftoken"].value

    def test_me_reports_unauthenticated_without_error(self):
        response = self.client.get("/api/accounts/me/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["authenticated"])

    def test_login_requires_csrf_token(self):
        # Login là request chưa đăng nhập -> SessionAuthentication không kiểm CSRF,
        # nên `csrf_protect` trên view là lớp bảo vệ duy nhất.
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "co_giao_a", "password": "matkhau-rat-dai"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_login_then_me_reports_role(self):
        token = self._csrf_token()
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "co_giao_a", "password": "matkhau-rat-dai"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["role"]["is_teacher"])
        self.assertTrue(response.data["role"]["can_see_bank_data"])

        me = self.client.get("/api/accounts/me/")
        self.assertTrue(me.data["authenticated"])
        self.assertEqual(me.data["user"]["house_ids"], [self.house_a.pk])

    def test_guardian_never_sees_bank_data(self):
        token = self._csrf_token()
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "phu_huynh", "password": "matkhau-rat-dai"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertFalse(response.data["role"]["can_see_bank_data"])

    def test_wrong_password_rejected(self):
        token = self._csrf_token()
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "co_giao_a", "password": "sai-mat-khau"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_clears_session(self):
        self.client.post(
            "/api/accounts/login/",
            {"username": "co_giao_a", "password": "matkhau-rat-dai"},
            format="json",
            HTTP_X_CSRFTOKEN=self._csrf_token(),
        )
        # django_login() gọi rotate_token() -> token cũ hết hiệu lực, phải đọc lại.
        response = self.client.post(
            "/api/accounts/logout/", format="json", HTTP_X_CSRFTOKEN=self._csrf_token()
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.client.get("/api/accounts/me/").data["authenticated"])


class StudentApiTests(PeopleFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get("/api/people/students/").status_code, 403)

    def test_teacher_list_is_scoped_to_own_house(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get("/api/people/students/")
        names = [row["full_name"] for row in response.data["results"]]
        self.assertEqual(names, ["Học sinh A"])

    def test_teacher_creates_student_with_nested_person(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            "/api/people/students/",
            {
                "person": {"full_name": "Học sinh mới", "phone": "0900000000"},
                "house": self.house_a.pk,
                "class_grade": "2B",
                "status": Student.Status.ACTIVE,
                "enrolled_date": "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        created = Student.objects.get(person__full_name="Học sinh mới")
        self.assertEqual(created.house, self.house_a)
        self.assertEqual(created.person.phone, "0900000000")

    def test_teacher_cannot_create_in_other_house(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            "/api/people/students/",
            {"person": {"full_name": "Lấn sân"}, "house": self.house_b.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("house", response.data)

    def test_teacher_cannot_edit_student_of_other_house(self):
        self.client.force_authenticate(self.teacher_user)
        # Không nằm trong queryset đã lọc -> 404, không lộ sự tồn tại của bản ghi.
        response = self.client.patch(
            f"/api/people/students/{self.student_b.pk}/",
            {"class_grade": "9Z"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_guardian_is_read_only(self):
        self.client.force_authenticate(self.guardian_user)
        self.assertEqual(self.client.get("/api/people/students/").status_code, 200)

        response = self.client.post(
            "/api/people/students/",
            {"person": {"full_name": "Không được phép"}, "house": self.house_a.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_patch_updates_nested_person_fields(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.patch(
            f"/api/people/students/{self.student_a.pk}/",
            {"person": {"full_name": "Học sinh A", "phone": "0911111111"}, "class_grade": "3C"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.student_a.refresh_from_db()
        self.student_a.person.refresh_from_db()
        self.assertEqual(self.student_a.class_grade, "3C")
        self.assertEqual(self.student_a.person.phone, "0911111111")

    def test_search_matches_name_and_phone(self):
        self.student_a.person.phone = "0987654321"
        self.student_a.person.save()
        self.client.force_authenticate(self.teacher_user)

        self.assertEqual(
            self.client.get("/api/people/students/?search=98765").data["count"], 1
        )
        self.assertEqual(
            self.client.get("/api/people/students/?search=khong-co-ai").data["count"], 0
        )

    def test_list_embeds_primary_guardian(self):
        self.client.force_authenticate(self.teacher_user)
        row = self.client.get("/api/people/students/").data["results"][0]
        self.assertEqual(row["guardians"][0]["full_name"], "Phụ huynh A")
        self.assertTrue(row["guardians"][0]["is_primary_contact"])

    def test_meta_lists_only_reachable_houses(self):
        self.client.force_authenticate(self.teacher_user)
        meta = self.client.get("/api/people/students/meta/").data
        self.assertEqual([h["value"] for h in meta["houses"]], [self.house_a.pk])
        self.assertEqual(meta["default_house"], self.house_a.pk)
        self.assertEqual(meta["class_grades"], ["1A"])

    def test_link_and_unlink_guardian(self):
        self.client.force_authenticate(self.teacher_user)
        bo = Guardian.objects.create(person=Person.objects.create(full_name="Bố A"))

        response = self.client.post(
            f"/api/people/students/{self.student_a.pk}/guardians/",
            {"guardian": bo.pk, "relationship_type": "father", "is_primary_contact": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.student_a.guardian_links.count(), 2)

        response = self.client.delete(
            f"/api/people/students/{self.student_a.pk}/guardians/{bo.pk}/"
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.student_a.guardian_links.count(), 1)

    def test_guardian_cannot_link_guardians(self):
        self.client.force_authenticate(self.guardian_user)
        response = self.client.post(
            f"/api/people/students/{self.student_a.pk}/guardians/",
            {"guardian": self.guardian_user.person_id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_enrolled_date_roundtrips(self):
        self.student_a.enrolled_date = date(2026, 9, 1)
        self.student_a.save()
        self.client.force_authenticate(self.teacher_user)
        row = self.client.get("/api/people/students/").data["results"][0]
        self.assertEqual(row["enrolled_date"], "2026-09-01")
