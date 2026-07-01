from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from mock_tdx_common import MOCK_SIGNATURE_LEN_SIZE, build_mock_quote_body


_MOCK_PRIVATE_VALUE = int(
    "123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
    16,
)


def _mock_private_key():
    return ec.derive_private_key(_MOCK_PRIVATE_VALUE, ec.SECP256R1())


def build_mock_quote(report_data: bytes) -> bytes:
    body = build_mock_quote_body(report_data)
    signature = _mock_private_key().sign(body, ec.ECDSA(hashes.SHA256()))
    return body + len(signature).to_bytes(MOCK_SIGNATURE_LEN_SIZE, "little") + signature
