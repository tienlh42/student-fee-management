from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from people.models import Guardian, Person, Student, StudentGuardian, Teacher
from people.services import link_guardian
from tenancy.models import House

from .models import (
    FeeItem,
    FeePackage,
    FeePackageItem,
    Invoice,
    StudentDiscount,
    StudentFeePackage,
)
from .services import build_draft_lines, due_date_for, generate_invoice
from payments.models import BankAccount, Payment
from payments.services import record_manual_payment

User = get_user_model()


class InvoiceGenerationTests(TestCase):
    def setUp(self):
        self.house = House.objects.create(name="Cơ sở A", inbound_email_slug="co-so-a")
        person = Person.objects.create(full_name="Nguyễn Văn A")
        self.student = Student.objects.create(person=person, house=self.house)

        self.tuition = FeeItem.objects.create(
            house=self.house,
            name="Học phí",
            category=FeeItem.Category.TUITION,
            default_amount=Decimal("3000000"),
        )
        self.meal = FeeItem.objects.create(
            house=self.house,
            name="Tiền ăn",
            category=FeeItem.Category.MEAL,
            default_amount=Decimal("900000"),
        )

        self.package = FeePackage.objects.create(
            house=self.house, name="Gói chuẩn lớp 1", due_day_of_month=5
        )
        FeePackageItem.objects.create(fee_package=self.package, fee_item=self.tuition)
        # Override giá tiền ăn riêng cho gói này.
        FeePackageItem.objects.create(
            fee_package=self.package, fee_item=self.meal, amount=Decimal("800000")
        )
        StudentFeePackage.objects.create(
            student=self.student, fee_package=self.package, effective_from=date(2026, 1, 1)
        )

    def test_lines_use_package_override_amount(self):
        lines = build_draft_lines(self.student, date(2026, 9, 1))
        amounts = {line.name: line.amount for line in lines}
        self.assertEqual(amounts["Học phí"], Decimal("3000000"))
        self.assertEqual(amounts["Tiền ăn"], Decimal("800000"))

    def test_percentage_discount_on_single_fee_item(self):
        StudentDiscount.objects.create(
            student=self.student,
            fee_item=self.tuition,
            name="Học bổng 10%",
            discount_type=StudentDiscount.DiscountType.PERCENTAGE,
            value=Decimal("10"),
            effective_from=date(2026, 1, 1),
        )
        invoice = generate_invoice(self.student, date(2026, 9, 1))
        self.assertEqual(invoice.total_amount, Decimal("3500000"))  # 3.8tr - 300k

    def test_expired_discount_is_ignored(self):
        StudentDiscount.objects.create(
            student=self.student,
            name="Ưu đãi cũ",
            discount_type=StudentDiscount.DiscountType.FIXED,
            value=Decimal("500000"),
            effective_from=date(2026, 1, 1),
            effective_until=date(2026, 6, 30),
        )
        invoice = generate_invoice(self.student, date(2026, 9, 1))
        self.assertEqual(invoice.total_amount, Decimal("3800000"))

    def test_generation_is_idempotent_per_period(self):
        first = generate_invoice(self.student, date(2026, 9, 1))
        second = generate_invoice(self.student, date(2026, 9, 18))  # cùng kỳ
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_due_date_clamps_to_last_day_of_short_month(self):
        self.assertEqual(due_date_for(date(2026, 2, 1), 31), date(2026, 2, 28))
        self.assertEqual(due_date_for(date(2026, 9, 1), 5), date(2026, 9, 5))

    def test_adjustment_changes_net_but_not_total(self):
        invoice = generate_invoice(self.student, date(2026, 9, 1))
        invoice.adjustment_amount = Decimal("-200000")
        invoice.adjustment_note = "Nghỉ 3 buổi"
        invoice.save()

        self.assertEqual(invoice.total_amount, Decimal("3800000"))
        self.assertEqual(invoice.net_amount, Decimal("3600000"))
        self.assertEqual(invoice.outstanding_amount, Decimal("3600000"))


