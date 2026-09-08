# Roadmap tính năng — triển khai sau khi hoàn thành "thu học phí"

> Tổng hợp từ: (1) phân tích khoảng trống quản lý phí, (2) so sánh MISA EMIS Kindergarten,
> (3) so sánh MISA AMIS Kế toán, (4) so sánh phần mềm tutor quốc tế (TutorBird, Teachworks,
> TutorCruncher). Phạm vi hiện tại (đang làm) chỉ dừng ở "thu học phí" — mọi mục dưới đây
> là MỞ RỘNG, chưa cần làm ngay.

## Phase 2 — Vận hành thu phí nâng cao

Mở rộng trực tiếp trên `billing`/`notifications` đã có, không cần entity mới lớn.

- [ ] **Xử lý nhập học/nghỉ học giữa tháng** — quy tắc tính hóa đơn tháng đó: đủ tháng hay
      theo tỷ lệ ngày còn lại (`StudentFeePackage.effective_from/until` đã có, cần logic tính)
- [ ] **Nhắc phí tự động theo lịch** — cron kiểm tra `due_date` mỗi ngày: nhắc trước hạn vài
      ngày, đúng hạn, sau khi quá hạn (dùng lại `Notification`)
- [ ] **Dashboard công nợ tổng hợp** — ai đang nợ, nợ bao nhiêu, nợ bao lâu, sắp đến hạn
- [ ] **Nhập liệu hàng loạt qua Excel** — import danh sách học sinh + gán gói phí lúc onboard
      house mới (dùng `xlsx` skill sẵn có)
- [ ] **Xuất hóa đơn/biên lai PDF** — để phụ huynh lưu hoặc giáo viên in (dùng `pdf` skill)
- [ ] **Công nợ gộp theo guardian** — 1 phụ huynh nhiều con, xem tổng nợ + thanh toán gộp
      (model đã hỗ trợ qua `Payment` nhiều-nhiều, chỉ thiếu UI/API tổng hợp)
- [ ] **Báo cáo doanh thu** — theo tháng, theo `FeeItem`
- [ ] **Trang đăng ký công khai (self-signup)** — phụ huynh mới tự điền form đăng ký học,
      giảm việc giáo viên nhập tay (ý tưởng từ TutorBird website builder)
- [ ] Phí phạt trễ hạn tự động cộng dồn
- [ ] Bảo lưu chỗ (tạm nghỉ, không tính phí, không mất chỗ khi quay lại)
- [ ] Đổi gói phí giữa tháng (quy tắc tính lại công bằng)

## Phase 3 — Vận hành giảng dạy (entity mới: lịch học)

Đây là mảng lớn nhất còn thiếu — cả MISA EMIS lẫn TutorBird/Teachworks/TutorCruncher đều
coi lịch học ngang hàng với billing, không phải phụ. Cần entity mới (`Lesson`/`ClassSession`)
chưa có trong entity diagram hiện tại.

- [ ] **Lịch học/đặt lịch theo buổi** — buổi học cụ thể (ngày giờ, giáo viên, học sinh/nhóm),
      không chỉ `TeachingAssignment` (ai phụ trách ai) như hiện tại
- [ ] **Điểm danh (attendance)** — cơ bản (giáo viên tick có mặt/vắng), chưa cần nhận diện
      khuôn mặt như MISA EMIS
- [ ] **Ghi chú/nhận xét tiến độ học tập** — gửi phụ huynh qua `Notification` đã có, nhưng
      nên tách thành entity riêng (`ProgressNote`) để xem lại lịch sử theo thời gian, không
      lẫn với thông báo hành chính
- [ ] Cổng phụ huynh mở rộng: xem lịch học, xem bài tập/ghi chú (không chỉ xem hóa đơn)

## Phase 4 — Quản lý chi phí & lương giáo viên (chiều CHI — hiện chưa có)

App hiện tại chỉ quản lý chiều THU (từ phụ huynh). TutorCruncher coi trả lương tutor là
tính năng lõi ngang hàng với thu tiền — đáng cân nhắc nếu house có giáo viên dạy thay
hưởng lương/thù lao.

- [ ] **Công nợ phải trả** — lương/thù lao giáo viên dạy thay chưa trả
- [ ] **Trả lương tự động theo giờ dạy** — phụ thuộc Phase 3 (cần dữ liệu buổi học thực tế)
- [ ] **Chi phí hoạt động khác** — điện nước, học liệu — ghi chép đơn giản, chưa cần phân bổ
      chi phí phức tạp

## Phase 5 — Báo cáo & kế toán mở rộng (chỉ nếu thực sự cần)

- [ ] Báo cáo tài chính tổng hợp (Thu − Chi = Lợi nhuận) — cần Phase 4 xong trước
- [ ] Quản lý tài sản cố định (bàn ghế, máy chiếu...) — chỉ đáng làm nếu house có tài sản
      giá trị lớn cần theo dõi khấu hao
- [ ] Cân nhắc export dữ liệu sang phần mềm kế toán chuyên dụng (MISA...) — chỉ cần nếu
      sau này house phải đăng ký hộ kinh doanh/doanh nghiệp, phát sinh nghĩa vụ kế toán/thuế
      chính thức (nên hỏi kế toán/luật sư thật khi tới lúc, ngoài phạm vi kỹ thuật)

## Quyết định còn treo (mang theo từ giai đoạn thiết kế entity)

- [ ] `FeeItem.category` — giữ hay bỏ
- [ ] `Invoice` có cần thêm state `refunded` riêng, hay giữ `cancelled` + bản ghi `Refund` làm
      bằng chứng
- [ ] Thứ tự áp `StudentDiscount` khi sinh hóa đơn — trừ từng `InvoiceItem` hay trừ 1 lần vào
      `total_amount` cuối
- [ ] Chiến lược khi ngân hàng của 1 house không rõ có hỗ trợ cá nhân qua SePay API — mặc
      định SMS hay để giáo viên tự chọn lúc setup

## Ngoài phạm vi (không đưa vào roadmap này)

- Điểm danh bằng nhận diện khuôn mặt, trích xuất ảnh tự động (tính năng AI của MISA EMIS) —
  vượt quá nhu cầu thực tế của quy mô <100 user
- Đa ngôn ngữ/đa quốc gia (OpenEduCat, Teachworks 45 ngôn ngữ) — không cần thiết, chỉ phục
  vụ 1 thị trường VN
