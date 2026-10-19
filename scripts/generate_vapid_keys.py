"""웹 푸시용 VAPID 키 한 쌍을 만든다. 실행: uv run python -m scripts.generate_vapid_keys

출력한 두 줄을 .env에 넣는다. 개인 키는 비밀로 두고, 바꾸면 기존 구독은 모두 다시 받아야 한다.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate() -> tuple[str, str]:
    """(공개 키: 압축하지 않은 점, 개인 키: 32바이트 값) — 둘 다 base64url."""
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    private = key.private_numbers().private_value.to_bytes(32, "big")
    return _b64url(public), _b64url(private)


if __name__ == "__main__":
    public_key, private_key = generate()
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
