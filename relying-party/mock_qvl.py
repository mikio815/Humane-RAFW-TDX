from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from mock_tdx_common import MOCK_SUPPLEMENTAL_DATA_SIZE, split_mock_quote_signature


_MOCK_PUBLIC_X = int(
    "16e980a9cae3a3554940f05c65064defe13c7b26a885105d01cd787fef428ded",
    16,
)
_MOCK_PUBLIC_Y = int(
    "7c5ff6dedde39b0ce85a134a97f44df043043462e2e13def22eec6643a330db1",
    16,
)


def _mock_public_key():
    numbers = ec.EllipticCurvePublicNumbers(
        _MOCK_PUBLIC_X,
        _MOCK_PUBLIC_Y,
        ec.SECP256R1(),
    )
    return numbers.public_key()


def verify_mock_quote_signature(quote: bytes) -> bool:
    parts = split_mock_quote_signature(quote)
    if parts is None:
        return False

    body, signature = parts
    try:
        _mock_public_key().verify(signature, body, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def build_mock_supplemental_data() -> bytes:
    return b"\x00" * MOCK_SUPPLEMENTAL_DATA_SIZE
