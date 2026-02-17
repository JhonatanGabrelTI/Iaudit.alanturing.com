
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import os

CERT_FILE = r"C:\nginx\conf\cert.pem"
KEY_FILE = r"C:\nginx\conf\key.pem"

def generate_self_signed_cert():
    # Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"BR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Parana"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Curitiba"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"IAudit System"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"iaudit.alanturing.com"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # Valid for 10 years
        datetime.datetime.utcnow() + datetime.timedelta(days=3650)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"iaudit.alanturing.com"), x509.DNSName(u"localhost"), x509.IPAddress(import_ip_address("127.0.0.1"))]),
        critical=False,
    ).sign(key, hashes.SHA256())

    # Write key to file
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Write cert to file
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print(f"[OK] Generated self-signed certificate at {CERT_FILE}")
    print(f"[OK] Generated private key at {KEY_FILE}")

def import_ip_address(ip):
    import ipaddress
    return ipaddress.ip_address(ip)

if __name__ == "__main__":
    generate_self_signed_cert()
