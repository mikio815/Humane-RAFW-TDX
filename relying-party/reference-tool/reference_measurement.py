#!/usr/bin/env python3
import os
import sys

ATT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../attester")
)
sys.path.insert(0, ATT_PATH)

from tdx_wrapper import get_tdx_quote


def generate_and_parse_quote():
    # Report Data は不要なので 64byte ゼロ埋め
    report_data = b"\x00" * 64

    print("[*] Generating TD Quote...")
    quote = get_tdx_quote(report_data)
    print(f"[*] Quote size: {len(quote)} bytes")

    quote_version = int.from_bytes(quote[0:2], "little")
    tee_type = int.from_bytes(quote[4:8], "little")

    print(f"[*] Quote version : {quote_version}")
    print(f"[*] TEE type      : 0x{tee_type:08x}")

    if tee_type != 0x81:
        raise RuntimeError("Not a TDX Quote")

    if quote_version == 4:
        report_base = 48
    elif quote_version == 5:
        report_base = 54
    else:
        raise RuntimeError(f"Unsupported Quote version: {quote_version}")

    mr_seam        = quote[report_base + 16  : report_base + 16  + 48]
    mrsigner_seam  = quote[report_base + 64  : report_base + 64  + 48]
    mr_td          = quote[report_base + 136 : report_base + 136 + 48]
    mr_config_id   = quote[report_base + 184 : report_base + 184 + 48]
    mr_owner       = quote[report_base + 232 : report_base + 232 + 48]
    mr_owner_config = quote[report_base + 280 : report_base + 280 + 48]

    rtmrs = [
        quote[report_base + 328 + i*48 : report_base + 328 + (i+1)*48]
        for i in range(4)
    ]

    W = 15
    print("\n=== Reference Measurements ===")
    print(f"{'MRSEAM':<{W}}: {mr_seam.hex()}\n")
    print(f"{'MRSIGNERSEAM':<{W}}: {mrsigner_seam.hex()}\n")
    print(f"{'MRTD':<{W}}: {mr_td.hex()}\n")
    print(f"{'MRCONFIGID':<{W}}: {mr_config_id.hex()}\n")
    print(f"{'MROWNER':<{W}}: {mr_owner.hex()}\n")
    print(f"{'MROWNERCONFIG':<{W}}: {mr_owner_config.hex()}\n")

    for i, rtmr in enumerate(rtmrs):
        print(f"{'RTMR[' + str(i) + ']':<{W}}: {rtmr.hex()}\n")


if __name__ == "__main__":
    generate_and_parse_quote()
