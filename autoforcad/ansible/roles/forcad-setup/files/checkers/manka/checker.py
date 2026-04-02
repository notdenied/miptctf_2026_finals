#!/usr/bin/env -S python3

from checklib import BaseChecker, status, Status, cquit
import string
import random
import copy
import sys

port = 7191
secret_size = 40
pass_alpha = string.ascii_letters + string.digits
pass_length = 10

argv = copy.deepcopy(sys.argv)

from pwn import *

class C4llChecker(BaseChecker):
    vulns: int = 1
    timeout: int = 5

    def __init__(self, *args, **kwargs):
        super(C4llChecker, self).__init__(*args, **kwargs)

    def check(self):
        try:
            conn = connect(self.host, port, timeout=self.timeout)
            self.cquit(Status.OK)
        except PwnlibException:
            self.cquit(Status.DOWN)
        pass

    def put(self, flag_id: str, flag: str, vuln: str):
        try:
            conn = connect(self.host, port, timeout=self.timeout)
        except PwnlibException:
            self.cquit(Status.DOWN)
        password = rng_password()
        try:
            key = send_flag(conn, flag, password)
            self.cquit(Status.OK, key, f"{key}:{password}")
        except EOFError:
            self.cquit(Status.MUMBLE)
        pass

    def get(self, flag_id: str, flag: str, vuln: str):
        key, password = flag_id.split(":")
        try:
            conn = connect(self.host, port, timeout=self.timeout)
        except PwnlibException:
            self.cquit(Status.DOWN)
        try:
            stored_flag = get_flag(conn, key, password)
        except EOFError:
            self.cquit(Status.CORRUPT)
        if stored_flag != flag:
            self.cquit(Status.CORRUPT)
        self.cquit(Status.OK)


def rng_password():
    return "".join(random.choice(pass_alpha) for _ in range(pass_length))

def send_flag(conn, secret, password):
    conn.recvuntil(b': ')
    conn.sendline(b'1')
    conn.recvuntil(b': ')
    conn.sendline(secret.encode())
    conn.recvuntil(b': ')
    conn.sendline(password.encode())
    conn.recvuntil(b': ')
    key = conn.recvline().replace(b'\n', b'')
    conn.close()
    return key.decode('utf8')

def get_flag(conn, key, password):
    conn.recvuntil(b': ')
    conn.sendline(b'2')
    conn.recvuntil(b': ')
    conn.sendline(key.encode())
    conn.recvuntil(b': ')
    conn.sendline(password.encode())
    conn.recvuntil(b': ')
    stored_secret = conn.recv(secret_size + 1).replace(b'\0', b'').replace(b'\n', b'')
    conn.close()
    return stored_secret.decode('utf8')


context.log_level = 'ERROR'
if __name__ == '__main__':
    c = C4llChecker(argv[2])
    try:
        c.action(argv[1], *argv[3:])
    except c.get_check_finished_exception() as e:
        cquit(status.Status(c.status), c.public, c.private)
    pass
