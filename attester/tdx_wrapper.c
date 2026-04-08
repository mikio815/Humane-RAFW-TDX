#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "tdx_attest.h"


int get_tdx_quote_wrapper(uint8_t report_data_raw[64], 
    uint8_t **out_quote, uint32_t *out_size)
{
    tdx_report_data_t rd = {0};
    memcpy(rd.d, report_data_raw, 64);

    tdx_uuid_t selected_key = {0};
    uint8_t *quote_buf = NULL;
    uint32_t quote_size = 0;

    int ret = tdx_att_get_quote(
        &rd,
        NULL,
        0,
        &selected_key,
        &quote_buf,
        &quote_size,
        0
    );

    if(ret != TDX_ATTEST_SUCCESS) return ret;

    *out_quote = quote_buf;
    *out_size = quote_size;

    return 0;
}

void free_tdx_quote(uint8_t *buf)
{
    tdx_att_free_quote(buf);
}