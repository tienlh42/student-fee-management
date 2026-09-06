# Quản lý học sinh & học phí

App quản lý học sinh và thu phí cho một hộ kinh doanh. Django (API + serve static)
gộp chung với Vue 3 + PrimeVue thành **một đơn vị triển khai duy nhất**.

## Kiến trúc

| Quyết định | Lý do |
| --- | --- |
| Vue build ra static, Django serve qua `django-vite` | Cùng origin → dùng session auth mặc định của Django, không JWT, không CORS |
| PostgreSQL, không Redis/Celery | < 100 user; cache dùng `LocMemCache`, tác vụ định kỳ dùng cron gọi management command |
| Docker Compose 3 service (`db`, `web`, `caddy`) trên 1 VPS | Caddy tự lo SSL Let's Encrypt, không cần certbot |
| CI/CD build thẳng trên VPS qua SSH | Bỏ bước setup registry ở giai đoạn đầu |

### 6 Django app theo ranh giới nghiệp vụ

| App | Model | Trả lời câu hỏi |
| --- | --- | --- |
| `tenancy` | `House` | Cơ sở nào — hầu hết app khác FK về đây |
| `accounts` | `User` (custom), `UserOAuthAccount` | Ai đăng nhập |
| `people` | `Person`, `Student`, `Teacher`, `Guardian`, `StudentGuardian`, `TeachingAssignment` | Ai là ai |
| `billing` | `FeeItem`, `FeePackage`, `FeePackageItem`, `StudentFeePackage`, `StudentDiscount`, `Invoice`, `InvoiceItem`, `Refund` | **Học sinh nợ bao nhiêu** |
| `payments` | `BankAccount`, `BankIntegration`, `IncomingTransaction`, `Payment` | **Tiền về từ đâu, khớp vào hóa đơn nào** |
| `notifications` | `Notification`, `NotificationRead` | Thông báo tới giáo viên/phụ huynh |

`billing` và `payments` tách rời có chủ đích: billing đổi theo nghiệp vụ, payments đổi
theo API bên thứ ba (SePay). Gộp chung sẽ khiến một thay đổi nhỏ bên này lây sang bên kia.

**Quy ước mỗi app**: `models.py`, `services.py` (logic nghiệp vụ thuần, không chạm HTTP
request), `admin.py`, `urls.py`. View/API chỉ gọi vào `services.py` — nhờ vậy test được
logic mà không cần dựng request. Xem `billing/tests.py`, `payments/tests.py`.

### Phân quyền

Không có field `role`. Vai trò suy ra từ dữ liệu — xem `accounts/services.py:role_for`:

- **Teacher** → toàn quyền trong `house` của mình
- **Guardian** → chỉ đọc, giới hạn qua `StudentGuardian` (`people/services.py:accessible_students`)
- **Guardian không bao giờ** thấy `BankAccount` / `BankIntegration` / `IncomingTransaction`
  (dùng permission `accounts.permissions.CanSeeBankData`)

## Chạy dev

Cần Docker Desktop và Node 20+. **Không cần cài Python trên máy** — backend chạy trong container.

```bash
cp .env.example .env   # rồi sửa DJANGO_DEBUG=True, DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

Terminal 1 — backend + Postgres:

```bash
docker compose -f docker-compose.dev.yml up
```

Terminal 2 — Vite dev server (chạy trên host, có HMR):

```bash
cd frontend && npm install && npm run dev
```

Mở http://localhost:8000 — Django render `templates/index.html`, `django-vite` trỏ thẻ
`<script>` về Vite ở cổng 5173. Sửa file `.vue` thấy hot-reload ngay.

Tạo tài khoản quản trị:

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

Django admin ở http://localhost:8000/admin/ — đã đăng ký đầy đủ 6 app, đủ dùng để nhập
liệu và kiểm thử nghiệp vụ trước khi có màn hình Vue thật.

### Migrations & test

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py makemigrations
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
docker compose -f docker-compose.dev.yml exec web python manage.py test
```

### Sinh hóa đơn theo kỳ

Thay cho Celery beat — gọi bằng cron trên VPS:

```bash
docker compose exec -T web python manage.py generate_invoices --period 2026-09
docker compose exec -T web python manage.py generate_invoices --dry-run
```

Idempotent: mỗi cặp `(student, period)` chỉ có đúng một hóa đơn, chạy lại không tạo trùng.

## Đối soát tiền vào

`Invoice.qr_reference_code` (dạng `HPXXXXXXXX`, bỏ các ký tự dễ nhìn nhầm như `0/O`, `1/I`)
là chuỗi phụ huynh ghi trong nội dung chuyển khoản. Khi webhook SePay báo giao dịch:

1. Lưu `IncomingTransaction` (`provider_transaction_id` là unique → webhook gửi lại không ghi trùng)
2. Gọi `payments.services.try_auto_match` — rút mã khỏi nội dung chuyển khoản sau khi
   lược bỏ mọi ký tự không phải chữ/số, rồi phân bổ tiền vào hóa đơn theo hạn nộp
3. `billing.services.recalculate_status` cập nhật trạng thái hóa đơn

Thiếu tiền → hóa đơn `partially_paid`. Thừa tiền → phần dư nằm lại ở giao dịch
(`unallocated_amount`) chờ gán tay bằng `allocate_manually`.

Thu tiền mặt đi qua `record_cash_payment`, **bắt buộc** ghi người thu để truy trách nhiệm.

## Deploy

Trên VPS, lần đầu:

```bash
git clone <repo> /opt/student-fee-manager && cd /opt/student-fee-manager
cp .env.example .env && nano .env      # đặt SECRET_KEY, mật khẩu DB, DOMAIN thật
docker compose up -d
docker compose exec -T web python manage.py migrate
docker compose exec -T web python manage.py createsuperuser
```

Caddy tự xin chứng chỉ Let's Encrypt cho `$DOMAIN` và redirect HTTP → HTTPS.

Các lần sau: push lên `main`, GitHub Actions SSH vào VPS chạy
`git pull && docker compose build && up -d && migrate && collectstatic`.
Secrets cần tạo: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

> `collectstatic` chạy **sau** `up -d` là cố ý: `static_volume` chỉ được nạp từ image ở
> lần đầu (lúc volume còn rỗng). Từ lần deploy thứ hai trở đi, không chạy lại
> `collectstatic` thì asset mới sẽ không vào được volume và Caddy vẫn trả file cũ.

### Backup — bắt buộc

Đây là app quản lý tiền. Thêm cron trên host VPS:

```
15 2 * * * /opt/student-fee-manager/scripts/backup_db.sh >> /var/log/hocphi-backup.log 2>&1
```

## Việc còn lại

- [ ] `serializers.py` + `urls.py` cho từng app (hiện `urlpatterns = []`)
- [ ] Endpoint webhook SePay + xác thực `webhook_secret`
- [ ] Sinh ảnh VietQR — `payments/services.py:build_vietqr_url` đang trả `None`:
      VietQR cần **số tài khoản đầy đủ**, mà `BankAccount` cố tình chỉ lưu 4 số cuối.
      Cần chốt nơi lưu số đầy đủ (biến môi trường, hay field mã hóa riêng) trước khi làm.
- [ ] Mã hóa thật cho `api_key_encrypted` / `access_token_encrypted` — hiện chỉ là
      `TextField`, tên field mô tả ý định chứ chưa có cơ chế mã hóa
- [ ] Thay các màn hình placeholder trong `frontend/src/views/` bằng PrimeVue DataTable
- [ ] Màn hình đăng nhập + `LoginRequiredMiddleware` hoặc guard ở `router`
