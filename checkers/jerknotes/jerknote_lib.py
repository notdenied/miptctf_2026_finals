import random
import checklib
from checklib import BaseChecker
import requests
import os

PORT_APP = 31338
PORT_MAIL = 31337


class Jerknote():
    @property
    def app_url(self):
        return f'http://{self.host}:{self.port_app}'
    
    @property
    def mail_url(self):
        return f'http://{self.host}:{self.port_mail}'
    
    def __init__(self, checker: BaseChecker, port=PORT_APP, host=None):
        self.c = checker
        self.port_app = port
        self.port_mail = PORT_MAIL
        self.host = host or self.c.host
    
    def ping(self):
        try:
            requests.get(self.app_url)
            requests.get(self.mail_url)
            return 1
        except Exception:
            return 0

    def signup_mail(self, session: requests.Session, email: str, password: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.mail_url}/register', json={
                'email':email, 'password':password
            }, timeout=5)
            resp_data = self.c.get_json(resp, 'Failed to signup mail: invalid data')
            self.c.assert_eq(resp_data['message'],'User registered successfully','Failed to signup mail', status=status)
        except Exception:
            return 0

    def signin_mail(self, session: requests.Session, email: str, password: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.mail_url}/login', json={
                'email':email, 'password':password
            }, timeout=5)
            resp_data = self.c.get_json(resp, 'Failed to login mail: invalid data')
            self.c.assert_eq(resp_data['message'],'Login successful','Failed to login mail', status=status)

        except Exception:
            return 0

    def signup_app(self, session: requests.Session, email: str, password: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.app_url}/auth/register', data={
                'username':email, 'password':password, 'confirm-password':password
            }, timeout=5)
            resp_data = self.c.get_text(resp, 'Failed to signup app: invalid data')
            self.c.assert_eq('Профиль пользователя' in resp_data,True,'Failed to signup app', status=status)

        except Exception:
            return 0
    
    def signin_app(self, session: requests.Session, email: str, password: str, status: checklib.Status = checklib.Status.MUMBLE):
            try:
                resp = session.post(f'{self.app_url}/auth/login', data={
                    'username':email, 'password':password
                }, timeout=5)
                resp_data = self.c.get_text(resp, 'Failed to signin app: invalid data')
                self.c.assert_eq('Профиль пользователя' in resp_data,True,'Failed to signin app', status=status)
                return resp_data
            except Exception:
                return 0

    
    def create_note(self, session: requests.Session, content: str, title: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.app_url}/api/notes/add', files={
                'title': (None, title), 'text': (None,content)
            }, timeout=5)
            resp_data = self.c.get_text(resp, 'Failed to create note: invalid data')
            self.c.assert_eq('Note Created' in resp_data,True,'Failed when create note', status=status)
            return resp_data
        except Exception:
            return 0
    
    def get_note(self, session: requests.Session, note_id: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.get(f'{self.app_url}/api/notes/get?id={note_id}', timeout=5)
            self.c.assert_eq(resp.status_code,200,'Failed get note', status=status)
            return resp.json()['text']
        except Exception:
            return 0
    
    def delete_note(self, session: requests.Session, note_id: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.delete(f'{self.app_url}/api/notes/delete?id={note_id}',timeout=5)
            resp_data = self.c.get_text(resp, 'Failed to delete note: invalid data')
            self.c.assert_eq(resp_data, 'deleted', 'Failed to delete note',status=status)
            return resp_data
        except Exception:
            return 0
    

    def create_file(self, session: requests.Session, filename: str, content: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.app_url}/api/files/upload', files={
                'file': (filename, content)
            }, timeout=5)
            self.c.assert_eq(resp.text, 'Successfully uploaded', 'Failer when upload file', status=status)
            self.c.get_text(resp, 'Failed to upload file: invalid data in response')
            return 1
        except Exception:
            return 0
            
    
    def get_file(self, session: requests.Session, filename: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.get(f'{self.app_url}/api/files/download/{filename}', timeout=5)
            self.c.assert_eq(resp.status_code, 200, 'Failed to get file', status=status)
            resp_data = self.c.get_text(resp, 'Failed to get file: invalid data')
            return resp_data
        except Exception:
            return 0

    def create_backup(self, session: requests.Session, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.app_url}/api/notes/backup', timeout=5)
            resp_data = self.c.get_text(resp, 'Failed to backup: invalid data')
            self.c.assert_eq(resp_data, 'Successfully backuped', 'Failed to backup', status=status)
            return 1
        except Exception:
            return 0

    def restore_backup(self, session: requests.Session, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.app_url}/api/notes/restore', timeout=5)
            self.c.assert_eq(resp.text, 'Successfully restored from backup', 'Failed to restore backup', status=status)
            resp_data = self.c.get_text(resp, 'Failed to restore backup: invalid data')
            return resp_data
        except Exception:
            return 0

    def start_reset(self, session: requests.Session, email: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.app_url}/auth/reset', data={'email':email},timeout=5)
            self.c.assert_eq(resp.status_code, 200, 'Failed to reset password', status=status)
            resp_data = self.c.get_text(resp, 'Failed to reset password: invalid data')
            return resp_data
        except Exception:
            return 0

    def get_reset_code(self, session: requests.Session, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.get(f'{self.mail_url}/mails', timeout=5)
            self.c.assert_eq(resp.status_code, 200, 'Failed to get letters', status=status)
            resp_data = self.c.get_json(resp, 'Failed to get letters: invalid data')
            return resp_data[0]['content'].split('.')[0].split(':')[1].strip()
        except Exception:
            return 0

    def set_password(self, session: requests.Session, email: str, newpass: str, code: str, status: checklib.Status = checklib.Status.MUMBLE):
        try:
            resp = session.post(f'{self.app_url}/auth/setpass', data={
                'email':email, 
                'resetCode':code,
                'newPassword':newpass
            }, timeout=5)
            self.c.assert_eq(resp.status_code, 200, 'Failed to set new password', status=status)
            resp_data = self.c.get_text(resp, 'Failed to set new password: invalid data')
            return resp_data
        except Exception:
            return 0
    

def gen_note_text():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, 'todos.txt'), 'r') as file:
        notetext = random.choices(file.readlines(), k=5)
        return '-' + '-'.join(notetext)