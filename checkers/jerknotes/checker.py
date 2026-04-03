#!/usr/bin/env -S python3
import random
import sys

from checklib import *
from checklib import status

import jerknote_lib

proxies = {
    'http':'http://127.0.0.1:8080',
    'https':'http://127.0.0.1:8080'
}

class Checker(BaseChecker):
    vulns: int = 1
    timeout: int = 25
    uses_attack_data: bool = True


    def __init__(self, *args, **kwargs):
        super(Checker, self).__init__(*args, **kwargs)
        self.lib = jerknote_lib.Jerknote(self)

    def session_with_req_ua(self):
        sess = get_initialized_session()
        if random.randint(0, 1) == 1:
            sess.headers['User-Agent'] = rnd_useragent()
        return sess
    


    def check(self):
        session = self.session_with_req_ua()
        em, p = rnd_username()+'@'+rnd_string(4)+'.com', rnd_password()

        ping = self.lib.ping()
        if not ping:
            self.cquit(Status.DOWN)

        if self.lib.signup_mail(session, em, p) == 0:
            self.cquit(Status.MUMBLE, "Failed register mail")

        if self.lib.signin_mail(session, em, p) == 0:
            self.cquit(Status.MUMBLE, "Failed login mail")
            
        if self.lib.signup_app(session, em, p) == 0:
            self.cquit(Status.MUMBLE, "Failed register app")

        content = jerknote_lib.gen_note_text()
        title = "День #" + str(random.randint(1,5000))
        note_id = self.lib.create_note(session,content,title).split('Note Created:')[1].strip()
        if str(note_id) == '0':
            self.cquit(Status.MUMBLE, "Failed create a note")

        note = self.lib.get_note(session, note_id)
        if str(note) != content:
            self.cquit(Status.MUMBLE, "Failed get a note")

        if self.lib.create_backup(session) == 0:
            self.cquit(Status.MUMBLE, "Failed create backup")
        
        if self.lib.delete_note(session, note_id) == 0:
            self.cquit(Status.MUMBLE, "Failed delete note")

        note = self.lib.get_note(session, note_id)
        if str(note) != '0':
            self.cquit(Status.MUMBLE, "Failed get note after delete")

        if self.lib.restore_backup(session) == 0:
            self.cquit(Status.MUMBLE, "Failed restore backup")

        note = self.lib.get_note(session, note_id)
        if str(note) != content:
            self.cquit(Status.MUMBLE, "Failed get note after backup restore ")

        
        if self.lib.start_reset(session, em) == 0:
            self.cquit(Status.MUMBLE, "Failed when sending reset code")

        code = self.lib.get_reset_code(session)
        if str(code) == '0':
            self.cquit(Status.MUMBLE, "Failed when get reset code")
        
        np = rnd_password()
        if self.lib.set_password(session, em, np, code) == 0:
            self.cquit(Status.MUMBLE, "Failed when set new passw")
        
        if self.lib.signin_app(session, em, np) == 0:
            self.cquit(Status.MUMBLE, "Failed to signin after reset pass")

        note = self.lib.get_note(session, note_id)
        if str(note) != content:
            self.cquit(Status.MUMBLE, "Failed to get note after reset pass")
        

        self.cquit(Status.OK)

    def put(self, flag_id: str, flag: str, vuln: str):
        sess = self.session_with_req_ua()
        em, p = rnd_username()+'@'+rnd_string(4)+'.com', rnd_password()

        self.lib.signup_mail(sess, em, p)
        self.lib.signin_mail(sess, em, p)
        self.lib.signup_app(sess, em, p)

        filename = rnd_string(5) + '.txt'
        put = self.lib.create_file(sess,filename, flag)

        if put == 1:
            self.cquit(Status.OK, em, f"{em}:{p}:{filename}")

        self.cquit(Status.MUMBLE)

    def get(self, flag_id: str, flag: str, vuln: str):
        em, p, filename = flag_id.split(':')
        sess = self.session_with_req_ua()

        if self.lib.signin_app(sess, em, p, status=Status.CORRUPT) == 0:
            self.cquit(Status.CORRUPT,'Error while login')

        file = self.lib.get_file(sess,filename,status=Status.CORRUPT)
        if str(file) != flag:
            self.cquit(Status.CORRUPT, 'Flag isnt correct')
        
        self.cquit(Status.OK)

if __name__ == '__main__':
    c = Checker(sys.argv[2])
    try:
        c.action(sys.argv[1], *sys.argv[3:])
    except c.get_check_finished_exception() as e:
        cquit(status.Status(c.status), c.public, c.private)