import ctypes
import os
from dataclasses import dataclass
from typing import Optional

LIB = "./libqvlwrapper.so"
if not os.path.exists(LIB):
    raise RuntimeError("libqvlwrapper.so not found. Run `make build` first.")

lib = ctypes.CDLL(LIB)


class QvlVerifyOut(ctypes.Structure):
    _fields_ = [
        ("wrapper_ret", ctypes.c_int32),
        ("dcap_ret", ctypes.c_uint32),
        ("collateral_expiration_status", ctypes.c_uint32),
        ("quote_verification_result", ctypes.c_uint32),
        ("supp_data_size", ctypes.c_uint32),
        ("supp_data", ctypes.POINTER(ctypes.c_uint8)),
    ]

@dataclass
class QvlVerifyOutPy:
    wrapper_ret: int
    dcap_ret: int
    collateral_expiration_status: int
    quote_verification_result: int
    supplemental_data: Optional[bytes]


lib.qvl_verify_quote.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_uint32
]
lib.qvl_verify_quote.restype = QvlVerifyOut

lib.qvl_free_buffer.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
lib.qvl_free_buffer.restype = None


def verify_quote(quote: bytes) -> QvlVerifyOutPy:
    if not isinstance(quote, (bytes, bytearray)):
        raise TypeError("quote must be bytes")

    buf = (ctypes.c_uint8 * len(quote)).from_buffer_copy(quote)
    out = lib.qvl_verify_quote(buf, ctypes.c_uint32(len(quote)))

    supp_bytes = b""
    if out.supp_data_size > 0 and out.supp_data:
        supp_bytes = ctypes.string_at(out.supp_data, out.supp_data_size)
        lib.qvl_free_buffer(out.supp_data)

    return QvlVerifyOutPy(
        wrapper_ret=out.wrapper_ret,
        dcap_ret=out.dcap_ret,
        collateral_expiration_status=out.collateral_expiration_status,
        quote_verification_result=out.quote_verification_result,
        supplemental_data=supp_bytes if supp_bytes else None,
    )