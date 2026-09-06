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

### Kết nối DB bằng GUI (DBeaver / extension PostgreSQL của VS Code)

`docker-compose.dev.yml` expose cổng 5432 ra host, nên client kết nối thẳng:

| Trường | Giá trị |
| --- | --- |
| Host | `localhost` |
| Port | `5432` |
| Database | `hocphi` |
| User | `hocphi_user` |
| Password | `changeme` (theo `.env`) |

`docker-compose.yml` (prod) **cố tình không** expose 5432 — trên VPS chỉ vào DB qua
`docker compose exec db psql -U hocphi_user hocphi`, không mở cổng ra internet.

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

## Đăng nhập & phân quyền trên API

Session auth cùng origin — không JWT, không lưu token ở `localStorage`.

| Endpoint | Việc |
| --- | --- |
| `POST /api/accounts/login/` | Đăng nhập, trả về user + `role` |
| `POST /api/accounts/logout/` | Đăng xuất |
| `GET /api/accounts/me/` | Trạng thái đăng nhập; **đồng thời set cookie `csrftoken`** |
| `POST /api/accounts/change-password/` | Đổi mật khẩu |

`GET /api/accounts/me/` trả `200 {"authenticated": false}` khi chưa đăng nhập chứ không
trả 401 — router guard chỉ cần biết trạng thái, 401 sẽ làm console đầy lỗi giả.

**Hai chỗ dễ sai về CSRF**, đã có test chốt trong `people/tests.py`:

1. DRF bọc `csrf_exempt` quanh mọi `APIView`, còn `SessionAuthentication` chỉ kiểm CSRF
   với request **đã** đăng nhập. Login là request chưa đăng nhập → phải tự gắn
   `@csrf_protect`, nếu không endpoint hở CSRF.
2. `django_login()` gọi `rotate_token()` → token cũ hết hiệu lực ngay sau khi đăng nhập.
   Client phải đọc lại cookie cho mỗi request ghi (`frontend/src/api/client.js` đã làm vậy).

### Ba lớp chặn quyền, không lớp nào thay được lớp nào

| Lớp | Ở đâu | Chặn gì |
| --- | --- | --- |
| Xác thực | `IsAuthenticated` | Khách vãng lai |
| Động từ | `accounts.permissions.IsTeacherOrReadOnly` | Guardian ghi dữ liệu |
| Cơ sở | `people.permissions.WritableWithinOwnHouse` | Teacher cơ sở A sửa bản ghi cơ sở B |
| Dòng dữ liệu | `people.services.accessible_students` (queryset) | Đọc bản ghi ngoài phạm vi |

> Khai báo `permission_classes` ở view **thay thế** `DEFAULT_PERMISSION_CLASSES` chứ không
> cộng dồn. Bỏ quên `IsAuthenticated` trong danh sách là khách vãng lai GET được — đúng
> lỗi này đã xảy ra một lần, nay có `test_anonymous_is_rejected` giữ.

Guard ở `frontend/src/router/index.js` chỉ để tránh chớp màn hình sai — **quyền thật luôn
do backend quyết định**. Ẩn nút trên UI không phải là bảo mật.

## API app `people`

`DefaultRouter` ở `people/urls.py`, tất cả dưới `/api/people/`:

| Route | Ghi chú |
| --- | --- |
| `students/` | CRUD; `?search=`, `?status=`, `?class_grade=`, `?house=`, `?page_size=` |
| `students/meta/` | Toàn bộ dropdown cho form + filter trong **một** request |
| `students/{id}/guardians/` | `GET` liệt kê, `POST` gắn (idempotent) |
| `students/{id}/guardians/{guardian_id}/` | `DELETE` gỡ liên kết |
| `guardians/`, `teachers/`, `assignments/` | CRUD |

`Student`/`Teacher`/`Guardian` đều lấy `person_id` làm khóa chính, nên `person` luôn là
object **lồng và ghi được** — không thể tạo vai trò trước khi có `Person`. Serializer
phơi `person_id` ra dưới tên `id` để frontend dùng làm `data-key` cho DataTable.

Sửa học sinh của cơ sở khác trả **404 chứ không phải 403**: bản ghi nằm ngoài queryset đã
lọc, trả 403 sẽ tiết lộ rằng nó tồn tại.

## Frontend

| File | Việc |
| --- | --- |
| `stores/auth.js` | User + role, `ensureResolved()` cho router guard |
| `api/client.js` | `fetch` + CSRF, `errorMessage()` / `fieldErrors()` gom lỗi DRF |
| `api/people.js` | Bọc endpoint, view không tự ghép query string |
| `views/LoginView.vue` | Form đăng nhập, hỗ trợ `?redirect=` |
| `views/StudentsView.vue` | DataTable lazy + filter + phân trang server-side |
| `components/StudentFormDialog.vue` | Form thêm/sửa, `person` lồng |
| `components/StudentGuardiansDialog.vue` | Gắn/gỡ phụ huynh, tạo nhanh phụ huynh mới |
| `utils/date.js` | `Date` ↔ `"YYYY-MM-DD"` |

> `utils/date.js` **không** dùng `toISOString()`: hàm đó quy về UTC nên ở múi giờ +07 sẽ
> lùi ngày sinh đi một ngày.

## Việc còn lại

- [x] Đăng nhập/đăng xuất + guard ở `router`
- [x] `serializers.py` + `urls.py` cho app `people`, màn hình Học sinh
- [ ] `serializers.py` + `urls.py` cho `billing`, `payments`, `notifications`
      (hiện `urlpatterns = []`)
- [ ] Endpoint webhook SePay + xác thực `webhook_secret`
- [ ] Sinh ảnh VietQR — `payments/services.py:build_vietqr_url` đang trả `None`:
      VietQR cần **số tài khoản đầy đủ**, mà `BankAccount` cố tình chỉ lưu 4 số cuối.
      Cần chốt nơi lưu số đầy đủ (biến môi trường, hay field mã hóa riêng) trước khi làm.
- [ ] Mã hóa thật cho `api_key_encrypted` / `access_token_encrypted` — hiện chỉ là
      `TextField`, tên field mô tả ý định chứ chưa có cơ chế mã hóa
- [ ] Thay 3 màn hình placeholder còn lại (Hóa đơn, Đối soát, Thông báo)
- [ ] Màn hình đổi mật khẩu (API `change-password/` đã có, UI chưa)
