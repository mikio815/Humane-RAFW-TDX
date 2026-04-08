from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
import hashlib


def generate_tls_cert():
    private_key = ec.generate_private_key(
        ec.SECP256R1(),
        default_backend()
    )

    public_key = private_key.public_key()

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"JP"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Aichi"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Nagoya"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Acompany co., Ltd."),
        x509.NameAttribute(NameOID.COMMON_NAME, u"attested-td"),
    ])

    # SAN拡張は付与しない。証明書の真正性はTDX QuoteのReport Data内の
    # SHA256(cert)で保証されるため、SANによるホスト名/IP検証は冗長である。
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=30))
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    cert_hash = hashlib.sha256(cert_pem).digest()

    return private_key_pem, cert_pem, cert_hash
