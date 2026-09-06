"""Sinh hóa đơn cho một kỳ. Chạy bằng cron thay cho Celery beat.

    docker compose exec -T web python manage.py generate_invoices --period 2026-09
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from billing.services import generate_invoice
from people.models import Student


class Command(BaseCommand):
    help = "Sinh hóa đơn nháp cho toàn bộ học sinh đang học trong một kỳ."

    def add_arguments(self, parser):
        parser.add_argument(
            "--period",
            help="Kỳ dạng YYYY-MM. Mặc định: tháng hiện tại.",
        )
        parser.add_argument(
            "--house",
            type=int,
            help="Chỉ sinh cho một cơ sở (house id).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ in ra sẽ tạo cho ai, không ghi DB.",
        )

    def handle(self, *args, **options):
        period = self._parse_period(options.get("period"))

        students = Student.objects.filter(status=Student.Status.ACTIVE).select_related("house")
        if options.get("house"):
            students = students.filter(house_id=options["house"])

        created = skipped = 0
        for student in students:
            if options["dry_run"]:
                self.stdout.write(f"[dry-run] {student} — kỳ {period:%m/%Y}")
                continue

            invoice = generate_invoice(student, period)
            if invoice.created_at.date() == date.today():
                created += 1
            else:
                skipped += 1

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry-run: {students.count()} học sinh."))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Kỳ {period:%m/%Y}: tạo mới {created}, đã có sẵn {skipped}.")
        )

    @staticmethod
    def _parse_period(raw: str | None) -> date:
        if not raw:
            today = date.today()
            return today.replace(day=1)
        try:
            year, month = raw.split("-")
            return date(int(year), int(month), 1)
        except (ValueError, TypeError) as exc:
            raise CommandError("--period phải có dạng YYYY-MM, ví dụ 2026-09.") from exc
