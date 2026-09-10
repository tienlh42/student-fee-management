"""Danh sách ngân hàng dùng cho VietQR.

Lấy từ API công khai của VietQR (`https://api.vietqr.io/v2/banks`, lấy ngày
2026-09-10), chỉ giữ ngân hàng có `transferSupported=1`. Giá trị lưu là mã BIN
(chuẩn Napas) — bắt buộc phải dùng BIN thật, không tự đặt mã, vì BIN sai sẽ
khiến QR trỏ sai/không tồn tại ngân hàng.
"""

NAPAS_BANKS = [
    ("970425", "ABBANK"),
    ("970416", "ACB"),
    ("970405", "Agribank"),
    ("970409", "BacABank"),
    ("970438", "BaoVietBank"),
    ("970418", "BIDV"),
    ("546034", "CAKE"),
    ("422589", "CIMB"),
    ("970446", "COOPBANK"),
    ("970431", "Eximbank"),
    ("970437", "HDBank"),
    ("668888", "KBank"),
    ("970452", "KienLongBank"),
    ("970449", "LPBank"),
    ("970422", "MBBank"),
    ("970414", "MBV"),
    ("971025", "MoMo"),
    ("970426", "MSB"),
    ("970428", "NamABank"),
    ("970419", "NCB"),
    ("970448", "OCB"),
    ("970430", "PGBank"),
    ("970412", "PVcomBank"),
    ("971133", "PVcomBank Pay"),
    ("970403", "Sacombank"),
    ("970400", "SaigonBank"),
    ("970429", "SCB"),
    ("970440", "SeABank"),
    ("970443", "SHB"),
    ("970424", "ShinhanBank"),
    ("970407", "Techcombank"),
    ("963388", "Timo"),
    ("970423", "TPBank"),
    ("546035", "Ubank"),
    ("970441", "VIB"),
    ("970427", "VietABank"),
    ("970433", "VietBank"),
    ("970454", "VietCapitalBank"),
    ("970436", "Vietcombank"),
    ("970415", "VietinBank"),
    ("970432", "VPBank"),
    ("970457", "Woori"),
]
