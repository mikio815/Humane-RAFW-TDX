import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec


MOCK_QUOTE_BODY_SIZE = 1024
MOCK_SIGNATURE_LEN_SIZE = 2
MOCK_QV_RESULT_OK = 0x00000000
MOCK_QV_RESULT_INVALID_SIGNATURE = 0x0000A004
MOCK_SUPPLEMENTAL_DATA_SIZE = 1024

MOCK_REPORT_BASE = 48
MOCK_QUOTE_VERSION = 4
MOCK_TEE_TYPE_TDX = 0x81

MOCK_MR_SEAM = bytes.fromhex("11" * 48)
MOCK_MRSIGNER_SEAM = bytes.fromhex("22" * 48)
MOCK_MR_TD = bytes.fromhex("33" * 48)
MOCK_RTMR0 = bytes.fromhex("44" * 48)
MOCK_RTMR1 = bytes.fromhex("55" * 48)
MOCK_RTMR2 = bytes.fromhex("66" * 48)
MOCK_RTMR3 = bytes.fromhex("77" * 48)

_MOCK_PRIVATE_VALUE = int(
    "123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
    16,
)


def mock_tdx_enabled() -> bool:
    return os.environ.get("MOCK_TDX", "").lower() in {"1", "true", "yes", "on"}


def _mock_private_key():
    return ec.derive_private_key(_MOCK_PRIVATE_VALUE, ec.SECP256R1())


def _mock_public_key():
    return _mock_private_key().public_key()


def build_mock_quote(report_data: bytes) -> bytes:
    if len(report_data) != 64:
        raise ValueError("report_data must be 64 bytes")

    body = bytearray(MOCK_QUOTE_BODY_SIZE)
    body[0:2] = MOCK_QUOTE_VERSION.to_bytes(2, "little")
    body[4:8] = MOCK_TEE_TYPE_TDX.to_bytes(4, "little")

    base = MOCK_REPORT_BASE
    body[base + 16 : base + 16 + 48] = MOCK_MR_SEAM
    body[base + 64 : base + 64 + 48] = MOCK_MRSIGNER_SEAM
    body[base + 136 : base + 136 + 48] = MOCK_MR_TD
    body[base + 328 : base + 328 + 48] = MOCK_RTMR0
    body[base + 328 + 48 : base + 328 + 48 * 2] = MOCK_RTMR1
    body[base + 328 + 48 * 2 : base + 328 + 48 * 3] = MOCK_RTMR2
    body[base + 328 + 48 * 3 : base + 328 + 48 * 4] = MOCK_RTMR3
    body[base + 520 : base + 520 + 64] = report_data

    body_bytes = bytes(body)
    signature = _mock_private_key().sign(body_bytes, ec.ECDSA(hashes.SHA256()))
    return body_bytes + len(signature).to_bytes(MOCK_SIGNATURE_LEN_SIZE, "little") + signature


def verify_mock_quote_signature(quote: bytes) -> bool:
    if len(quote) < MOCK_QUOTE_BODY_SIZE + MOCK_SIGNATURE_LEN_SIZE:
        return False

    body = quote[:MOCK_QUOTE_BODY_SIZE]
    sig_len_start = MOCK_QUOTE_BODY_SIZE
    sig_len_end = sig_len_start + MOCK_SIGNATURE_LEN_SIZE
    sig_len = int.from_bytes(quote[sig_len_start:sig_len_end], "little")
    sig_start = sig_len_end
    sig_end = sig_start + sig_len

    if sig_len <= 0 or len(quote) != sig_end:
        return False

    signature = quote[sig_start:sig_end]

    try:
        _mock_public_key().verify(signature, body, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def build_mock_supplemental_data() -> bytes:
    return b"\x00" * MOCK_SUPPLEMENTAL_DATA_SIZE