class BillingApiFixtureMixin:
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

        self.fee_item = FeeItem.objects.create(
            house=self.house_a,
            name="Học phí",
            category=FeeItem.Category.TUITION,
            default_amount=Decimal("3000000"),
        )
        self.package = FeePackage.objects.create(house=self.house_a, name="Gói chuẩn")
        FeePackageItem.objects.create(fee_package=self.package, fee_item=self.fee_item)
        StudentFeePackage.objects.create(
            student=self.student_a, fee_package=self.package, effective_from=date(2026, 1, 1)
        )

        self.client = APIClient()

    def _student(self, full_name: str, house: House) -> Student:
        person = Person.objects.create(full_name=full_name)
        return Student.objects.create(person=person, house=house)

    def _user(self, username: str, role_obj, *, full_name: str) -> User:
        person = Person.objects.create(full_name=full_name)
        role_obj.person = person
        role_obj.save()
        return User.objects.create_user(username=username, password="matkhau-rat-dai", person=person)


class FeeItemApiTests(BillingApiFixtureMixin, TestCase):
    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get("/api/billing/fee-items/").status_code, 403)

    def test_teacher_list_is_scoped_to_own_house(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get("/api/billing/fee-items/")
        self.assertEqual(response.data["count"], 1)

    def test_guardian_cannot_read_fee_catalog(self):
        # Biểu phí là cấu hình nội bộ — chỉ teacher/staff được đụng vào, không phải
        # cứ đọc-được-mọi-thứ như phần lớn API khác của guardian.
        self.client.force_authenticate(self.guardian_user)
        self.assertEqual(self.client.get("/api/billing/fee-items/").status_code, 403)

    def test_teacher_cannot_create_in_other_house(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            "/api/billing/fee-items/",
            {"house": self.house_b.pk, "name": "Lấn sân", "default_amount": "100000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("house", response.data)

    def test_teacher_creates_fee_item_in_own_house(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            "/api/billing/fee-items/",
            {"house": self.house_a.pk, "name": "Tiền ăn", "default_amount": "900000"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)


class FeePackageApiTests(BillingApiFixtureMixin, TestCase):
    def test_create_package_with_nested_items(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            "/api/billing/fee-packages/",
            {
                "house": self.house_a.pk,
                "name": "Gói mới",
                "due_day_of_month": 10,
                "items": [{"fee_item": self.fee_item.pk, "amount": "2500000"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        package = FeePackage.objects.get(name="Gói mới")
        self.assertEqual(package.items.count(), 1)
        self.assertEqual(package.items.first().amount, Decimal("2500000"))

    def test_item_from_other_house_is_rejected(self):
        other_item = FeeItem.objects.create(
            house=self.house_b, name="Khác cơ sở", default_amount=Decimal("1")
        )
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            "/api/billing/fee-packages/",
            {
                "house": self.house_a.pk,
                "name": "Gói lỗi",
                "due_day_of_month": 5,
                "items": [{"fee_item": other_item.pk}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("items", response.data)

    def test_update_replaces_items(self):
        self.client.force_authenticate(self.teacher_user)
        other_item = FeeItem.objects.create(
            house=self.house_a, name="Tiền ăn", default_amount=Decimal("500000")
        )
        response = self.client.patch(
            f"/api/billing/fee-packages/{self.package.pk}/",
            {"items": [{"fee_item": other_item.pk, "amount": "500000"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.package.refresh_from_db()
        self.assertEqual(self.package.items.count(), 1)
        self.assertEqual(self.package.items.first().fee_item, other_item)


class InvoiceApiTests(BillingApiFixtureMixin, TestCase):
    def test_generate_creates_invoice_for_own_house_only(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            "/api/billing/invoices/generate/", {"period": "2026-09"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["created"], 1)
        self.assertTrue(
            Invoice.objects.filter(student=self.student_a, period=date(2026, 9, 1)).exists()
        )
        self.assertFalse(Invoice.objects.filter(student=self.student_b).exists())

    def test_generate_twice_is_idempotent(self):
        self.client.force_authenticate(self.teacher_user)
        self.client.post("/api/billing/invoices/generate/", {"period": "2026-09"}, format="json")
        response = self.client.post(
            "/api/billing/invoices/generate/", {"period": "2026-09"}, format="json"
        )
        self.assertEqual(response.data, {"period": "2026-09-01", "created": 0, "existing": 1})

    def test_guardian_sees_only_own_child_invoice(self):
        generate_invoice(self.student_a, date(2026, 9, 1))
        generate_invoice(self.student_b, date(2026, 9, 1))
        self.client.force_authenticate(self.guardian_user)
        response = self.client.get("/api/billing/invoices/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["student"], self.student_a.pk)

    def test_lookup_by_code_returns_exact_match(self):
        """Trang chi tiết hóa đơn dùng qr_reference_code làm slug thay vì id."""
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get(f"/api/billing/invoices/?code={invoice.qr_reference_code}")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], invoice.pk)

    def test_lookup_by_code_is_scoped_to_accessible_students(self):
        invoice_b = generate_invoice(self.student_b, date(2026, 9, 1))
        self.client.force_authenticate(self.guardian_user)
        response = self.client.get(f"/api/billing/invoices/?code={invoice_b.qr_reference_code}")
        self.assertEqual(response.data["count"], 0)

    def test_guardian_cannot_void_invoice(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.guardian_user)
        response = self.client.post(f"/api/billing/invoices/{invoice.pk}/void/")
        self.assertEqual(response.status_code, 403)

    def test_teacher_voids_invoice(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(f"/api/billing/invoices/{invoice.pk}/void/")
        self.assertEqual(response.status_code, 200, response.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.VOID)

    def test_guardian_cannot_restore_invoice(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        invoice.status = Invoice.Status.VOID
        invoice.save(update_fields=["status"])
        self.client.force_authenticate(self.guardian_user)
        response = self.client.post(f"/api/billing/invoices/{invoice.pk}/restore/")
        self.assertEqual(response.status_code, 403)

    def test_teacher_restores_voided_invoice(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        invoice.status = Invoice.Status.VOID
        invoice.save(update_fields=["status"])
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(f"/api/billing/invoices/{invoice.pk}/restore/")
        self.assertEqual(response.status_code, 200, response.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.ISSUED)

    def test_cannot_restore_invoice_that_is_not_void(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(f"/api/billing/invoices/{invoice.pk}/restore/")
        self.assertEqual(response.status_code, 400)

    def test_cannot_void_fully_refunded_invoice(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        invoice.status = Invoice.Status.FULLY_REFUNDED
        invoice.save(update_fields=["status"])
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(f"/api/billing/invoices/{invoice.pk}/void/")
        self.assertEqual(response.status_code, 400)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.FULLY_REFUNDED)


    def test_guardian_cannot_delete_invoice(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.guardian_user)
        response = self.client.delete(f"/api/billing/invoices/{invoice.pk}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Invoice.objects.filter(pk=invoice.pk).exists())

    def test_teacher_deletes_invoice_allowing_regeneration_same_period(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.delete(f"/api/billing/invoices/{invoice.pk}/")
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())

        # Xóa xong thì sinh lại được hóa đơn khác cho đúng kỳ đó (unique constraint không còn vướng).
        regenerate = self.client.post(
            "/api/billing/invoices/generate/", {"period": "2026-09"}, format="json"
        )
        self.assertEqual(regenerate.status_code, 200, regenerate.data)
        self.assertEqual(regenerate.data["created"], 1)

    def test_cannot_delete_invoice_with_payment(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        record_manual_payment(
            invoice, Decimal("100000"), method=Payment.Method.CASH, user=self.teacher_user
        )
        self.client.force_authenticate(self.teacher_user)
        response = self.client.delete(f"/api/billing/invoices/{invoice.pk}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Invoice.objects.filter(pk=invoice.pk).exists())

    def test_guardian_cannot_record_cash_payment(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.guardian_user)
        response = self.client.post(
            f"/api/billing/invoices/{invoice.pk}/record-payment/",
            {"amount": "1000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_records_cash_payment(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/billing/invoices/{invoice.pk}/record-payment/",
            {"amount": "1000000", "method": "cash", "note": "Thu tại văn phòng"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], Invoice.Status.PARTIALLY_PAID)
        self.assertEqual(Decimal(response.data["paid_amount"]), Decimal("1000000"))

    def test_teacher_records_bank_transfer_payment(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/billing/invoices/{invoice.pk}/record-payment/",
            {"amount": "1000000", "method": "bank_transfer"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        payment = invoice.payments.get()
        self.assertEqual(payment.payment_method, Payment.Method.BANK_TRANSFER)

    def test_default_payment_method_is_cash(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/billing/invoices/{invoice.pk}/record-payment/",
            {"amount": "1000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(invoice.payments.get().payment_method, Payment.Method.CASH)

    def test_rejects_invalid_payment_method(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/billing/invoices/{invoice.pk}/record-payment/",
            {"amount": "1000000", "method": "bitcoin"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_can_split_payment_into_multiple_installments(self):
        # Hóa đơn mẫu (BillingApiFixtureMixin) tổng 3.000.000 — chia làm 2 đợt,
        # cố ý chưa trả đủ để phân biệt được với test "trả đủ" ở trên.
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        self.client.post(
            f"/api/billing/invoices/{invoice.pk}/record-payment/",
            {"amount": "1000000", "method": "cash", "note": "Đợt 1"},
            format="json",
        )
        response = self.client.post(
            f"/api/billing/invoices/{invoice.pk}/record-payment/",
            {"amount": "1000000", "method": "bank_transfer", "note": "Đợt 2"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(invoice.payments.count(), 2)
        self.assertEqual(Decimal(response.data["paid_amount"]), Decimal("2000000"))
        self.assertEqual(response.data["status"], Invoice.Status.PARTIALLY_PAID)

    def test_cannot_record_cash_payment_on_void_invoice(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        invoice.status = Invoice.Status.VOID
        invoice.save(update_fields=["status"])
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/billing/invoices/{invoice.pk}/record-payment/",
            {"amount": "1000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_guardian_cannot_view_payment_history(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        record_manual_payment(
            invoice, Decimal("500000"), method=Payment.Method.CASH, user=self.teacher_user
        )
        self.client.force_authenticate(self.guardian_user)
        response = self.client.get(f"/api/billing/invoices/{invoice.pk}/payments/")
        self.assertEqual(response.status_code, 403)

    def test_teacher_views_payment_history(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        record_manual_payment(
            invoice,
            Decimal("500000"),
            method=Payment.Method.CASH,
            user=self.teacher_user,
            note="Thu tiền mặt",
        )
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get(f"/api/billing/invoices/{invoice.pk}/payments/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(Decimal(response.data[0]["amount_applied"]), Decimal("500000"))
        self.assertEqual(response.data[0]["payment_method"], "cash")

    def test_adjustment_editable_but_total_amount_is_not(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.client.force_authenticate(self.teacher_user)
        response = self.client.patch(
            f"/api/billing/invoices/{invoice.pk}/",
            {"adjustment_amount": "-100000", "total_amount": "999"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.adjustment_amount, Decimal("-100000"))
        self.assertEqual(invoice.total_amount, Decimal("3000000"))


class InvoicePrintApiTests(BillingApiFixtureMixin, TestCase):
    """Trang in/xem trước hóa đơn (`invoice_template.html`) — 2 biến thể theo status."""

    def setUp(self):
        super().setUp()
        self.invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        self.invoice.status = Invoice.Status.ISSUED
        self.invoice.save(update_fields=["status"])
        account = BankAccount(
            house=self.house_a,
            bank_code="970436",
            account_holder_name="NGUYEN THI LAN",
            is_primary=True,
        )
        account.set_account_number("0011223348899")
        account.save()

    def test_guardian_can_print_own_child_invoice(self):
        self.client.force_authenticate(self.guardian_user)
        response = self.client.get(f"/api/billing/invoices/{self.invoice.pk}/print/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        html = response.content.decode()
        self.assertIn("Hóa đơn kỳ", html)
        self.assertIn(self.invoice.qr_reference_code, html)
        self.assertIn("img.vietqr.io", html)

    def test_guardian_cannot_print_other_students_invoice(self):
        other_invoice = generate_invoice(self.student_b, date(2026, 9, 1))
        self.client.force_authenticate(self.guardian_user)
        response = self.client.get(f"/api/billing/invoices/{other_invoice.pk}/print/")
        self.assertEqual(response.status_code, 404)

    def test_paid_invoice_prints_receipt_without_qr(self):
        record_manual_payment(
            self.invoice, self.invoice.net_amount, method=Payment.Method.CASH, user=self.teacher_user
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

        self.client.force_authenticate(self.guardian_user)
        response = self.client.get(f"/api/billing/invoices/{self.invoice.pk}/print/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Đã đóng đủ", html)
        self.assertNotIn("img.vietqr.io", html)
        self.assertIn("Lịch sử thanh toán", html)
