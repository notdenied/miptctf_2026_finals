import sqlite3
import os
from datetime import datetime
import secrets

STORAGE_DIR = 'storage'
os.makedirs(STORAGE_DIR, exist_ok=True)

DB_PATHS = {
    1: os.path.join(STORAGE_DIR, 'level1.db'),
    2: os.path.join(STORAGE_DIR, 'level2.db'),
    3: os.path.join(STORAGE_DIR, 'level3.db'),
}


def _init_dbs():
    queries = {
        1: 'CREATE TABLE IF NOT EXISTS level1 (id TEXT PRIMARY KEY, ts TEXT, ciphertext_hex TEXT, token TEXT, username TEXT);',
        2: 'CREATE TABLE IF NOT EXISTS level2 (id TEXT PRIMARY KEY, ts TEXT, ciphertext_hex TEXT, nonce_hex TEXT, username TEXT);',
        3: 'CREATE TABLE IF NOT EXISTS level3 (id TEXT PRIMARY KEY, ts TEXT, ciphertext_hex TEXT, n TEXT, e TEXT, username TEXT);',
    }

    for lvl, path in DB_PATHS.items():
        conn = sqlite3.connect(path)
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=-10000')
            conn.execute('PRAGMA temp_store=MEMORY')
            
            cur = conn.cursor()
            cur.execute(queries[lvl])
            conn.commit()
            cur.execute("PRAGMA table_info(level" + str(lvl) + ")")
            columns = [col[1] for col in cur.fetchall()]
            if 'username' not in columns:
                cur.execute('ALTER TABLE level' + str(lvl) + ' ADD COLUMN username TEXT;')
                conn.commit()
            try:
                cur.execute('CREATE INDEX IF NOT EXISTS idx_level' + str(lvl) + '_username ON level' + str(lvl) + '(username);')
                conn.commit()
            except Exception:
                pass
        finally:
            conn.close()


def _insert_level1(ciphertext_hex: str, token, username: str = None) -> str:
    path = DB_PATHS[1]
    conn = sqlite3.connect(path)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()
        ts = datetime.utcnow().isoformat()
        rec_id = secrets.token_hex(6)
        cur.execute('INSERT INTO level1 (id, ts, ciphertext_hex, token, username) VALUES (?, ?, ?, ?, ?)', (rec_id, ts, ciphertext_hex, str(token), username))
        conn.commit()
        return rec_id
    finally:
        conn.close()


def _insert_level2(ciphertext_hex: str, nonce_hex: str, username: str = None) -> str:
    path = DB_PATHS[2]
    conn = sqlite3.connect(path)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()
        ts = datetime.utcnow().isoformat()
        rec_id = secrets.token_hex(6)
        cur.execute('INSERT INTO level2 (id, ts, ciphertext_hex, nonce_hex, username) VALUES (?, ?, ?, ?, ?)', (rec_id, ts, ciphertext_hex, nonce_hex, username))
        conn.commit()
        return rec_id
    finally:
        conn.close()


def _insert_level3(ciphertext_hex: str, n_hex: str, e_hex: str, username: str = None) -> str:
    path = DB_PATHS[3]
    conn = sqlite3.connect(path)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()
        ts = datetime.utcnow().isoformat()
        rec_id = secrets.token_hex(6)
        cur.execute('INSERT INTO level3 (id, ts, ciphertext_hex, n, e, username) VALUES (?, ?, ?, ?, ?, ?)', (rec_id, ts, ciphertext_hex, n_hex, e_hex, username))
        conn.commit()
        return rec_id
    finally:
        conn.close()


def _get_level1_by_id(rec_id: str):
    path = DB_PATHS[1]
    conn = sqlite3.connect(path)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()
        cur.execute('SELECT id, ts, ciphertext_hex, token FROM level1 WHERE id = ?', (rec_id,))
        return cur.fetchone()
    finally:
        conn.close()


def _get_level2_by_id(rec_id: str):
    path = DB_PATHS[2]
    conn = sqlite3.connect(path)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()
        cur.execute('SELECT id, ts, ciphertext_hex, nonce_hex FROM level2 WHERE id = ?', (rec_id,))
        return cur.fetchone()
    finally:
        conn.close()


def _get_level3_by_id(rec_id: str):
    path = DB_PATHS[3]
    conn = sqlite3.connect(path)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()
        cur.execute('SELECT id, ts, ciphertext_hex, n, e FROM level3 WHERE id = ?', (rec_id,))
        return cur.fetchone()
    finally:
        conn.close()


def _get_user_records(username: str, limit: int = 50):
    records = {'level1': [], 'level2': [], 'level3': []}
    
    def get_records_for_level(level: int):
        path = DB_PATHS[level]
        conn = sqlite3.connect(path)
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=-10000')
            cur = conn.cursor()
            cur.execute('SELECT id, ts FROM level' + str(level) + ' WHERE username = ? ORDER BY ts DESC LIMIT ?', (username, limit))
            return cur.fetchall()
        finally:
            conn.close()
    
    try:
        records['level1'] = get_records_for_level(1)
        records['level2'] = get_records_for_level(2)
        records['level3'] = get_records_for_level(3)
    except Exception as e:
        print(f"Error fetching user records: {e}")
    
    return records


_init_dbs()

