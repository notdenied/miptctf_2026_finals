from flask import Flask, render_template, request, session, redirect, url_for, flash
from functools import wraps
import ast
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import sys, os

from modules import SKZI, db

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 3600
app.secret_key = SKZI.generate_secure_key(24)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('agent'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.before_request
def log_request_info():
    try:
        info = f"REQ {request.method} {request.path}"
        if request.method == 'POST':
            if request.form:
                form_data = dict(request.form)
                if 'pwd' in form_data:
                    form_data['pwd'] = '***'
                if 'pwd2' in form_data:
                    form_data['pwd2'] = '***'
                info += f" FORM={form_data}"
            else:
                try:
                    j = request.get_json(silent=True)
                    if j:
                        info += f" JSON={j}"
                except Exception:
                    pass
        print(info)
    except Exception as e:
        print('log_request_info error', e)
    sys.stdout.flush()


USERS_DB = os.path.join('storage', 'users.db')

def _init_users_db():
    conn = sqlite3.connect(USERS_DB)
    try:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, role TEXT, bio TEXT)')
        conn.commit()
        cur.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cur.fetchall()]
        if 'bio' not in columns:
            cur.execute('ALTER TABLE users ADD COLUMN bio TEXT;')
            conn.commit()
    finally:
        conn.close()


def create_user(username: str, password: str, role: str = 'agent'):
    pw_hash = generate_password_hash(password)
    conn = sqlite3.connect(USERS_DB)
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', (username, pw_hash, role))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user(username: str):
    conn = sqlite3.connect(USERS_DB)
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, username, password_hash, role, bio FROM users WHERE username = ?', (username,))
        return cur.fetchone()
    finally:
        conn.close()


def update_user_bio(username: str, bio: str):
    conn = sqlite3.connect(USERS_DB)
    try:
        cur = conn.cursor()
        cur.execute('UPDATE users SET bio = ? WHERE username = ?', (bio, username))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


