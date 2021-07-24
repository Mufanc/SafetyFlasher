from Crypto.Cipher import AES
from base64 import b64encode


def pkcs7_fix(plain):
    padding_size = (AES.block_size - len(plain) % AES.block_size)
    return plain + padding_size * chr(padding_size)


def encrypt(passwd, data):
    passwd += '\x00' * (16 - len(passwd))
    cipher = AES.new(passwd.encode(), AES.MODE_ECB)
    encrypted = cipher.encrypt(pkcs7_fix(data).encode())
    return b64encode(encrypted).decode().replace('+', '-').replace('/', '_')
