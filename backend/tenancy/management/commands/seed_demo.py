"""Dựng bộ dữ liệu mẫu để chạy thử và demo.

    docker compose -f docker-compose.dev.yml exec web python manage.py seed_demo
    docker compose -f docker-compose.dev.yml exec web python manage.py seed_demo --students 30 --invoices
    docker compose -f docker-compose.dev.yml exec web python manage.py seed_demo --reset

Idempotent như `generate_invoices`: chạy lại không nhân đôi dữ liệu. Tên người
được lấy theo thứ tự cố định từ một danh sách có sẵn, nên lần chạy thứ hai
`get_or_create` khớp đúng bản ghi cũ.

Đây là app quản lý tiền — lệnh **từ chối chạy khi `DEBUG=False`** trừ khi có
`--force`, và `--reset` thì không bao giờ chạy ngoài DEBUG.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from billing.models import (
    FeeItem,
    FeePackage,
    FeePackageItem,
    Invoice,
    InvoiceItem,
    StudentDiscount,
    StudentFeePackage,
)
from billing.services import generate_invoice, period_start
from payments.models import BankAccount, Payment
from people.models import Guardian, Person, Student, StudentGuardian, Teacher
from people.services import link_guardian
from tenancy.models import House

User = get_user_model()

HOUSE_SLUG = "co-so-chinh"
DEFAULT_PASSWORD = "hocphi123!"

TEACHERS = [
    ("colan", "Nguyễn Thị Lan"),
    ("thaynam", "Trần Hoài Nam"),
]

# Cặp (họ tên học sinh, họ tên phụ huynh, quan hệ) — cố định để chạy lại khớp bản cũ.
FAMILIES = [
    ("Nguyễn Minh An", "Nguyễn Thị Hoa", "mother"),
    ("Trần Bảo Châu", "Trần Văn Dũng", "father"),
    ("Lê Gia Huy", "Lê Thị Mai", "mother"),
    ("Phạm Khánh Linh", "Phạm Quốc Toản", "father"),
    ("Hoàng Đức Anh", "Hoàng Thị Nga", "mother"),
    ("Vũ Thảo Nguyên", "Vũ Đình Phúc", "father"),
    ("Đặng Tuấn Kiệt", "Đặng Thị Bích", "mother"),
    ("Bùi Ngọc Diệp", "Bùi Văn Sơn", "father"),
    ("Đỗ Hải Đăng", "Đỗ Thị Thu", "mother"),
    ("Ngô Phương Vy", "Ngô Minh Tuấn", "father"),
    ("Dương Quang Minh", "Dương Thị Hằng", "mother"),
    ("Lý Bảo Ngọc", "Lý Văn Thành", "father"),
    ("Trịnh Gia Bảo", "Trịnh Thị Yến", "mother"),
    ("Cao Thùy Dương", "Cao Xuân Hòa", "father"),
    ("Mai Anh Khoa", "Mai Thị Lệ", "mother"),
    ("Phan Hà My", "Phan Trọng Nghĩa", "father"),
    ("Võ Nhật Nam", "Võ Thị Kim", "mother"),
    ("Chu Diệu Linh", "Chu Văn Bình", "father"),
    ("Tạ Đình Long", "Tạ Thị Vân", "mother"),
    ("Hồ Khánh Vân", "Hồ Sỹ Cường", "father"),
    ("Đinh Tiến Dũng", "Đinh Thị Loan", "mother"),
    ("Lương Thanh Trúc", "Lương Văn Kiên", "father"),
    ("Đào Minh Quân", "Đào Thị Hạnh", "mother"),
    ("Tô Yến Nhi", "Tô Hữu Đạt", "father"),
    ("Hà Bảo Lâm", "Hà Thị Xuân", "mother"),
    ("Kiều Thu Trang", "Kiều Văn Lộc", "father"),
    ("Lâm Gia Hân", "Lâm Thị Tuyết", "mother"),
    ("Tăng Quốc Việt", "Tăng Văn Hải", "father"),
    ("Ưng Mỹ Duyên", "Ưng Thị Nhàn", "mother"),
    ("Quách Đình Phong", "Quách Văn Tâm", "father"),
]

CLASS_GRADES = ["1A", "1B", "2A", "2B", "3A"]

# Đa số đang học; xen vài trạng thái khác để lọc trên UI có gì mà lọc.
STATUS_CYCLE = (
    [Student.Status.ACTIVE] * 8 + [Student.Status.PAUSED] + [Student.Status.WITHDRAWN]
)

FEE_ITEMS = [
    ("Học phí", FeeItem.Category.TUITION, Decimal("3000000")),
    ("Tiền ăn", FeeItem.Category.MEAL, Decimal("900000")),
    ("Phí xe đưa đón", FeeItem.Category.TRANSPORT, Decimal("600000")),
    ("Đồng phục", FeeItem.Category.OTHER, Decimal("450000")),
]

# Model bị xóa theo đúng thứ tự này khi --reset: con trước, cha sau. Đảo thứ tự
# sẽ vướng on_delete=PROTECT của Invoice.house / Student.house.
RESET_ORDER = [
    Payment,
    InvoiceItem,
    Invoice,
    StudentDiscount,
    StudentFeePackage,
    FeePackageItem,
    FeePackage,
    FeeItem,
    StudentGuardian,
    BankAccount,
]


class Command(BaseCommand):
    help = "Tạo cơ sở, giáo viên, học sinh, phụ huynh và biểu phí mẫu để chạy thử."

    def add_arguments(self, parser):
        parser.add_argument(
            "--students",
            type=int,
            default=12,
            help=f"Số học sinh cần tạo (tối đa {len(FAMILIES)}). Mặc định: 12.",
        )
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Mật khẩu cho các tài khoản mẫu. Mặc định: {DEFAULT_PASSWORD}",
        )
        parser.add_argument(
            "--invoices",
            action="store_true",
            help="Sinh luôn hóa đơn kỳ hiện tại cho học sinh đang học.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="XÓA toàn bộ dữ liệu của cơ sở mẫu trước khi tạo lại. Chỉ chạy khi DEBUG=True.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Cho phép chạy khi DEBUG=False. Không mở khóa được --reset.",
        )

    def handle(self, *args, **options):
        count = options["students"]
        if not 1 <= count <= len(FAMILIES):
            raise CommandError(f"--students phải trong khoảng 1..{len(FAMILIES)}.")

        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "DEBUG=False — đây là dữ liệu giả, không nên đổ vào DB thật. "
                "Chắc chắn thì thêm --force."
            )

        if options["reset"]:
            if not settings.DEBUG:
                raise CommandError("--reset chỉ chạy khi DEBUG=True. Không có cách ghi đè.")
            self._reset()

        with transaction.atomic():
            house = self._house()
            self._bank_account(house)
            teachers = self._teachers(house, options["password"])
            package = self._fee_package(house)
            students = self._families(house, package, count, options["password"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Cơ sở «{house.name}»: {len(teachers)} giáo viên, {len(students)} học sinh."
            )
        )

        if options["invoices"]:
            self._invoices(house)

        self._print_credentials(options["password"])

    # --- xóa ------------------------------------------------------------

    def _reset(self):
        house = House.objects.filter(inbound_email_slug=HOUSE_SLUG).first()
        if house is None:
            self.stdout.write("Chưa có cơ sở mẫu — bỏ qua --reset.")
            return

        self.stdout.write(self.style.WARNING(f"Xóa dữ liệu của «{house.name}»:"))
        with transaction.atomic():
            student_ids = list(house.students.values_list("person_id", flat=True))

            for model in RESET_ORDER:
                deleted, _ = self._reset_queryset(model, house, student_ids).delete()
                if deleted:
                    self.stdout.write(f"  - {model.__name__}: {deleted}")

            # Person của học sinh/giáo viên/phụ huynh xóa theo cascade từ vai trò,
            # nên xóa vai trò trước rồi mới dọn Person mồ côi.
            #
            # Student/Teacher/Guardian có soft delete (xem core.models) — .objects
            # ẩn bản ghi đã xóa nên không tái sử dụng được person_id của nó.
            # --reset là dọn sạch dữ liệu demo thật sự, phải xóa cứng qua
            # all_objects, không thì lần seed lại sẽ đụng unique constraint.
            person_ids = student_ids + list(
                Teacher.objects.filter(house=house).values_list("person_id", flat=True)
            )
            Student.all_objects.filter(person_id__in=student_ids).delete()
            Teacher.all_objects.filter(house=house).delete()
            Guardian.all_objects.filter(student_links__isnull=True).delete()

            User.objects.filter(person_id__in=person_ids).delete()
            Person.objects.filter(id__in=person_ids).delete()
            Person.objects.filter(
                student__isnull=True, teacher__isnull=True, guardian__isnull=True, user__isnull=True
            ).delete()
            house.delete()

        self.stdout.write(self.style.WARNING("Đã xóa xong.\n"))

    @staticmethod
    def _reset_queryset(model, house: House, student_ids: list[int]):
        """Mỗi model neo về house theo một đường khác nhau."""
        if model is Payment:
            return model.objects.filter(invoice__house=house)
        if model is InvoiceItem:
            return model.objects.filter(invoice__house=house)
        if model in (StudentDiscount, StudentFeePackage, StudentGuardian):
            return model.objects.filter(student_id__in=student_ids)
        if model is FeePackageItem:
            return model.objects.filter(fee_package__house=house)
        return model.objects.filter(house=house)

    # --- tạo ------------------------------------------------------------

    def _house(self) -> House:
        house, created = House.objects.get_or_create(
            inbound_email_slug=HOUSE_SLUG,
            defaults={"name": "Cơ sở chính", "address": "12 Nguyễn Trãi, Thanh Xuân, Hà Nội"},
        )
        self.stdout.write(f"{'Tạo' if created else 'Dùng lại'} cơ sở: {house.name}")
        return house

    def _bank_account(self, house: House) -> BankAccount:
        account, _ = BankAccount.objects.get_or_create(
            house=house,
            defaults={
                "bank_code": "970436",  # Vietcombank
                "account_number_last4": "8899",
                "account_holder_name": "NGUYEN THI LAN",
            },
        )
        return account

    def _teachers(self, house: House, password: str) -> list[Teacher]:
        created = []
        for username, full_name in TEACHERS:
            person, _ = Person.objects.get_or_create(
                full_name=full_name,
                defaults={"phone": self._phone(len(created)), "gender": Person.Gender.FEMALE},
            )
            teacher, _ = Teacher.objects.get_or_create(person=person, defaults={"house": house})

            user, is_new = User.objects.get_or_create(
                username=username, defaults={"person": person}
            )
            # Chỉ gắn khi user chưa liên kết ai. User đã trỏ vào Person khác là
            # dữ liệu thật của ai đó — lệnh seed không được cướp liên kết đó.
            if user.person_id is None:
                user.person = person
            if is_new:
                user.set_password(password)
            user.save()

            created.append(teacher)
        return created

    def _fee_package(self, house: House) -> FeePackage:
        items = [
            FeeItem.objects.get_or_create(
                house=house, name=name, defaults={"category": category, "default_amount": amount}
            )[0]
            for name, category, amount in FEE_ITEMS
        ]

        package, _ = FeePackage.objects.get_or_create(
            house=house,
            name="Gói chuẩn cả ngày",
            defaults={
                "description": "Học phí + tiền ăn + xe đưa đón.",
                "due_day_of_month": 5,
            },
        )
        # Đồng phục là khoản thu lẻ, không nằm trong gói định kỳ.
        for item in items[:3]:
            FeePackageItem.objects.get_or_create(fee_package=package, fee_item=item)
        return package

    def _families(
        self, house: House, package: FeePackage, count: int, password: str
    ) -> list[Student]:
        students = []
        enrolled = date.today().replace(day=1) - timedelta(days=365)

        for index, (student_name, guardian_name, relationship) in enumerate(FAMILIES[:count]):
            person, _ = Person.objects.get_or_create(
                full_name=student_name,
                defaults={
                    "date_of_birth": date(2018, (index % 12) + 1, (index % 28) + 1),
                    "gender": Person.Gender.MALE if index % 2 else Person.Gender.FEMALE,
                    "current_address": "Hà Nội",
                },
            )
            student, _ = Student.objects.get_or_create(
                person=person,
                defaults={
                    "house": house,
                    "class_grade": CLASS_GRADES[index % len(CLASS_GRADES)],
                    "status": STATUS_CYCLE[index % len(STATUS_CYCLE)],
                    "enrolled_date": enrolled,
                },
            )

            guardian_person, _ = Person.objects.get_or_create(
                full_name=guardian_name,
                defaults={"phone": self._phone(index + 100), "current_address": "Hà Nội"},
            )
            guardian, _ = Guardian.objects.get_or_create(
                person=guardian_person, defaults={"occupation": "Tự do"}
            )
            link_guardian(
                student,
                guardian=guardian,
                relationship_type=relationship,
                is_primary_contact=True,
            )

            StudentFeePackage.objects.get_or_create(
                student=student,
                fee_package=package,
                defaults={"effective_from": enrolled},
            )
            students.append(student)

        # Một phụ huynh có tài khoản đăng nhập — để thử vai trò chỉ đọc.
        first_guardian = Guardian.objects.get(person__full_name=FAMILIES[0][1])
        user, is_new = User.objects.get_or_create(
            username="phuhuynh", defaults={"person": first_guardian.person}
        )
        if user.person_id is None:
            user.person = first_guardian.person
        if is_new:
            user.set_password(password)
        user.save()

        # Một suất học bổng, để màn hình hóa đơn có dòng giảm trừ mà nhìn.
        StudentDiscount.objects.get_or_create(
            student=students[0],
            name="Học bổng khuyến học 10%",
            defaults={
                "discount_type": StudentDiscount.DiscountType.PERCENTAGE,
                "value": Decimal("10"),
                "effective_from": enrolled,
            },
        )
        return students

    def _invoices(self, house: House):
        period = period_start(date.today())
        students = house.students.filter(status=Student.Status.ACTIVE)
        for student in students:
            generate_invoice(student, period)

        total = Invoice.objects.filter(house=house, period=period).count()
        self.stdout.write(
            self.style.SUCCESS(f"Hóa đơn kỳ {period:%m/%Y}: {total} bản ghi.")
        )

    # --- phụ trợ --------------------------------------------------------

    @staticmethod
    def _phone(index: int) -> str:
        return f"09{index:08d}"

    def _print_credentials(self, password: str):
        self.stdout.write("\nTài khoản đăng nhập:")
        for username, full_name in TEACHERS:
            self.stdout.write(f"  {username:<10} / {password}   (giáo viên — {full_name})")
        self.stdout.write(f"  {'phuhuynh':<10} / {password}   (phụ huynh — chỉ đọc)")
        self.stdout.write(
            self.style.WARNING(
                "\nMật khẩu chỉ đặt cho tài khoản MỚI tạo — tài khoản đã có giữ nguyên "
                "mật khẩu cũ. Đổi bằng: manage.py changepassword <username>"
            )
        )