_init_users_db()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('user')
        pwd = request.form.get('pwd')
        row = get_user(user)
        if row:
            uid, username, pw_hash, role, bio = row
            if check_password_hash(pw_hash, pwd):
                session['agent'] = username
                return redirect(url_for('index'))
            else:
                flash('Invalid credentials', 'error')
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('agent', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('user')
        pwd = request.form.get('pwd')
        pwd2 = request.form.get('pwd2')
        if not username or not pwd:
            flash('Username and password are required', 'error')
            return render_template('register.html')
        if pwd != pwd2:
            flash('Passcodes do not match', 'error')
            return render_template('register.html')
        try:
            create_user(username, pwd)
            flash('Agent created — please log in', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            msg = str(e)
            if 'UNIQUE constraint' in msg:
                flash('Agent ID already exists', 'error')
            else:
                flash(f'Error creating agent: {e}', 'error')
    return render_template('register.html')


@app.route('/', methods=['GET'])
@login_required
def index():
    return render_template('index.html', agent=session.get('agent'))


@app.route('/process', methods=['POST'])
@login_required
def process():
    action = request.form.get('action')
    
    try:
        level = int(request.form.get('level'))
        if level not in [1, 2, 3]:
            return render_template('result.html', action='none', level=None, 
                                 m='Invalid security level. Must be 1, 2, or 3', 
                                 agent=session.get('agent'))
    except (ValueError, TypeError):
        return render_template('result.html', action='none', level=None, 
                             m='Invalid security level', agent=session.get('agent'))

    if action == 'encrypt':
        plaintext_str = request.form.get('plaintext', '').strip()
        if not plaintext_str:
            return render_template('result.html', action='none', level=None, 
                                 m='Plaintext cannot be empty', agent=session.get('agent'))
        plaintext = plaintext_str.encode('utf-8')

        username = session.get('agent')
        
        if level == 3:
            ct_hex, n, e, d, rec_id = SKZI.encryption_security_clearance_level_3(plaintext, username)
            return render_template('result.html', action=action, level=level,
                                   ct=ct_hex, n=n, e=e, d=d, rec_id=rec_id, agent=username)

        elif level == 2:
            ct_hex, key_hex, nonce_hex, rec_id = SKZI.encryption_security_clearance_level_2(plaintext, username)
            return render_template('result.html', action=action, level=level,
                                   ct=ct_hex, key=key_hex, nonce=nonce_hex, rec_id=rec_id, agent=username)

        elif level == 1:
            ct_hex, token, key, rec_id = SKZI.encryption_security_clearance_level_1(plaintext, username)
            return render_template('result.html', action=action, level=level,
                                   ct=ct_hex, token=token, key=repr(key), rec_id=rec_id, agent=username)

    elif action == 'decrypt':
        if level == 3:
            ct_hex = request.form.get('ct_hex', '').strip()
            n_hex = request.form.get('n', '').strip()
            d_hex = request.form.get('d', '').strip()
            if not ct_hex or not n_hex or not d_hex:
                m = 'Error: ciphertext, n, and d are required'
            else:
                try:
                    m = SKZI.decryption_security_clearance_level_3(ct_hex, n_hex, d_hex)
                except (ValueError, TypeError) as e:
                    m = f'Error: Invalid hex format - {e}'
                except Exception as e:
                    m = f'Error: {e}'
            return render_template('result.html', action=action, level=level, m=m, agent=session.get('agent'))

        elif level == 2:
            ct_hex = request.form.get('ct_hex', '').strip()
            key_hex = request.form.get('key_hex', '').strip()
            if not ct_hex or not key_hex:
                m = 'Error: ciphertext and key are required'
            else:
                try:
                    m = SKZI.decryption_security_clearance_level_2(ct_hex, key_hex, SKZI.NONCE.hex())
                except Exception as e:
                    m = f'Error: {e}'
            return render_template('result.html', action=action, level=level, m=m, agent=session.get('agent'))

        elif level == 1:
            ct_hex = request.form.get('ct_hex', '').strip()
            key_literal = request.form.get('key_literal', '').strip()
            if not ct_hex or not key_literal:
                m = 'Error: ciphertext and key are required'
            else:
                try:
                    key = ast.literal_eval(key_literal)
                    m = SKZI.decryption_security_clearance_level_1(ct_hex, key)
                except (ValueError, SyntaxError) as e:
                    m = f'Error: Invalid key format - {e}'
                except Exception as e:
                    m = f'Error: {e}'
            return render_template('result.html', action=action, level=level, m=m, agent=session.get('agent'))

    return render_template('result.html', action='none', level=None, m='Invalid request', agent=session.get('agent'))


@app.route('/lookup', methods=['POST'])
@login_required
def lookup():
    try:
        level = int(request.form.get('level'))
        rec_id = request.form.get('rec_id', '').strip()
        if level not in [1, 2, 3]:
            return render_template('result.html', action='none', level=None, 
                                 m='Invalid security level. Must be 1, 2, or 3', 
                                 agent=session.get('agent'))
        if not rec_id:
            return render_template('result.html', action='none', level=None, 
                                 m='Record ID is required', 
                                 agent=session.get('agent'))
    except (ValueError, TypeError) as e:
        return render_template('result.html', action='none', level=None, 
                             m=f'Invalid input: {e}', agent=session.get('agent'))

    row = None
    try:
        if level == 1:
            row = db._get_level1_by_id(rec_id)
        elif level == 2:
            row = db._get_level2_by_id(rec_id)
        elif level == 3:
            row = db._get_level3_by_id(rec_id)
    except Exception as e:
        return render_template('result.html', action='none', level=None, 
                             m=f'Error querying DB: {e}', agent=session.get('agent'))

    return render_template('result.html', action='lookup', level=level, row=row, agent=session.get('agent'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    username = session.get('agent')
    
    if request.method == 'POST':
        bio = request.form.get('bio', '').strip()
        if update_user_bio(username, bio):
            flash('Bio updated successfully', 'success')
        else:
            flash('Failed to update bio', 'error')
        return redirect(url_for('profile'))
    
    user_row = get_user(username)
    if user_row:
        user_id, user_username, pw_hash, role, bio = user_row
    else:
        bio = None
        role = 'admin'
    
    records = db._get_user_records(username, limit=20)
    
    return render_template('profile.html', agent=username, bio=bio or '', records=records, role=role)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
