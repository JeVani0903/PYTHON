import sqlite3
import os

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        queries = [
            '''CREATE TABLE IF NOT EXISTS albums (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, album_name TEXT NOT NULL, cover_path TEXT, chu_de TEXT, phan_loai TEXT, quoc_gia TEXT, the_loai TEXT, tac_gia TEXT, note TEXT)''',
            '''CREATE TABLE IF NOT EXISTS download_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, name TEXT, start_num INTEGER DEFAULT 1, total_img INTEGER DEFAULT 59)''',
            '''CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, name TEXT NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, t_type TEXT, amount TEXT, t_date TEXT, note TEXT)''',
            '''CREATE TABLE IF NOT EXISTS app_links (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, path TEXT NOT NULL)'''
        ]
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            for q in queries: c.execute(q)
            c.execute("CREATE INDEX IF NOT EXISTS idx_album_name ON albums (album_name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_chu_de ON albums (chu_de)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_phan_loai ON albums (phan_loai)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_quoc_gia ON albums (quoc_gia)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_the_loai ON albums (the_loai)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tac_gia ON albums (tac_gia)")
            conn.commit()

        # Vá lỗi db cũ nếu có
        try: self.execute("ALTER TABLE albums ADD COLUMN phan_loai TEXT")
        except: pass
        try: self.execute("ALTER TABLE albums ADD COLUMN note TEXT")
        except: pass

    def execute(self, query, params=()):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return c.lastrowid

    def executemany(self, query, params_list):
        with sqlite3.connect(self.db_path) as conn:
            conn.cursor().executemany(query, params_list)
            conn.commit()

    def fetchall(self, query, params=()):
        with sqlite3.connect(self.db_path) as conn:
            return conn.cursor().execute(query, params).fetchall()

    def fetchone(self, query, params=()):
        with sqlite3.connect(self.db_path) as conn:
            return conn.cursor().execute(query, params).fetchone()
