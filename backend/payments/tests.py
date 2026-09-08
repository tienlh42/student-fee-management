from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from billing.models import FeeItem, FeePackage, FeePackageItem, Invoice, StudentFeePackage
from billing.services import generate_invoice
from billing.tests import BillingApiFixtureMixin
from people.models import Person, Student
from tenancy.models import House

from .models import IncomingTransaction, Payment
from .services import extract_reference_codes, record_manual_payment, try_auto_match


class ReferenceExtractionTests(TestCase):
    def test_extracts_code_despite_bank_noise(self):
        content = "CT DEN:123 NGUYEN VAN A chuyen tien hp-ACDEF345 GD 987654"
        self.assertEqual(extract_reference_codes(content), ["HPACDEF345"])

    def test_returns_empty_when_no_code(self):
        self.assertEqual(extract_reference_codes("NGUYEN VAN A chuyen tien hoc phi"), [])


class AutoMatchTests(TestCase):
    def setUp(self):
        self.house = House.objects.create(name="Cơ sở A", inbound_email_slug="co-so-a")
        person = Person.objects.create(full_name="Nguyễn Văn A")
        self.student = Student.objects.create(person=person, house=self.house)

        item = FeeItem.objects.create(
            house=self.house, name="Học phí", default_amount=Decimal("1000000")
        )
        package = FeePackage.objects.create(house=self.house, name="Gói cơ bản")
        FeePackageItem.objects.create(fee_package=package, fee_item=item)
        StudentFeePackage.objects.create(
            student=self.student, fee_package=package, effective_from=date(2026, 1, 1)
        )

        self.invoice = generate_invoice(self.student, date(2026, 9, 1))

    def _incoming(self, amount, content):
        return IncomingTransaction.objects.create(
            house=self.house,
            amount=Decimal(amount),
            transfer_content=content,
            transaction_time=timezone.now(),
            provider_transaction_id=f"tx-{IncomingTransaction.objects.count() + 1}",
        )

    def test_exact_amount_marks_invoice_paid(self):
        incoming = self._incoming("1000000", f"CK {self.invoice.qr_reference_code}")
        payments = try_auto_match(incoming)

        self.assertEqual(len(payments), 1)
        incoming.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(incoming.status, IncomingTransaction.Status.MATCHED)
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

    def test_underpayment_leaves_invoice_partially_paid(self):
        incoming = self._incoming("400000", self.invoice.qr_reference_code)
        try_auto_match(incoming)

        self.invoice.refresh_from_db()
        incoming.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PARTIALLY_PAID)
        self.assertEqual(self.invoice.outstanding_amount, Decimal("600000"))
        self.assertEqual(incoming.status, IncomingTransaction.Status.MATCHED)

    def test_overpayment_only_allocates_outstanding(self):
        incoming = self._incoming("1500000", self.invoice.qr_reference_code)
        try_auto_match(incoming)

        incoming.refresh_from_db()
        self.assertEqual(incoming.allocated_amount, Decimal("1000000"))
        self.assertEqual(incoming.unallocated_amount, Decimal("500000"))
        self.assertEqual(incoming.status, IncomingTransaction.Status.PARTIALLY_MATCHED)

    def test_rerunning_match_does_not_double_pay(self):
        incoming = self._incoming("1000000", self.invoice.qr_reference_code)
        try_auto_match(incoming)
        incoming.refresh_from_db()
        try_auto_match(incoming)

        self.assertEqual(Payment.objects.filter(invoice=self.invoice).count(), 1)

    def test_unknown_code_leaves_transaction_unmatched(self):
        incoming = self._incoming("1000000", "CK HPZZZZZZZZ")
        self.assertEqual(try_auto_match(incoming), [])
        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingTransaction.Status.UNMATCHED)

    def test_cash_payment_requires_a_recorder(self):
        with self.assertRaises(ValueError):
            record_manual_payment(
                self.invoice, Decimal("100000"), method=Payment.Method.CASH, user=None
            )

    def test_rejects_unknown_payment_method(self):
        with self.assertRaises(ValueError):
            record_manual_payment(self.invoice, Decimal("100000"), method="bitcoin", user=object())


