from Crypto.Util.number import bytes_to_long, long_to_bytes, getPrime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Util import Counter

import os
import random
from hashlib import sha256

from . import db

KEY = os.urandom(16)
NONCE = os.urandom(8)

class SEA:

    P = 1997
    g = 16
    h = 2

    A = 0xDEADBEEFBAAD0A55
    B = 0x228F00DBABA1CAAA
    C = 0x5EC0DE526914808A
    D = 0xFADA6788D0001228

    ROUNDS = 8


    def pad(self, data):
        pad_len = 8 - (len(data) % 8)
        return data + bytes([pad_len] * pad_len)

    def unpad(self, data):
        pad_len = data[-1]
        if pad_len > 8 or pad_len == 0 or data[-pad_len:] != bytes([pad_len] * pad_len):
            raise ValueError("error: invalid padding")
        return data[:-pad_len]

    @staticmethod
    def cipher_block(block_int, k1, k2, decrypt=False):

        if decrypt:
            k1_inv = pow(k1, -1, 2**64)
            state = block_int
            for _ in range(SEA.ROUNDS):
                state ^= (state >> 32)
                state = (state - k2) & 0xFFFFFFFFFFFFFFFF
                state = (state * k1_inv) & 0xFFFFFFFFFFFFFFFF
            return state
        
        else:
            state = block_int
            for _ in range(SEA.ROUNDS):
                state = (state * k1) & 0xFFFFFFFFFFFFFFFF
                state = (state + k2) & 0xFFFFFFFFFFFFFFFF
                state ^= (state >> 32)
            return state

    def keygen(self, plaintext_bytes):

        sec_exp = random.getrandbits(256)
        key_base = pow(self.g, sec_exp, self.P)
        
        S = int.from_bytes(sha256(plaintext_bytes).digest()[:2], 'big')
        token = pow(self.h, S, self.P)
        
        internal_kb = (key_base + S) % self.P
        
        k1 = (internal_kb * self.A + self.B) & 0xFFFFFFFFFFFFFFFF
        k2 = (internal_kb * self.C + self.D) & 0xFFFFFFFFFFFFFFFF
        k1 |= 1
        
        return (k1, k2), token, key_base

    def encrypt(self, plaintext_bytes):

        key, token, _ = self.keygen(plaintext_bytes)
        k1, k2 = key
        
        padded_plaintext = self.pad(plaintext_bytes)
        ciphertext = b''
        
        for i in range(0, len(padded_plaintext), 8):
            block_int = int.from_bytes((padded_plaintext[i:i+8]), 'big')
            encrypted_int = self.cipher_block(block_int, k1, k2)
            ciphertext += encrypted_int.to_bytes(8, 'big')
            
        return ciphertext, token, key

    def decrypt(self, ciphertext_bytes, key):

        k1, k2 = key
        plaintextpadded = b''

        for i in range(0, len(ciphertext_bytes), 8):
            block = ciphertext_bytes[i:i+8]
            block_int = int.from_bytes((block), 'big')
            decrypted_int = self.cipher_block(block_int, k1, k2, decrypt=True)
            plaintextpadded += decrypted_int.to_bytes(8, 'big')

        try:
            plaintext = self.unpad(plaintextpadded)
            return plaintext
        except ValueError as e:
            print(f"error: {e}")
            return None

def encryption_security_clearance_level_3(plaintext: bytes, username: str = None) -> int:

    plaintext = bytes_to_long(plaintext)
    p = getPrime(1024)
    q = getPrime(1024)

    n = p * q
    
    phi = (p-1)*(q-1)
    while True:
        d = getPrime(256)
        e = pow(d,-1,phi)
        if e.bit_length() == n.bit_length():
            break
    ciphertext = pow(plaintext, e, n)
    rec_id = None
    try:
        ct_hex = hex(ciphertext)[2:]
        n_hex = hex(n)[2:]
        e_hex = hex(e)[2:]
        rec_id = db._insert_level3(ct_hex, n_hex, e_hex, username)
    except Exception:
        rec_id = None

    return hex(ciphertext)[2:], hex(n)[2:], hex(e)[2:], hex(d)[2:], rec_id

def decryption_security_clearance_level_3(ciphertext: str, n: str, d: str) -> str:
    if isinstance(ciphertext, str):
        ciphertext = int(ciphertext, 16)
    
    n = int(n, 16)
    d = int(d, 16)

    message = pow(ciphertext, d, n)
    message = long_to_bytes(message)

    try:
        return message.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return message.decode('utf-8', errors='replace')
        except:
            return message.hex()

def encryption_security_clearance_level_2(plaintext: bytes, username: str = None) -> str:

    ctr = Counter.new(64, prefix=NONCE)
    cipher = AES.new(KEY, AES.MODE_CTR, counter=ctr)
    
    ciphertext = cipher.encrypt(plaintext)
    ct_hex = ciphertext.hex()
    key_hex = KEY.hex()
    nonce_hex = NONCE.hex()

    rec_id = None
    try:
        rec_id = db._insert_level2(ct_hex, nonce_hex, username)
    except Exception:
        rec_id = None

    return ct_hex, key_hex, nonce_hex, rec_id

def decryption_security_clearance_level_2(ciphertext: str, key: str, nonce: str):
    
    ciphertext = bytes.fromhex(ciphertext)
    key = bytes.fromhex(key)
    nonce = bytes.fromhex(nonce)
    
    ctr = Counter.new(64, prefix=nonce)
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
    
    message = cipher.decrypt(ciphertext)

    try:
        return message.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return message.decode('utf-8', errors='replace')
        except:
            return message.hex()

def encryption_security_clearance_level_1(plaintext: bytes, username: str = None): 

    cipher = SEA()
    ciphertext, token, key = cipher.encrypt(plaintext)
    ct_hex = ciphertext.hex()
    rec_id = None
    try:
        rec_id = db._insert_level1(ct_hex, token, username)
    except Exception:
        rec_id = None

    return ct_hex, token, key, rec_id

def decryption_security_clearance_level_1(ciphertext: str, key: tuple):

    cipher = SEA()
    ciphertext = bytes.fromhex(ciphertext)
    message = cipher.decrypt(ciphertext, key)

    if message is None:
        return "Ошибка дешифрования"
    
    try:
        return message.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return message.decode('utf-8', errors='replace')
        except:
            return message.hex()


_counter = 0

def generate_secure_key(length=24):
    global _counter
    p_outer = 127
    p_middle = 251
    p_inner = 97
    
    g_outer = 3
    g_middle = 5
    g_inner = 6
    
    cycle_pos = _counter % 100
    _counter += 1
    
    key_bytes = []
    for i in range(length):
        inner_base = (cycle_pos * 7 + i * 13) % (p_inner - 1)
        inner_val = pow(g_inner, inner_base, p_inner)
        
        middle_base = (inner_val + cycle_pos * 11 + i * 17) % (p_middle - 1)
        middle_exp = (cycle_pos * 3 + i * 5 + inner_val) % (p_middle - 1)
        middle_val = pow(g_middle, middle_exp, p_middle)
        
        combined = (inner_val * middle_val) % p_middle
        
        outer_base = (combined + cycle_pos * 19 + i * 23) % (p_outer - 1)
        outer_exp = (cycle_pos * 2 + i * 7 + combined % (p_outer - 1)) % (p_outer - 1)
        outer_val = pow(g_outer, outer_exp, p_outer)
        
        final = (outer_val * combined + middle_val) % 256
        key_bytes.append(final)
    
    return bytes(key_bytes)
