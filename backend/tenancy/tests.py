"""Test lệnh seed_demo — trọng tâm là tính idempotent và lớp chặn khi DEBUG=False."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from billing.models import FeePackage, Invoice
from people.models import Guardian, Person, Student, StudentGuardian, Teacher

from .models import House

User = get_user_model()


def seed(**kwargs) -> str:
    out = StringIO()
    call_command("seed_demo", stdout=out, **kwargs)
    return out.getvalue()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def test_creates_house_teachers_and_students(self):
        seed(students=5)

        self.assertEqual(House.objects.count(), 1)
        self.assertEqual(Student.objects.count(), 5)
        self.assertEqual(Teacher.objects.count(), 2)
        self.assertEqual(Guardian.objects.count(), 5)
        self.assertTrue(User.objects.filter(username="colan").exists())

    def test_rerun_does_not_duplicate(self):
        seed(students=5)
        seed(students=5)

        self.assertEqual(House.objects.count(), 1)
        self.assertEqual(Student.objects.count(), 5)
        self.assertEqual(StudentGuardian.objects.count(), 5)
        self.assertEqual(FeePackage.objects.count(), 1)

    def test_rerun_with_more_students_only_adds_the_new_ones(self):
        seed(students=3)
        seed(students=6)
        self.assertEqual(Student.objects.count(), 6)

    def test_seeded_teacher_can_log_in(self):
        seed(students=2, password="mat-khau-thu-nghiem")
        self.assertTrue(
            self.client.login(username="colan", password="mat-khau-thu-nghiem")
        )

    def test_guardian_account_is_read_only(self):
        from accounts.services import role_for

        seed(students=2)
        guardian_user = User.objects.get(username="phuhuynh")
        role = role_for(guardian_user)

        self.assertTrue(role.is_guardian)
        self.assertFalse(role.is_teacher)
        self.assertFalse(role.can_see_bank_data)

    def test_rerun_keeps_existing_password(self):
        seed(students=2, password="mat-khau-ban-dau")
        seed(students=2, password="mat-khau-khac")
        # Lệnh chỉ đặt mật khẩu cho tài khoản mới — không được ghi đè tài khoản đang dùng.
        self.assertTrue(self.client.login(username="colan", password="mat-khau-ban-dau"))

    def test_invoices_flag_generates_current_period(self):
        seed(students=5, invoices=True)
        active = Student.objects.filter(status=Student.Status.ACTIVE).count()
        self.assertEqual(Invoice.objects.count(), active)
        self.assertTrue(all(inv.total_amount > 0 for inv in Invoice.objects.all()))

    def test_invoices_are_idempotent_across_runs(self):
        seed(students=5, invoices=True)
        before = Invoice.objects.count()
        seed(students=5, invoices=True)
        self.assertEqual(Invoice.objects.count(), before)

    def test_reset_removes_everything_it_created(self):
        seed(students=5, invoices=True)
        seed(students=5, reset=True)

        self.assertEqual(House.objects.count(), 1)
        self.assertEqual(Student.objects.count(), 5)
        # Sau reset thì hóa đơn cũ biến mất (lần seed lại không truyền --invoices).
        self.assertEqual(Invoice.objects.count(), 0)

    def test_reset_leaves_no_orphan_person(self):
        seed(students=4)
        call_command("seed_demo", "--reset", students=4, stdout=StringIO())
        # Mỗi Person còn lại phải gắn với đúng một vai trò, không có bản mồ côi.
        orphans = Person.objects.filter(
            student__isnull=True, teacher__isnull=True, guardian__isnull=True, user__isnull=True
        )
        self.assertEqual(orphans.count(), 0)

    def test_rejects_out_of_range_student_count(self):
        with self.assertRaises(CommandError):
            seed(students=0)
        with self.assertRaises(CommandError):
            seed(students=999)


class SeedDemoGuardTests(TestCase):
    """Đây là app quản lý tiền — dữ liệu giả không được rơi vào DB thật."""

    @override_settings(DEBUG=False)
    def test_refuses_to_run_without_debug(self):
        with self.assertRaises(CommandError):
            seed(students=2)
        self.assertEqual(House.objects.count(), 0)

    @override_settings(DEBUG=False)
    def test_force_allows_seeding_without_debug(self):
        seed(students=2, force=True)
        self.assertEqual(Student.objects.count(), 2)

    @override_settings(DEBUG=False)
    def test_force_does_not_unlock_reset(self):
        with self.assertRaises(CommandError):
            seed(students=2, force=True, reset=True)
