from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from billing.models import FeeItem, FeePackage, FeePackageItem, Invoice, StudentFeePackage
from billing.services import generate_invoice
from people.models import Person, Student
from tenancy.models import House

from .models import IncomingTransaction, Payment
from .services import extract_reference_codes, record_cash_payment, try_auto_match


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
            record_cash_payment(self.invoice, Decimal("100000"), user=None)
