"""Mã hoá số tài khoản ngân hàng tại chỗ.

Dùng Fernet (đối xứng) thay vì chỉ lưu last4 như trước — VietQR cần số tài
khoản đầy đủ. Key lấy từ env, không hardcode, không lưu trong DB.
"""

from cryptography.fernet import Fernet, InvalidToken
from decouple import config as env


def _fernet() -> Fernet:
    key = env("BANK_ACCOUNT_ENCRYPTION_KEY")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_account_number(raw: str) -> str:
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_account_number(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Không giải mã được số tài khoản — sai key hoặc dữ liệu hỏng.") from exc
