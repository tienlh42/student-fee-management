from datetime import date
from decimal import Decimal

from django.test import TestCase

from people.models import Person, Student
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
