from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ssl
import base64
import hashlib
import subprocess

from cert_gen import generate_tls_cert
from tdx_wrapper import get_tdx_quote

IMA_LOG_PATH = "/sys/kernel/security/ima/ascii_runtime_measurements"

priv_pem, cert_pem, cert_hash = generate_tls_cert()

if len(cert_hash) != 32:
    raise RuntimeError("cert_hash must be 32 bytes.")

app = FastAPI()

class AttestRequest(BaseModel):
    nonce: str

class AddRequest(BaseModel):
    a: int
    b: int


def get_ima_log():
    try:
        with open(IMA_LOG_PATH, "rb") as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Failed to read IMA log: {e}")


def get_tdeventlog():
    try:
        result = subprocess.run(
            ["tdeventlog"],
            capture_output=True,
            timeout=30,
        )
        return result.stderr
    except FileNotFoundError:
        raise RuntimeError("tdeventlog command not found.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("tdeventlog command timed out.")


@app.post("/attest")
def attest(req: AttestRequest):
    try:
        nonce = base64.b64decode(req.nonce, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 format of nonce.")

    if len(nonce) != 32:
        raise HTTPException(status_code=400, detail="Nonce must be 32 bytes.")

    try:
        tdeventlog = get_tdeventlog()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        ima_log = get_ima_log()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    nonce_log_hash = hashlib.sha256(nonce + tdeventlog + ima_log).digest()

    report_data = cert_hash + nonce_log_hash
    assert len(report_data) == 64

    try:
        quote = get_tdx_quote(report_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TDX Quote error: {e}")

    return {
        "quote": quote.hex(),
        "tls_cert": cert_pem.decode(),
        "cert_hash": cert_hash.hex(),
        "tdeventlog": tdeventlog.decode("utf-8", errors="replace"),
        "ima_log": ima_log.decode("utf-8", errors="replace"),
        "nonce_log_hash": nonce_log_hash.hex(),
    }

@app.post("/add")
def add(req: AddRequest):

    result = req.a + req.b

    return {
        "result": result
    }


if __name__ == "__main__":
    # 証明書を書き出し
    with open("tls_cert.pem", "wb") as f:
        f.write(cert_pem)
    with open("tls_key.pem", "wb") as f:
        f.write(priv_pem)

    import uvicorn

    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8443,
        ssl_certfile="tls_cert.pem",
        ssl_keyfile="tls_key.pem",
    )

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain("tls_cert.pem", "tls_key.pem")
    ctx.options |= ssl.OP_NO_TICKET
    config.ssl = ctx

    server = uvicorn.Server(config)
    server.run()
