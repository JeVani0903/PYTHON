import sqlite3
import os

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def init_db(self):
        queries = [
            '''CREATE TABLE IF NOT EXISTS albums (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, album_name TEXT NOT NULL, cover_path TEXT, chu_de TEXT, phan_loai TEXT, quoc_gia TEXT, the_loai TEXT, tac_gia TEXT, note TEXT)''',
            '''CREATE TABLE IF NOT EXISTS download_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, name TEXT, start_num INTEGER DEFAULT 1, total_img INTEGER DEFAULT 59, source TEXT DEFAULT 'Unknown')''',
            '''CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, name TEXT NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, t_type TEXT, amount TEXT, t_date TEXT, note TEXT)''',
            '''CREATE TABLE IF NOT EXISTS app_links (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, path TEXT NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL DEFAULT 'Chung', site TEXT NOT NULL, username TEXT NOT NULL, password TEXT NOT NULL, email TEXT, note TEXT)''',
            '''CREATE TABLE IF NOT EXISTS app_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT DEFAULT 'user')'''
        ]
        
        with self.get_connection() as conn:
            for q in queries: 
                conn.execute(q)
            conn.commit()
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_album_name ON albums (album_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chu_de ON albums (chu_de)")
            conn.commit()
            
            # Khởi tạo account mặc định
            if conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
                default_accs = [
                    ('Công Việc', 'Gmail Công Việc', 'admin_work@gmail.com', 'WorkPass123!@', 'recovery1@gmail.com', 'Mail chính của công ty'),
                    ('Giải Trí / Manga', 'MangaDex API', 'manga_scraper', 'Scrape!99', 'bot@md.org', 'Dùng để kéo API'),
                    ('Lưu Trữ Cloud', 'PCloud Storage', 'storage_admin', 'Cloud@2026', 'admin@cloud.com', 'Lưu trữ tài liệu 500GB')
                ]
                conn.executemany("INSERT INTO accounts (category, site, username, password, email, note) VALUES (?, ?, ?, ?, ?, ?)", default_accs)
                conn.commit()
                
            # Khởi tạo User Admin mặc định nếu chưa có
            if conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0] == 0:
                conn.execute("INSERT INTO app_users (username, password, role) VALUES (?, ?, ?)", ('hello9x', 'Pt169537!', 'admin'))
                conn.commit()

        try: self.execute("ALTER TABLE albums ADD COLUMN phan_loai TEXT")
        except: pass
        try: self.execute("ALTER TABLE albums ADD COLUMN note TEXT")
        except: pass

    def execute(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def executemany(self, query, params_list):
        with self.get_connection() as conn:
            conn.executemany(query, params_list)
            conn.commit()

    def fetchall(self, query, params=()):
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def fetchone(self, query, params=()):
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchone()
