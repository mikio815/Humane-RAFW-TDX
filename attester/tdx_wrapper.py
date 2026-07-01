import ctypes
import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mock_quote import build_mock_quote
from mock_tdx_common import mock_tdx_enabled


def _find_libtdxwrapper():
    # PyInstaller --onefile 実行時
    if hasattr(sys, "_MEIPASS"):
        # 実行ディレクトリにある libtdxwrapper.so を使う
        return os.path.join(os.getcwd(), "libtdxwrapper.so")
    else:
        # 通常の python 実行時
        this_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(this_dir, "libtdxwrapper.so")


LIB_PATH = _find_libtdxwrapper()
MOCK_TDX = mock_tdx_enabled()

if not MOCK_TDX and not os.path.exists(LIB_PATH):
    raise RuntimeError(
        f"libtdxwrapper.so not found at {LIB_PATH}. "
        "Run 'make build' in attester directory first."
    )

lib = None if MOCK_TDX else ctypes.CDLL(LIB_PATH)

if not MOCK_TDX:
    lib.get_tdx_quote_wrapper.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8)),
        ctypes.POINTER(ctypes.c_uint32),
    ]
    lib.get_tdx_quote_wrapper.restype = ctypes.c_int

    lib.free_tdx_quote.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
    lib.free_tdx_quote.restype = None

def get_tdx_quote(report_data: bytes) -> bytes:
    assert len(report_data) == 64

    if MOCK_TDX:
        return build_mock_quote(report_data)

    report = (ctypes.c_uint8 * 64).from_buffer_copy(report_data)

    quote_ptr = ctypes.POINTER(ctypes.c_uint8)()
    quote_size = ctypes.c_uint32()

    ret = lib.get_tdx_quote_wrapper(
        report,
        ctypes.byref(quote_ptr),
        ctypes.byref(quote_size)
    )

    if ret != 0:
        raise RuntimeError(f"Failed to generate TD Quote. (code={ret})")

    quote = ctypes.string_at(quote_ptr, quote_size.value)

    lib.free_tdx_quote(quote_ptr)

    return quote
