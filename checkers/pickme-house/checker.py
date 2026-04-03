#!/usr/bin/env -S python3

from checklib import *
import pickme_api
from pickme_generator import pickme_username, pickme_spletny
import sys
import json
import base64


class Checker(BaseChecker):
    vulns: int = 4
    timeout: int = 20
    uses_attack_data: bool = True

    def __init__(self, *args, **kwargs):
        super(Checker, self).__init__(*args, **kwargs)
        self.api = pickme_api.PickmeApi(self.host)

    def check(self):
        assert_(self.api.ping(), '', Status.DOWN)
        self.cquit(Status.OK)

    def put(self, flag_id: str, flag: str, vuln: str):
        un = pickme_username()
        pwd = rnd_password(16)

        assert_(self.api.register(un, pwd), 'Registration failed')
        assert_(self.api.login(un, pwd), 'Login failed')

        chk_un, bio = self.api.get_profile()
        assert_eq(un, chk_un, 'Broken profile')
        secret = pickme_spletny() + " " + flag 

        if 1 <= int(vuln) <= 3:
            record = self.api.encrypt(vuln, secret)
            assert_(record != None, "Broken encryption")

        elif int(vuln) == 4:
            assert_(self.api.set_bio(secret), "Broken bio")
            self.cquit(Status.OK, {'user': un}, f"{un}:{pwd}:")

        self.cquit(Status.OK, 
                   {'user': un, 'rec_id': record['id'], 'level': record['level']}, 
                   f'{un}:{pwd}:{base64.b64encode(json.dumps(record).encode()).decode()}'
        )

    def get(self, flag_id: str, flag: str, vuln: str):
        un, pwd, record = flag_id.split(':')
        if record.strip():
            record = json.loads(base64.b64decode(record).decode())

        assert_(self.api.login(un, pwd), 'Login failed', Status.CORRUPT)

        chk_un, bio = self.api.get_profile()
        assert_eq(un, chk_un, 'Broken profile')

        if 1 <= int(vuln) <= 3:
            lookup = self.api.lookup(record['level'], record['id'])
            assert_eq(record['enc']['ct_hex'], lookup['enc']['ct_hex'], "Lookup mismatch", Status.CORRUPT)
            if int(vuln) == 1:
                assert_eq(record['enc']['token'], lookup['enc']['token'], "Lookup mismatch", Status.CORRUPT)
                del lookup['enc']['token']

            record['enc'].update(lookup['enc'])

            decrypt = self.api.decrypt(record)
            assert_(flag in decrypt, "Decryption failed", Status.CORRUPT)

        elif int(vuln) == 4:
            assert_(flag in bio, 'Invalid flag', Status.CORRUPT)
        
        self.cquit(Status.OK)


if __name__ == '__main__':
    c = Checker(sys.argv[2])
    try:
        c.action(sys.argv[1], *sys.argv[3:])
    except c.get_check_finished_exception() as e:
        cquit(Status(c.status), c.public, c.private)