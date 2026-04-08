#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "sgx_dcap_quoteverify.h"


typedef struct qvl_verify_out_t {
    int32_t  wrapper_ret;
    uint32_t dcap_ret;
    uint32_t collateral_expiration_status;
    uint32_t quote_verification_result;
    uint32_t supp_data_size;
    uint8_t *supp_data;
} qvl_verify_out_t;

/* Supplemental Dataのバージョン情報用型定義 */
typedef union _supp_ver_t
{
    uint32_t version;
    struct
    {
        uint16_t major_version;
        uint16_t minor_version;
    };
} supp_ver_t;


qvl_verify_out_t qvl_verify_quote(
    const uint8_t *quote,
    uint32_t quote_size)
{
    qvl_verify_out_t out;
    memset(&out, 0, sizeof(out));

    tee_supp_data_descriptor_t supp_data;
    memset(&supp_data, 0, sizeof(supp_data));
    supp_ver_t latest_ver;

    if(!quote || quote_size == 0)
    {
        out.wrapper_ret = -1;
        out.dcap_ret = TEE_ERROR_INVALID_PARAMETER;
        return out;
    }

    quote3_error_t ret =
        tee_get_supplemental_data_version_and_size(
            quote,
            quote_size,
            &latest_ver.version,
            &supp_data.data_size
        );

    if(ret == TEE_SUCCESS && supp_data.data_size == sizeof(sgx_ql_qv_supplemental_t))
    {
        supp_data.p_data = (uint8_t*)malloc(supp_data.data_size);

        if(!supp_data.p_data)
        {
            out.wrapper_ret = -2;
            out.dcap_ret = TEE_ERROR_OUT_OF_MEMORY;
            return out;
        }

        memset(supp_data.p_data, 0, supp_data.data_size);
    }
    else
    {
        supp_data.p_data = NULL;
        supp_data.data_size = 0;
    }

    time_t current_time = time(NULL);
    uint32_t collateral_status = 1;
    sgx_ql_qv_result_t qv_result = TEE_QV_RESULT_UNSPECIFIED;

    ret = tee_verify_quote(
        quote,
        quote_size,
        NULL,
        current_time,
        &collateral_status,
        &qv_result,
        NULL,
        (supp_data.data_size > 0) ? &supp_data : NULL
    );

    out.wrapper_ret = 0;
    out.dcap_ret = ret;
    out.collateral_expiration_status = collateral_status;
    out.quote_verification_result = qv_result;

    out.supp_data_size = supp_data.data_size;
    out.supp_data = supp_data.p_data;

    return out;
}


void qvl_free_buffer(uint8_t *buf)
{
    if(buf) free(buf);
}
