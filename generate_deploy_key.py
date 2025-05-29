# generate_deploy_key.py
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate key pair
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# Export private key in PEM format
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)

# Export public key in OpenSSH format
public_ssh = public_key.public_bytes(
    encoding=serialization.Encoding.OpenSSH,
    format=serialization.PublicFormat.OpenSSH
)

# Print both
print("🔐 PRIVATE KEY (save this in Render as secret):\n")
print(private_pem.decode())

print("\n🔓 PUBLIC KEY (add this to GitHub Deploy Keys):\n")
print(public_ssh.decode())