class IncomingTransactionApiTests(BillingApiFixtureMixin, TestCase):
    def _incoming(self, house, amount, content, *, status=IncomingTransaction.Status.UNMATCHED):
        return IncomingTransaction.objects.create(
            house=house,
            amount=Decimal(amount),
            transfer_content=content,
            transaction_time=timezone.now(),
            provider_transaction_id=f"tx-{IncomingTransaction.objects.count() + 1}",
            status=status,
        )

    def test_guardian_has_no_access_to_transactions(self):
        self._incoming(self.house_a, "1000000", "CK noi dung")
        self.client.force_authenticate(self.guardian_user)
        response = self.client.get("/api/payments/incoming-transactions/")
        self.assertEqual(response.status_code, 403)

    def test_teacher_lists_own_house_transactions_only(self):
        self._incoming(self.house_a, "1000000", "CK house a")
        self._incoming(self.house_b, "2000000", "CK house b")
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get("/api/payments/incoming-transactions/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["house"], self.house_a.pk)

    def test_retry_match_action(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        incoming = self._incoming(self.house_a, "3000000", invoice.qr_reference_code)
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/payments/incoming-transactions/{incoming.pk}/retry-match/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["matched"], 1)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)

    def test_allocate_manually_action(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        incoming = self._incoming(self.house_a, "3000000", "khong khop ma nao")
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/payments/incoming-transactions/{incoming.pk}/allocate/",
            {"invoice": invoice.pk, "amount": "1500000"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PARTIALLY_PAID)

    def test_allocate_rejects_invoice_from_other_house(self):
        invoice_b = generate_invoice(self.student_b, date(2026, 9, 1))
        incoming = self._incoming(self.house_a, "1000000", "khong khop ma nao")
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/payments/incoming-transactions/{incoming.pk}/allocate/",
            {"invoice": invoice_b.pk, "amount": "100000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_allocate_rejects_void_invoice(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        invoice.status = Invoice.Status.VOID
        invoice.save(update_fields=["status"])
        incoming = self._incoming(self.house_a, "1000000", "khong khop ma nao")
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/payments/incoming-transactions/{incoming.pk}/allocate/",
            {"invoice": invoice.pk, "amount": "100000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_ignore_action(self):
        incoming = self._incoming(self.house_a, "1000000", "khong khop ma nao")
        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/payments/incoming-transactions/{incoming.pk}/ignore/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingTransaction.Status.IGNORED)

    def test_cannot_ignore_partially_matched_transaction(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        incoming = self._incoming(self.house_a, "1000000", invoice.qr_reference_code)
        try_auto_match(incoming)
        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingTransaction.Status.MATCHED)

        self.client.force_authenticate(self.teacher_user)
        response = self.client.post(
            f"/api/payments/incoming-transactions/{incoming.pk}/ignore/"
        )
        self.assertEqual(response.status_code, 400)


class PaymentApiTests(BillingApiFixtureMixin, TestCase):
    def test_guardian_has_no_access_to_payments(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        record_manual_payment(
            invoice, Decimal("100000"), method=Payment.Method.CASH, user=self.teacher_user
        )
        self.client.force_authenticate(self.guardian_user)
        response = self.client.get("/api/payments/payments/")
        self.assertEqual(response.status_code, 403)

    def test_teacher_lists_own_house_payments_only(self):
        invoice_a = generate_invoice(self.student_a, date(2026, 9, 1))
        invoice_b = generate_invoice(self.student_b, date(2026, 9, 1))
        record_manual_payment(
            invoice_a, Decimal("100000"), method=Payment.Method.CASH, user=self.teacher_user
        )
        record_manual_payment(
            invoice_b, Decimal("200000"), method=Payment.Method.CASH, user=self.teacher_user
        )
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get("/api/payments/payments/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["invoice"], invoice_a.pk)

    def test_filter_by_payment_method(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        record_manual_payment(
            invoice, Decimal("100000"), method=Payment.Method.CASH, user=self.teacher_user
        )
        record_manual_payment(
            invoice, Decimal("200000"), method=Payment.Method.BANK_TRANSFER, user=self.teacher_user
        )
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get("/api/payments/payments/?payment_method=cash")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["payment_method"], "cash")

    def test_search_by_student_name(self):
        invoice = generate_invoice(self.student_a, date(2026, 9, 1))
        record_manual_payment(
            invoice, Decimal("100000"), method=Payment.Method.CASH, user=self.teacher_user
        )
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get(f"/api/payments/payments/?search={self.student_a.person.full_name}")
        self.assertEqual(response.data["count"], 1)

    def test_meta_returns_method_and_matched_by_choices(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.get("/api/payments/payments/meta/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("payment_methods", response.data)
        self.assertIn("matched_by", response.data)
