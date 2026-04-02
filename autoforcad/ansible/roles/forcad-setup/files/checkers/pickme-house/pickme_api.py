from bs4 import BeautifulSoup
from checklib import *
import requests
import random

PORT = 10000

req_ua_agents = ['python-requests/2.{}.0'.format(x) for x in range(15, 28)]

class PickmeApi:
    def __init__(self, host: str):
        self.host = host
        self.port = PORT
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(req_ua_agents)
        })
        self.base_url = f'http://{self.host}:{self.port}'

    def build_url(self, *args):
        return '/'.join((self.base_url, *args))
    
    def ping(self) -> bool:
        try:
            res = self.session.get(self.build_url('login'))
            if res.status_code != 200:
                return False

            page = BeautifulSoup(res.text, 'html.parser')
            if page.title.string != '💖 hi girl! 💖':
                return False

            return True

        except Exception as e:
            return False

    def register(self, un: str, pwd: str) -> bool:
        try:
            res = self.session.post(self.build_url('register'), data={'user': un, 'pwd': pwd, 'pwd2': pwd})
            if res.status_code != 200:
                return False
            
            page = BeautifulSoup(res.text, 'html.parser')
            status = page.find('div', class_='flash success girly-flash').text
            if status != 'Agent created — please log in':
                return False
            
            return True

        except Exception as e:
            return False

    def login(self, un: str, pwd: str) -> bool:
        try:
            res = self.session.post(self.build_url('login'), data={'user': un, 'pwd': pwd})
            if res.status_code != 200:
                return False

            page = BeautifulSoup(res.text, 'html.parser')
            if page.title.string != '💖 pickme house 💖':
                return False

            return True

        except Exception as e:
            return False

    def get_profile(self) -> tuple[str, str]:
        try:
            res = self.session.get(self.build_url('profile'))
            if res.status_code != 200:
                return None, None
            
            page = BeautifulSoup(res.text, 'html.parser')
            un = page.find('div', class_='girly-subtitle').text.split()[3]
            bio = page.find('textarea', id='bio').text
            return un, bio
        
        except Exception as e:
            return None, None

    def set_bio(self, bio: str) -> bool:
        try:
            res = self.session.post(self.build_url('profile'), data={'bio': bio})
            if res.status_code != 200:
                return False
            
            return True
        
        except Exception as e:
            return False

    def encrypt(self, level: str, plaintext: str) -> dict:
        try:
            data = {
                'action': 'encrypt',
                'level': level,
                'plaintext': plaintext
            }

            res = self.session.post(self.build_url('process'), data=data)
            if res.status_code != 200:
                return None
            
            record = dict()
            enc = dict()

            page = BeautifulSoup(res.text, 'html.parser')
            record['level'] = level
            record['id'] = page.find('span', class_='record-id').text

            result_panel = page.find('div', id='result-panel')
            result = result_panel.find_all('div')[2:]

            if level == '1':
                enc['ct_hex'] = result[0].text.split()[-1]
                enc['token'] = result[1].text.split()[-1]
                enc['key_literal'] = ''.join(result[2].text.split()[-2:])

            elif level == '2':
                enc['ct_hex'] = result[0].text.split()[-1]
                enc['key_hex'] = result[1].text.split()[-1]
                # enc['nonce_hex'] = result[2].text.split()[-1]

            elif level == '3':
                enc['ct_hex'] = result[0].text.split()[-1]
                # enc['n'] = result[1].text.split()[-1]
                enc['d'] = result[3].text.split()[-1]

            else:
                return None

            record['enc'] = enc

            return record

        except Exception as e:
            return None
        
    def decrypt(self, record: dict) -> str:
        try:
            data = {
                'action': 'decrypt',
                'level': record['level']
            }
            data.update(record['enc'])

            res = self.session.post(self.build_url('process'), data=data)
            if res.status_code != 200:
                return None

            page = BeautifulSoup(res.text, 'html.parser')
            return page.find('pre').text

        except Exception as e:
            return None
        
    def lookup(self, level: str, rec_id: str) -> dict:
        try:
            data = {
                'level': level,
                'rec_id': rec_id,
            }

            res = self.session.post(self.build_url('lookup'), data=data)
            if res.status_code != 200:
                return None
            
            page = BeautifulSoup(res.text, 'html.parser')
            result_panel = page.find('div', id='result-panel')
            result = result_panel.find_all('div', class_='field-value')

            record = dict()
            enc = dict()

            record['level'] = level
            record['id'] = result[0].text
            record['enc'] = dict()

            if record['level'] == '1':
                enc['ct_hex'] = result[2].text
                enc['token'] = result[3].text

            elif record['level'] == '2':
                enc['ct_hex'] = result[2].text
                enc['nonce_hex'] = result[3].text

            elif record['level'] == '3':
                enc['ct_hex'] = result[2].text
                enc['n'] = result[3].text

            else:
                return None

            record['enc'] = enc

            return record

        except Exception as e:
            return None