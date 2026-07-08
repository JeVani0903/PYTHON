import sys, os, sqlite3, re, math, traceback, time, threading, ctypes, webbrowser, shutil, tempfile, random, subprocess, queue
import urllib.parse
import urllib.request
from tkinter import messagebox, filedialog
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from urllib.parse import urlparse, urljoin

# 1. THIẾT LẬP MÔI TRƯỜNG & ẨN CONSOLE
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if os.name == 'nt':
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 0)
    except: pass

# 2. BẮT LỖI TOÀN CỤC CHỐNG CRASH APP
def global_exception_handler(exc_type, exc_value, exc_traceback):
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Lỗi Hệ Thống", f"Gặp sự cố vận hành:\n\n{err_msg}")
    root.destroy()
    sys.exit(1)

def tk_exception_handler(exc, val, tb):
    err_msg = "".join(traceback.format_exception(exc, val, tb))
    messagebox.showerror("Lỗi Giao Diện", f"Sự cố luồng hiển thị:\n\n{err_msg}")

sys.excepthook = global_exception_handler
ctk.CTk.report_callback_exception = tk_exception_handler

# 3. BIẾN TOÀN CỤC & GIAO DIỆN
DB_PATH = os.path.join(BASE_DIR, "AIO_Portal_SuperApp_PC.db")
FIXED_GOOGLE_API_KEY = "AIzaSyD8zQpA869UKNitk1jZteUBLLsL_hFLXfE"

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# =========================================================================
# LÕI DATABASE SQLITE (TỐI ƯU WAL MODE ĐA LUỒNG THREAD-SAFE)
# =========================================================================
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
            '''CREATE TABLE IF NOT EXISTS download_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, name TEXT, start_num INTEGER DEFAULT 1, total_img INTEGER DEFAULT 59, source TEXT DEFAULT 'Unknown')''',
            '''CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, name TEXT NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL DEFAULT 'Chung', site TEXT NOT NULL, username TEXT NOT NULL, password TEXT NOT NULL, email TEXT, note TEXT)''',
            '''CREATE TABLE IF NOT EXISTS app_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT DEFAULT 'user')'''
        ]
        with self.get_connection() as conn:
            c = conn.cursor()
            for q in queries: c.execute(q)
            conn.commit()
            
            # Khởi tạo Admin
            if conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0] == 0:
                conn.execute("INSERT INTO app_users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'admin'))
                conn.commit()
                
            # Khởi tạo dữ liệu mẫu cho bảng Account
            if conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
                default_accs = [
                    ('Chung', 'Gmail Công Việc', 'admin@gmail.com', 'Pass123', 'admin@congty.com', 'Mail chính'),
                    ('Giải Trí / Manga', 'MangaDex API', 'scraper', 'Scrape!99', '', 'Kéo API'),
                    ('Lưu Trữ Cloud', 'Google Drive', 'drive_admin', 'Drive2026', 'cloud@abc.com', 'Lưu File')
                ]
                conn.executemany("INSERT INTO accounts (category, site, username, password, email, note) VALUES (?, ?, ?, ?, ?, ?)", default_accs)
                conn.commit()

    def execute(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetchall(self, query, params=()):
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def fetchone(self, query, params=()):
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchone()

db = Database(DB_PATH)

# =========================================================================
# CORE ENGINE: XỬ LÝ KHỐI DỮ LIỆU ĐA PHƯƠNG TIỆN (TỐI ƯU HÓA)
# =========================================================================
class CoreEngine:
    def __init__(self, log_queue, base_dir):
        self.log_queue = log_queue
        self.base_dir = base_dir

    def safe_log(self, text, overwrite=False):
        try: self.log_queue.put({"type": "log", "msg": text, "overwrite": overwrite})
        except: pass

    def run_curl_command(self, url, output_file, referer=None, need_lang=True, is_video=False):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        max_time = 3600 if is_video else 60
        cmd = f'curl.exe -g -s -L -C - --compressed --connect-timeout 15 --max-time {max_time} -A "{ua}"'
        if referer: cmd += f' -e "{referer}"'
        cmd += f' -o "{output_file}" "{url}"'
        try:
            subprocess.run(cmd, shell=True, creationflags=0x08000000)
            return True
        except: return False

    def validate_video_file(self, filepath, target_ext=".mp4"):
        try:
            if not os.path.exists(filepath): return False
            if os.path.getsize(filepath) < 1024:
                os.remove(filepath); return False
            with open(filepath, 'rb') as f: header = f.read(32)
            header_lower = header.lower()
            if b'<html' in header_lower or b'cloudflare' in header_lower:
                os.remove(filepath); return False
            if filepath.lower().endswith('.tmp'):
                new_path = os.path.splitext(filepath)[0] + target_ext
                if os.path.exists(new_path): os.remove(new_path)
                os.rename(filepath, new_path)
            return True
        except: return False

    def validate_and_fix_image(self, filepath):
        try:
            if not os.path.exists(filepath): return False
            if os.path.getsize(filepath) < 200:
                os.remove(filepath); return False
            with open(filepath, 'rb') as f: header = f.read(12)
            ext = None; is_webp = False
            if header.startswith(b'\xff\xd8'): ext = '.jpg'
            elif header.startswith(b'\x89PNG\r\n\x1a\n'): ext = '.png'
            elif header.startswith(b'RIFF') and header[8:12] == b'WEBP': ext = '.webp'; is_webp = True
            elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'): ext = '.gif'
            if not ext: os.remove(filepath); return False
            if is_webp:
                try:
                    from PIL import Image
                    with Image.open(filepath) as img: rgb_im = img.convert("RGB")
                    jpg_path = os.path.splitext(filepath)[0] + ".jpg"
                    if filepath != jpg_path: os.remove(filepath)
                    rgb_im.save(jpg_path, "JPEG", quality=95)
                    return True
                except: pass 
            if not filepath.lower().endswith(ext):
                new_path = os.path.splitext(filepath)[0] + ext
                if os.path.exists(new_path): os.remove(new_path)
                os.rename(filepath, new_path)
            return True
        except: return False

    def _dl_m3u8_pure_python(self, m3u8_url, output_file, referer):
        uid = f"{int(time.time()*1000)}_{random.randint(100,999)}"
        tmp_m3u8 = os.path.join(tempfile.gettempdir(), f"v_{uid}.m3u8")
        if not self.run_curl_command(m3u8_url, tmp_m3u8, referer=referer): return False
        with open(tmp_m3u8, 'r', encoding='utf-8') as f: content = f.read()
        os.remove(tmp_m3u8)
        ts_urls, sub_m3u8 = [], None
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if '.m3u8' in line: sub_m3u8 = urljoin(m3u8_url, line); break
                else: ts_urls.append(urljoin(m3u8_url, line))
        if sub_m3u8: return self._dl_m3u8_pure_python(sub_m3u8, output_file, referer)
        if not ts_urls: return False
        ts_files = []
        for idx, ts_url in enumerate(ts_urls):
            ts_path = os.path.join(tempfile.gettempdir(), f"ts_{uid}_{idx:04d}.ts")
            self.safe_log(f"    + Kéo cục dữ liệu Video: [{idx+1}/{len(ts_urls)}] ({int(((idx+1)/len(ts_urls))*100)}%)", overwrite=(idx>0))
            self.run_curl_command(ts_url, ts_path, referer=referer, need_lang=False, is_video=True)
            if self.validate_video_file(ts_path, ".ts"): ts_files.append(ts_path)
        if not ts_files: return False
        self.safe_log("\n    + Đang ghép luồng dữ liệu thô (.ts)... ")
        try:
            with open(output_file, 'wb') as merged:
                for ts_file in ts_files:
                    with open(ts_file, 'rb') as f: shutil.copyfileobj(f, merged)
                    os.remove(ts_file)
            return True
        except: return False

    def dl_core_xchina(self, url, custom_name, start_num, max_img, target_base_dir):
        self.safe_log(f"[*] XCHINA: Bắt đầu dò tìm cấu trúc đa phương tiện...\n")
        m = re.search(r'id-([a-zA-Z0-9]+)', url) or re.search(r'id=([^&]+)', url)
        if not m: self.safe_log("[!] URL không hợp lệ.\n"); return False
        album_id = m.group(1)
        try: start_num, max_img = int(start_num), int(max_img)
        except: start_num, max_img = 1, 59
        
        uid = f"{int(time.time() * 1000)}"
        tmp = os.path.join(tempfile.gettempdir(), f"xc_{uid}.html")
        html = ""
        for _ in range(3):
            self.run_curl_command(url, tmp, referer=url)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                with open(tmp, 'r', encoding='utf-8', errors='ignore') as f: html = f.read()
                if "Cloudflare" not in html: break
            time.sleep(2)
        if os.path.exists(tmp): os.remove(tmp)
        if not html: self.safe_log("[!] Bị chặn truy cập hoặc lỗi Cloudflare.\n"); return False
        
        all_html = html
        domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        max_page = 1
        page_matches = re.findall(r'id-' + re.escape(album_id) + r'(?:/|_|/index_)(\d+)\.html', html)
        if page_matches: max_page = max(max_page, max([int(p) for p in page_matches]))
        if max_page > 1:
            for p in range(2, min(max_page + 1, 50)):
                p_url = f"{domain}/photo/id-{album_id}/{p}.html"
                tmp_p = os.path.join(tempfile.gettempdir(), f"xc_p_{uid}_{p}.html")
                if not self.run_curl_command(p_url, tmp_p, referer=url):
                    self.run_curl_command(f"{domain}/photo/id-{album_id}_{p}.html", tmp_p, referer=url)
                if os.path.exists(tmp_p) and os.path.getsize(tmp_p) > 0:
                    with open(tmp_p, 'r', encoding='utf-8', errors='ignore') as f:
                        p_html = f.read()
                        if "Cloudflare" not in p_html: all_html += p_html
                if os.path.exists(tmp_p): os.remove(tmp_p)
        
        html_clean = all_html.replace('\\/', '/')
        if not custom_name:
            t = re.search(r'<title>(.*?)</title>', html, re.I)
            if t: custom_name = re.sub(r'[<>:"/\\|?*]', '', t.group(1)).strip()
        custom_name = re.sub(r'[\\/*?:"<>|]', "", custom_name or f"Album_{album_id}")
        target_dir = os.path.join(target_base_dir, custom_name)
        os.makedirs(target_dir, exist_ok=True)
        
        download_success = False
        seen_media_ids, unique_videos = set(), []
        raw_m3u8s = re.findall(r'(https?://[^\s"\'<>\[\]{},]+\.m3u8)', html_clean)
        for m_url in raw_m3u8s:
            v_u = m_url.strip('\\')
            if v_u not in seen_media_ids: seen_media_ids.add(v_u); unique_videos.append(v_u)
            
        for m_str in re.finditer(r'["\']([^"\']+\.mp4[^"\']*)["\']', html_clean, re.IGNORECASE):
            v_u = m_str.group(1).strip('\\')
            if v_u not in seen_media_ids: seen_media_ids.add(v_u); unique_videos.append(v_u)

        if unique_videos:
            for v_idx, v_url in enumerate(unique_videos, 1):
                out_mp4 = os.path.join(target_dir, f"{custom_name}_Vid_{v_idx:02d}.mp4")
                if os.path.exists(out_mp4): download_success = True; continue
                if '.mp4' in v_url.lower() and '.m3u8' not in v_url.lower():
                    self.run_curl_command(v_url, out_mp4 + ".tmp", referer=url, is_video=True)
                    if self.validate_video_file(out_mp4 + ".tmp", ".mp4"): download_success = True
                else:
                    if self._dl_m3u8_pure_python(v_url, os.path.join(target_dir, f"{custom_name}_Vid_{v_idx:02d}.ts"), referer=url): download_success = True

        unique_names, found_folder = [], "photos"
        pattern = r'(photos|photos2|photos3|upload|images)/' + re.escape(album_id) + r'/([^/"\'\s>]+?\.(?:jpg|jpeg|png|webp))'
        for m_str in re.finditer(pattern, html_clean, re.IGNORECASE):
            found_folder = m_str.group(1)
            name_no_ext, _ = os.path.splitext(m_str.group(2))
            if name_no_ext.lower() != 'cover' and name_no_ext not in unique_names: unique_names.append(name_no_ext)

        if unique_names:
            valid_b = f"https://img.xchina.io/{found_folder}/{album_id}"
            saved = start_num
            for idx, pure_name in enumerate(unique_names):
                base_path = os.path.join(target_dir, f"{saved:04d}")
                self.safe_log(f"  ➔ Kéo ảnh: [{idx + 1}/{len(unique_names)}] ({int(((idx+1)/len(unique_names))*100)}%)", overwrite=(idx>0))
                tmp_path = base_path + ".tmp"
                if self.run_curl_command(f"{valid_b}/{pure_name}.jpg", tmp_path, referer=url, need_lang=False) and self.validate_and_fix_image(tmp_path): download_success = True
                elif self.run_curl_command(f"{valid_b}/{pure_name}.webp", tmp_path, referer=url, need_lang=False) and self.validate_and_fix_image(tmp_path): download_success = True
                time.sleep(random.uniform(2.0, 4.0)) 
                saved += 1
                
        self.safe_log("\n[✓] HOÀN TẤT TIẾN TRÌNH TẢI!\n\n")
        return download_success

    def task_winrar(self, winrar_exe, target, password, del_opt):
        if not os.path.exists(winrar_exe): self.safe_log("[!] Thư mục cài đặt WinRAR mặc định lỗi.\n"); return
        items = os.listdir(target)
        cmd = [winrar_exe, "a", "-cfg-", "-m0", "-ep1", "-ibck", "-inul", "-x*.bat", "-x*.py"]
        if password: cmd.append(f"-p{password}")
        for item in [i for i in items if os.path.isdir(os.path.join(target, i))]:
            ipath = os.path.join(target, item)
            self.safe_log(f"  ➔ Đóng gói khối: {item} ")
            res = subprocess.run(cmd + [os.path.join(target, f"{item}.cbz"), ipath], stdout=subprocess.PIPE, creationflags=0x08000000)
            if res.returncode in [0, 1] and del_opt: shutil.rmtree(ipath, ignore_errors=True)
        self.safe_log("[✓] HOÀN TẤT TÁC VỤ FILE!\n\n")

    def task_create_folders(self, target, name, vol_str):
        try: vol = int(vol_str)
        except: return
        for i in range(1, vol + 1): os.makedirs(os.path.join(target, f"{name} T{i:02d}"), exist_ok=True)
        self.safe_log(f"[✓] Hoàn tất tạo nhanh {vol} cấu trúc thư mục.\n")

    def task_rename_files(self, target, prefix):
        if not os.path.exists(target): return
        files = sorted([f for f in os.listdir(target) if os.path.isfile(os.path.join(target, f))])
        for idx, f in enumerate(files, 1):
            ext = os.path.splitext(f)[1]
            try: os.rename(os.path.join(target, f), os.path.join(target, f"{prefix}_{idx:04d}{ext}" if prefix else f"{idx:04d}{ext}"))
            except: pass
        self.safe_log(f"[✓] Hoàn thành đồng bộ định dạng chuỗi {len(files)} tệp tin.\n")

# =========================================================================
# GIAO DIỆN PHÂN QUYỀN VÀ KHỞI CHẠY ỨNG DỤNG CHÍNH
# =========================================================================
class AIOPortalApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("⚡ AIO Portal Master Security Panel - Commercial V5.0")
        self.geometry("1300x820")
        self.minsize(1100, 700)
        self.configure(fg_color="#f5f3f2")
        
        self.log_queue = queue.Queue()
        self.engine = CoreEngine(self.log_queue, BASE_DIR)
        
        self.t1_cover_path = ""
        self.t2_cover_base64 = ""
        self.current_edit_id = None
        self.current_user_role = None

        self.build_login_screen()
        self.after(100, self.process_log_queue)

    def process_log_queue(self):
        while not self.log_queue.empty():
            try:
                task = self.log_queue.get_nowait()
                if task["type"] == "log" and hasattr(self, 'live_log_box'):
                    self.live_log_box.configure(state="normal")
                    if task.get("overwrite"):
                        lines = self.live_log_box.get("1.0", tk.END).splitlines()
                        if len(lines) > 1: self.live_log_box.delete(f"{len(lines)-1}.0", tk.END); self.live_log_box.insert(tk.END, "\n")
                    self.live_log_box.insert(tk.END, task["msg"])
                    self.live_log_box.see(tk.END)
                    self.live_log_box.configure(state="disabled")
            except: break
        self.after(100, self.process_log_queue)

    # --- SCREEN: ĐĂNG NHẬP BẢO MẬT ---
    def build_login_screen(self):
        self.login_frame = ctk.CTkFrame(self, width=420, height=460, corner_radius=12, fg_color="#ffffff", border_width=1, border_color="#dadce0")
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.login_frame.pack_propagate(False)

        ctk.CTkLabel(self.login_frame, text="🔒 ĐĂNG NHẬP CONTROL PANEL", font=("Arial", 18, "bold"), text_color="#1a73e8").pack(pady=(45, 30))
        ctk.CTkLabel(self.login_frame, text="Tài khoản người dùng:", font=("Arial", 12, "bold")).pack(anchor="w", padx=45, pady=(5, 5))
        self.ent_user = ctk.CTkEntry(self.login_frame, height=38, placeholder_text="Username...")
        self.ent_user.pack(fill="x", padx=45, pady=(0, 15))

        ctk.CTkLabel(self.login_frame, text="Mật khẩu bảo mật:", font=("Arial", 12, "bold")).pack(anchor="w", padx=45, pady=(5, 5))
        self.ent_pass = ctk.CTkEntry(self.login_frame, height=38, show="*", placeholder_text="Password...")
        self.ent_pass.pack(fill="x", padx=45, pady=(0, 25))
        self.ent_pass.bind("<Return>", lambda e: self.verify_login())

        ctk.CTkButton(self.login_frame, text="XÁC THỰC TRUY CẬP", fg_color="#10b981", hover_color="#0d9a6c", height=42, font=("Arial", 13, "bold"), command=self.verify_login).pack(fill="x", padx=45)

    def verify_login(self):
        u, p = self.ent_user.get().strip(), self.ent_pass.get().strip()
        user_data = db.fetchone("SELECT role FROM app_users WHERE username=? AND password=?", (u, p))
        if user_data:
            self.current_user_role = user_data[0]
            self.login_frame.destroy()
            self.setup_main_workspace()
        else: messagebox.showerror("Lỗi hệ thống", "Xác thực không hợp lệ. Bản quyền hoặc tài khoản chưa kích hoạt!")

    # --- WORKSPACE: KHOANG LÀM VIỆC CHÍNH ---
    def setup_main_workspace(self):
        self.main_tabs = ctk.CTkTabview(self)
        self.main_tabs.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.main_tabs._segmented_button.configure(font=("Arial", 13, "bold"))
        
        self.tab1 = self.main_tabs.add("🚀 1. Downloader")
        self.tab2 = self.main_tabs.add("🛠️ 2. Công Cụ File")
        self.tab3 = self.main_tabs.add("✍️ 3. Studio Code")
        self.tab4 = self.main_tabs.add("🔐 4. Tài Khoản & Bookmark")
        
        if self.current_user_role == 'admin':
            self.tab_admin = self.main_tabs.add("👑 Quản Trị Hệ Thống")
            self.build_tab_admin_users()

        self.build_tab_downloader()
        self.build_tab_filetools()
        self.build_tab_studio()
        self.build_tab_account_bookmark()

    # --- TAB ADMIN: QUẢN TRỊ USER ---
    def build_tab_admin_users(self):
        self.tab_admin.grid_columnconfigure(0, weight=0, minsize=350)
        self.tab_admin.grid_columnconfigure(1, weight=1)
        self.tab_admin.grid_rowconfigure(0, weight=1)
        
        left_p = ctk.CTkFrame(self.tab_admin, fg_color="#f8f9fa", border_width=1, border_color="#dadce0", corner_radius=10)
        left_p.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_p, text="👑 QUẢN TRỊ CẤP PHÁT QUYỀN ACCESS", font=("Arial", 13, "bold"), text_color="#e51661").pack(anchor="w", padx=20, pady=(20, 15))
        ctk.CTkLabel(left_p, text="Tên tài khoản mới:", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
        self.new_u = ctk.CTkEntry(left_p, height=35)
        self.new_u.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(left_p, text="Mật khẩu khởi tạo:", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
        self.new_p = ctk.CTkEntry(left_p, height=35)
        self.new_p.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(left_p, text="Nhóm phân quyền:", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 2))
        self.new_role = ctk.CTkOptionMenu(left_p, values=["user", "admin"], height=35)
        self.new_role.pack(fill="x", padx=20, pady=(0, 25))
        
        ctk.CTkButton(left_p, text="KÍCH HOẠT USER", fg_color="#10b981", height=42, font=("Arial", 12, "bold"), command=self.action_add_app_user).pack(fill="x", padx=20)

        right_p = ctk.CTkFrame(self.tab_admin, fg_color="transparent")
        right_p.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(right_p, text="📋 DANH SÁCH USER HOẠT ĐỘNG", font=("Arial", 13, "bold")).pack(anchor="w", pady=(10, 10))
        self.user_list_frame = ctk.CTkScrollableFrame(right_p, fg_color="transparent")
        self.user_list_frame.pack(fill="both", expand=True)
        self.refresh_app_user_ui()

    def action_add_app_user(self):
        u, p, r = self.new_u.get().strip(), self.new_p.get().strip(), self.new_role.get()
        if not u or not p: return
        try:
            db.execute("INSERT INTO app_users (username, password, role) VALUES (?,?,?)", (u, p, r))
            self.new_u.delete(0, tk.END); self.new_p.delete(0, tk.END); self.refresh_app_user_ui()
        except: messagebox.showerror("Lỗi", "Tên tài khoản này đã tồn tại trên phân vùng!")

    def refresh_app_user_ui(self):
        for w in self.user_list_frame.winfo_children(): w.destroy()
        for r_id, u, p, r in db.fetchall("SELECT id, username, password, role FROM app_users ORDER BY id ASC"):
            card = ctk.CTkFrame(self.user_list_frame, fg_color="#f8f9fa", border_width=1, border_color="#dadce0")
            card.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(card, text=f"{'👑' if r=='admin' else '👤'} {u}", font=("Arial", 13, "bold"), text_color="#dc3545" if r=='admin' else "#1a73e8").pack(side="left", padx=15, pady=8)
            ctk.CTkLabel(card, text=f"Mật khẩu: {p}  |  Quyền hạn: {r.upper()}", font=("Arial", 11)).pack(side="left", padx=10)
            if u != "admin":
                ctk.CTkButton(card, text="Thu Hồi", width=60, height=28, fg_color="#e51661", command=lambda i=r_id: (db.execute("DELETE FROM app_users WHERE id=?", (i,)), self.refresh_app_user_ui())).pack(side="right", padx=15)

    # ================= TAB 1: KHOANG TẢI DỮ LIỆU ĐÃ LƯỢC BỎ =================
    def build_tab_downloader(self):
        self.tab1.grid_columnconfigure(0, weight=0, minsize=320) 
        self.tab1.grid_columnconfigure(1, weight=1)
        self.tab1.grid_rowconfigure(0, weight=1)

        left_pane = ctk.CTkFrame(self.tab1, fg_color="#f8f9fa", border_width=1, border_color="#dadce0", corner_radius=10)
        left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_pane, text="📥 BỘ LỌC TẢI KHỐI ĐA PHƯƠNG TIỆN", font=("Arial", 13, "bold"), text_color="#1a73e8").pack(anchor="w", padx=15, pady=(15, 10))
        
        self.dl_u, self.dl_n, self.dl_d = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.dl_t = tk.StringVar(value="59") # Cố định mặc định 59

        ctk.CTkLabel(left_pane, text="Nguồn định tuyến tải:", font=("Arial", 11, "bold")).pack(anchor="w", padx=15, pady=(5, 2))
        seg = ctk.CTkSegmentedButton(left_pane, values=["XChina.co"])
        seg.pack(fill="x", padx=15, pady=(0, 10))
        seg.set("XChina.co")

        self.dl_dyn_frame = ctk.CTkFrame(left_pane, fg_color="transparent")
        self.dl_dyn_frame.pack(fill="x", padx=15, pady=5)
        
        self.create_entry(self.dl_dyn_frame, "Đường dẫn liên kết (URL):", self.dl_u, expand=True)
        self.create_entry(self.dl_dyn_frame, "Tên đóng gói thư mục (Tùy chọn):", self.dl_n, expand=True)
        self.create_entry(self.dl_dyn_frame, "Thời gian phát hành (Gợi nhớ):", self.dl_d, expand=True)
        
        # Ô Số lượng được neo mặc định 59
        f_t = ctk.CTkFrame(self.dl_dyn_frame, fg_color="transparent")
        f_t.pack(fill="x", pady=4)
        ctk.CTkLabel(f_t, text="Thông số giới hạn tải:", font=("Arial", 11, "bold"), text_color="#656e77").pack(anchor="w")
        ent_t = ctk.CTkEntry(f_t, textvariable=self.dl_t, height=35)
        ent_t.pack(fill="x", pady=(2, 0))
        
        self.btn_action_frame = ctk.CTkFrame(left_pane, fg_color="transparent")
        self.btn_action_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(self.btn_action_frame, text="🚀 NẠP FILE TXT AUTO LUỒNG", fg_color="#f59e0b", hover_color="#d97706", height=40, font=("Arial", 12, "bold"), command=self.import_xchina_txt).pack(fill="x", pady=4)
        ctk.CTkButton(self.btn_action_frame, text="▶ TIẾN HÀNH TẢI TRỰC TIẾP", fg_color="#10b981", hover_color="#0d9a6c", height=42, font=("Arial", 12, "bold"), command=self.action_download_direct).pack(fill="x", pady=4)

        right_pane = ctk.CTkFrame(self.tab1, fg_color="#1e1e1e", corner_radius=10)
        right_pane.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(right_pane, text="🖥️ LIVE SYSTEM CORE LOGS", font=("Arial", 12, "bold"), text_color="#00ff00").pack(anchor="w", padx=15, pady=(15, 5))
        self.live_log_box = ctk.CTkTextbox(right_pane, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#00ff00")
        self.live_log_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.live_log_box.insert(tk.END, "=== LÕI HỆ THỐNG ĐÃ KÍCH HOẠT ===\n")
        self.live_log_box.configure(state="disabled")

    def action_download_direct(self):
        u = self.dl_u.get().strip()
        if not u: return
        n, d, t = self.dl_n.get().strip(), self.dl_d.get().strip(), self.dl_t.get().strip()
        
        pm = re.search(r'(\d+)\s*[pP]', t)
        p_count = pm.group(1) if pm else (re.search(r'^(\d+)', t).group(1) if re.search(r'^(\d+)', t) else "59")
        vm = re.search(r'(\d+)\s*[vV]', t)
        v_count = vm.group(1) if vm else ("1" if "/video/" in u.lower() else "0")
        fn = f"{n} ({d}) [{p_count}P+{v_count}V]" if d else f"{n} [{p_count}P+{v_count}V]"
        fn = re.sub(r'[\\/*?:"<>|]', "", fn)
        
        threading.Thread(target=self.engine.dl_core_xchina, args=(u, fn, 1, str(int(p_count)+int(v_count)), os.path.join(BASE_DIR, "Downloads")), daemon=True).start()
        self.dl_u.set(""); self.dl_n.set(""); self.dl_d.set("")
        self.dl_t.set("59") # Reset về 59

    def import_xchina_txt(self):
        filepath = filedialog.askopenfilename(title="Chọn file TXT XChina", filetypes=[("Text Files", "*.txt")])
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
            blocks = content.split("=====================================")
            tasks = []
            for b in blocks:
                if not b.strip(): continue
                name_match = re.search(r'📌 Tên (?:Album|Mục)\s*:\s*(.+)', b)
                model_match = re.search(r'📌 Tên (?:Diễn viên|Model)\s*:\s*(.+)', b) or re.search(r'👤 Model\s*:\s*(.+)', b)
                date_match = re.search(r'📅 Note/Ngày\s*:\s*(.+)', b)
                count_match = re.search(r'🖼️ (?:Số lượng|Thông số)\s*:\s*(.+)', b)
                link_match = re.search(r'🔗 Link\s*:\s*(https?://[^\s"\'<>]+)', b)
                
                if name_match and link_match:
                    raw_name = name_match.group(1).strip()
                    model_name = model_match.group(1).strip() if model_match else ""
                    date_str = date_match.group(1).strip() if date_match else ""
                    if date_str.upper() == "N/A": date_str = ""
                    d_extract = re.search(r'\((.*?)\)', date_str)
                    if d_extract: date_str = d_extract.group(1)
                    
                    u = link_match.group(1).strip()
                    base_name = model_name if (model_name and model_name.upper() != "N/A") else raw_name
                    t_raw = count_match.group(1).strip() if count_match else "59"
                    
                    pm = re.search(r'(\d+)\s*[pP]', t_raw)
                    p_count = pm.group(1) if pm else (re.search(r'^(\d+)', t_raw).group(1) if re.search(r'^(\d+)', t_raw) else "59")
                    vm = re.search(r'(\d+)\s*[vV]', t_raw)
                    v_count = vm.group(1) if vm else ("1" if "/video/" in u.lower() else "0")
                    
                    fn = f"{base_name} ({date_str}) [{p_count}P+{v_count}V]" if date_str else f"{base_name} [{p_count}P+{v_count}V]"
                    fn = re.sub(r'[\\/*?:"<>|]', "", fn)
                    tasks.append((u, fn, str(int(p_count)+int(v_count))))

            if tasks: 
                # Chạy cơ chế Queued (Hàng đợi tuần tự) chống spam luồng
                threading.Thread(target=self._dl_xchina_multi_worker, args=(tasks,), daemon=True).start()
                messagebox.showinfo("Thành công", f"Đã nạp {len(tasks)} bộ Album vào tiến trình tải tự động.")
            else: messagebox.showwarning("Cảnh báo", "Không tìm thấy URL hợp lệ trong tệp tin TXT này.")
        except Exception as e: messagebox.showerror("Lỗi hệ thống", f"Không thể xử lý định dạng tệp: {e}")

    def _dl_xchina_multi_worker(self, tasks):
        target_dir = os.path.join(BASE_DIR, "Downloads")
        os.makedirs(target_dir, exist_ok=True)
        self.engine.safe_log(f"\n--- BẮT ĐẦU CHẾ ĐỘ AUTO NẠP TXT ({len(tasks)} BỘ) ---\n")
        for idx, (u, fn, t) in enumerate(tasks, 1):
            self.engine.safe_log(f"\n[TIẾN TRÌNH LÕI {idx}/{len(tasks)}] Đang kết nối Data: {fn}\n")
            self.engine.dl_core_xchina(u, fn, 1, t, target_dir)
            time.sleep(3) # Cố định nghỉ 3s giữa các Album chống khóa IP
        self.engine.safe_log("\n[✓] HOÀN TẤT TOÀN BỘ TIẾN TRÌNH TXT!\n\n")

    # ================= TAB 2: CÔNG CỤ FILE =================
    def build_tab_filetools(self):
        container = ctk.CTkFrame(self.tab2, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=50, pady=20)
        
        self.tl_rar_tgt = tk.StringVar(value="C:\\")
        self.tl_rar_pass = tk.StringVar()
        self.tl_rar_del = tk.BooleanVar(value=False)
        self.tl_cf_tgt = tk.StringVar()
        self.tl_cf_name = tk.StringVar()
        self.tl_cf_vol = tk.StringVar(value="5")
        self.tl_ren_tgt = tk.StringVar()
        self.tl_ren_pre = tk.StringVar()

        ctk.CTkLabel(container, text="🛠️ BỘ CÔNG CỤ QUẢN LÝ TỆP TIN HỆ THỐNG", font=("Arial", 15, "bold"), text_color="#1a73e8").pack(pady=(0, 20))
        self.tool_selector = ctk.CTkSegmentedButton(container, values=["Nén WinRAR", "Tạo Thư Mục", "Đổi Tên File"], command=self.update_tool_ui)
        self.tool_selector.pack(fill="x", pady=(0, 20))
        self.tool_selector.set("Nén WinRAR")
        
        self.tool_container = ctk.CTkFrame(container, fg_color="#ffffff", border_width=1, border_color="#dadce0", corner_radius=10)
        self.tool_container.pack(fill="both", expand=True)
        self.update_tool_ui("Nén WinRAR")

    def update_tool_ui(self, choice):
        for w in self.tool_container.winfo_children(): w.destroy()
        inner_pad = ctk.CTkFrame(self.tool_container, fg_color="transparent")
        inner_pad.pack(expand=True, fill="both", padx=40, pady=30)
            
        if choice == "Nén WinRAR":
            cmd_rar = lambda: threading.Thread(target=self.engine.task_winrar, args=("C:\\Program Files\\WinRAR\\WinRAR.exe", self.tl_rar_tgt.get(), self.tl_rar_pass.get(), self.tl_rar_del.get()), daemon=True).start()
            self.create_entry(inner_pad, "Đường dẫn phân vùng nén:", self.tl_rar_tgt)
            self.create_entry(inner_pad, "Mật khẩu mã hóa khối (Tùy chọn):", self.tl_rar_pass)
            ctk.CTkCheckBox(inner_pad, text="Xóa thư mục dữ liệu thô sau khi xuất CBZ thành công", variable=self.tl_rar_del).pack(anchor="w", pady=15)
            ctk.CTkButton(inner_pad, text="▶ KÍCH HOẠT TIẾN TRÌNH NÉN", fg_color="#10b981", height=42, font=("Arial", 12, "bold"), command=cmd_rar).pack(fill="x")
                          
        elif choice == "Tạo Thư Mục":
            cmd_cf = lambda: threading.Thread(target=self.engine.task_create_folders, args=(self.tl_cf_tgt.get(), self.tl_cf_name.get(), self.tl_cf_vol.get()), daemon=True).start()
            self.create_entry(inner_pad, "Thư mục đích cấu trúc:", self.tl_cf_tgt)
            self.create_entry(inner_pad, "Ký hiệu đầu mục (Prefix):", self.tl_cf_name)
            self.create_entry(inner_pad, "Giới hạn chuỗi lặp:", self.tl_cf_vol)
            ctk.CTkButton(inner_pad, text="▶ KHỞI TẠO KHỐI", fg_color="#10b981", height=42, font=("Arial", 12, "bold"), command=cmd_cf).pack(fill="x", pady=15)
            
        elif choice == "Đổi Tên File":
            cmd_ren = lambda: threading.Thread(target=self.engine.task_rename_files, args=(self.tl_ren_tgt.get(), self.tl_ren_pre.get()), daemon=True).start()
            self.create_entry(inner_pad, "Thư mục mục tiêu xử lý:", self.tl_ren_tgt)
            self.create_entry(inner_pad, "Tiền tố chuỗi số chuẩn (Bỏ trống = 0001):", self.tl_ren_pre)
            ctk.CTkButton(inner_pad, text="▶ ĐỒNG BỘ ĐỊNH DẠNG CHUỖI", fg_color="#10b981", height=42, font=("Arial", 12, "bold"), command=cmd_ren).pack(fill="x", pady=15)

    # ================= TAB 3: STUDIO SCRIPT GENERATOR =================
    def build_tab_studio(self):
        top_bar = ctk.CTkFrame(self.tab3, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(top_bar, text="📌 CÔNG CỤ PHÁT TRIỂN NỘI DUNG SOẠN THẢO:", font=("Arial", 12, "bold"), text_color="#1a73e8").pack(side="left", padx=(0, 10))
        self.studio_selector = ctk.CTkOptionMenu(top_bar, values=["📝 1. Blogspot HTML", "⚡ 2. Trình Đọc Truyện CBZ"], width=320, command=self.switch_studio_mode)
        self.studio_selector.pack(side="left")
        self.studio_container = ctk.CTkFrame(self.tab3, fg_color="transparent")
        self.studio_container.pack(fill="both", expand=True)
        self.switch_studio_mode("📝 1. Blogspot HTML")

    def switch_studio_mode(self, choice):
        for w in self.studio_container.winfo_children(): w.destroy()
        self.studio_container.grid_columnconfigure(0, weight=0, minsize=380)
        self.studio_container.grid_columnconfigure(1, weight=1)
        self.studio_container.grid_rowconfigure(0, weight=1)
        
        left_f = ctk.CTkFrame(self.studio_container, fg_color="#f8f9fa", border_width=1, border_color="#dadce0", corner_radius=10)
        left_f.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_f = ctk.CTkFrame(self.studio_container, fg_color="#1e1e1e", corner_radius=10)
        right_f.grid(row=0, column=1, sticky="nsew")

        if "Blogspot" in choice:
            ctk.CTkLabel(left_f, text="1. Chọn ảnh bìa đại diện:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
            btn_img = ctk.CTkButton(left_f, text="📂 Duyệt file ảnh từ PC", fg_color="#f39c12", hover_color="#e08e0b", height=35, command=lambda: self.t1_select_img(btn_img))
            btn_img.pack(fill="x", padx=15, pady=(0, 10))
            
            ctk.CTkLabel(left_f, text="2. Tiêu đề bài viết mục mục:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(5, 5))
            ent_title = ctk.CTkEntry(left_f, height=35)
            ent_title.pack(fill="x", padx=15, pady=(0, 10))
            
            ctk.CTkLabel(left_f, text="3. Thân bài HTML thô:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(5, 5))
            txt_content = ctk.CTkTextbox(left_f, height=140)
            txt_content.pack(fill="both", expand=True, padx=15, pady=(0, 10))
            
            ctk.CTkLabel(left_f, text="4. Link chi tiết điều hướng:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(5, 5))
            ent_link = ctk.CTkEntry(left_f, height=35)
            ent_link.pack(fill="x", padx=15, pady=(0, 15))
            
            txt_out = ctk.CTkTextbox(right_f, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#00ff00")
            txt_out.pack(fill="both", expand=True, padx=15, pady=15)
            
            ctk.CTkButton(left_f, text="🚀 XUẤT CODE CONTAINER HTML", fg_color="#10b981", height=42, font=("Arial", 12, "bold"), command=lambda: self.t1_generate(ent_title.get(), txt_content.get("1.0", tk.END), ent_link.get(), txt_out)).pack(fill="x", padx=15, pady=(0, 10))
            ctk.CTkButton(left_f, text="📋 CHÉP VÀ LÀM SẠCH KHUNG", fg_color="#008CBA", height=40, command=lambda: self.copy_to_clip(txt_out.get("1.0", tk.END), [ent_title, ent_link], [txt_content, txt_out])).pack(fill="x", padx=15, pady=(0, 15))
        else:
            ctk.CTkLabel(left_f, text="1. Khóa API Google Drive (Cố định):", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
            ent_api = ctk.CTkEntry(left_f, height=35); ent_api.pack(fill="x", padx=15, pady=(0, 10)); ent_api.insert(0, FIXED_GOOGLE_API_KEY); ent_api.configure(state="readonly")
            
            ctk.CTkLabel(left_f, text="2. Điền mã ID hoặc Link Drive:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(5, 5))
            ent_link = ctk.CTkEntry(left_f, height=35); ent_link.pack(fill="x", padx=15, pady=(0, 10)); ent_link.bind("<KeyRelease>", lambda e: self.auto_extract_id(ent_link))
            
            ctk.CTkLabel(left_f, text="3. Ảnh Cover hiển thị ẩn danh:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(5, 5))
            btn_cov = ctk.CTkButton(left_f, text="📂 Chọn tệp làm nền", fg_color="#f39c12", height=35, command=lambda: self.t2_select_cov(btn_cov)); btn_cov.pack(fill="x", padx=15, pady=(0, 5))
            ent_cov_link = ctk.CTkEntry(left_f, placeholder_text="Hoặc dán Link URL trực tiếp...", height=35); ent_cov_link.pack(fill="x", padx=15, pady=(0, 15))
            
            txt_out = ctk.CTkTextbox(right_f, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#00ff00"); txt_out.pack(fill="both", expand=True, padx=15, pady=15)
            
            ctk.CTkFrame(left_f, fg_color="transparent").pack(fill="both", expand=True)
            ctk.CTkButton(left_f, text="🚀 BIÊN DỊCH MÃ NHÚNG CBZ", fg_color="#10b981", height=42, font=("Arial", 12, "bold"), command=lambda: self.t2_generate(ent_link.get(), ent_cov_link.get(), txt_out)).pack(fill="x", padx=15, pady=(0, 10))
            ctk.CTkButton(left_f, text="📋 CHÉP KHỐI", fg_color="#e91e63", height=40, command=lambda: self.copy_to_clip(txt_out.get("1.0", tk.END), [ent_link, ent_cov_link], [txt_out])).pack(fill="x", padx=15, pady=(0, 15))

    def t1_select_img(self, btn):
        fp = filedialog.askopenfilename(filetypes=[("Image", "*.jpg *.png *.webp *.gif")])
        if fp: self.t1_cover_path = fp; btn.configure(text=f"✅ {os.path.basename(fp)[:15]}...")

    def t1_generate(self, title, content, link, txt_out):
        if not title.strip(): return
        body_m = re.search(r'<body[^>]*>(.*?)</body>', content, re.IGNORECASE | re.DOTALL)
        cln = body_m.group(1) if body_m else content
        cln = re.sub(r'background(?:-color)?\s*:\s*[^;"\'>]+;?', '', cln, flags=re.IGNORECASE)
        img_tag = "<p><i>(Không nạp ảnh)</i></p>"
        if self.t1_cover_path and os.path.exists(self.t1_cover_path):
            with open(self.t1_cover_path, "rb") as f: b64 = base64.b64encode(f.read()).decode('utf-8')
            img_tag = f'<img src="data:image/{self.t1_cover_path.split(".")[-1].lower()};base64,{b64}" style="max-width: 100%; border-radius: 6px;" alt="{title}" />'
        res = f'<div style="display: flex; flex-wrap: wrap; gap: 20px; font-family: Arial;"><div style="flex: 1; min-width: 250px;">{img_tag}</div><div style="flex: 2; min-width: 300px;"><h2 style="color: #333; margin-top: 0;">{title}</h2><div style="color: #222; margin-bottom: 20px;">{cln}</div><div style="margin-top: 15px;"><a href="{link}" target="_blank" style="text-decoration: none; display: inline-flex; background-color: #007bff; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold;">Truy cập ngay</a></div></div></div>'
        txt_out.delete("1.0", tk.END); txt_out.insert("1.0", res.strip())

    def auto_extract_id(self, ent):
        val = ent.get().strip()
        match = re.search(r'(?:id=|/d/)([\w-]+)', val)
        if match and match.group(1) != val: ent.delete(0, tk.END); ent.insert(0, match.group(1))

    def t2_select_cov(self, btn):
        fp = filedialog.askopenfilename(filetypes=[("Image", "*.jpg *.png *.webp *.gif")])
        if fp:
            with open(fp, "rb") as f: self.t2_cover_base64 = f"data:image/{fp.split('.')[-1].lower()};base64,{base64.b64encode(f.read()).decode('utf-8')}"
            btn.configure(text=f"✅ {os.path.basename(fp)[:10]}...")

    def t2_generate(self, file_id, cov_link, txt_out):
        if not file_id.strip(): return
        s_id = re.sub(r'[^a-zA-Z0-9]', 'X', file_id.strip())
        fc = cov_link.strip() if cov_link.strip() else self.t2_cover_base64
        cb = f'\n<div style="display: none !important;"><img src="{fc}" /></div>\n' if fc else ""
        core = f'''
<script src="https://unpkg.com/@zip.js/zip.js/dist/zip.min.js"></script>
<div id="setup-box-{s_id}" style="background: rgb(26, 26, 26); border-radius: 10px; color: white; font-family: sans-serif; margin-bottom: 20px; padding: 20px; text-align: center;">
    <input id="cbz-password-{s_id}" placeholder="Mật khẩu mã hóa tệp..." onkeypress="if(event.key === 'Enter') fetchFromGoogleAPI_{s_id}();" style="color: black; border-radius: 5px; max-width: 250px; padding: 10px; width: 60%;" type="password" /><br />
    <button onclick="fetchFromGoogleAPI_{s_id}();" style="background-color: #e91e63; border-radius: 5px; border: none; color: white; cursor: pointer; font-size: 16px; font-weight: bold; padding: 12px 25px; margin-top: 10px;">📖 Mở File Truyện</button>
</div>
<div id="status-box-{s_id}" style="color: #4caf50; font-weight: bold; text-align: center;"></div>
<div id="comic-viewer-{s_id}" style="display: none; background: rgb(44, 44, 44); padding: 10px; text-align: center;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
        <button onclick="prevPage_{s_id}();" style="padding: 8px 15px; cursor: pointer; background: #3498db; border: none; color: white;">◀ Trước</button>
        <span id="page-counter-{s_id}" style="color: #f1c40f; font-weight: bold;">1 / ?</span>
        <button onclick="nextPage_{s_id}();" style="padding: 8px 15px; cursor: pointer; background: #3498db; border: none; color: white;">Sau ▶</button>
    </div>
    <div style="position: relative; height: 85vh; display: flex; justify-content: center; background: #000;">
        <div onclick="prevPage_{s_id}();" style="position: absolute; left: 0; width: 50%; height: 100%; cursor: w-resize;"></div>
        <div onclick="nextPage_{s_id}();" style="position: absolute; right: 0; width: 50%; height: 100%; cursor: e-resize;"></div>
        <img id="manga-page-{s_id}" src="" style="max-height: 100%; max-width: 100%; object-fit: contain;" />
    </div>
</div>
<script>
    const API_KEY_{s_id}='{FIXED_GOOGLE_API_KEY}', FID_{s_id}='{file_id.strip()}'; let blbs_{s_id}=[], cIdx_{s_id}=0;
    async function fetchFromGoogleAPI_{s_id}() {{
        document.getElementById('status-box-{s_id}').innerText='Đang kết nối Cloud giải nén...'; 
        try {{ 
            const r=await fetch(`https://www.googleapis.com/drive/v3/files/${{FID_{s_id}}}?alt=media&key=${{API_KEY_{s_id}}}`); const b=await r.blob(); 
            const z=new zip.ZipReader(new zip.BlobReader(b), document.getElementById('cbz-password-{s_id}').value ? {{password:document.getElementById('cbz-password-{s_id}').value}} : {{}}); 
            const e=await z.getEntries(); const ie=e.filter(x=>!x.directory&&x.filename.match(/\\.(jpg|png|webp|gif)$/i)).sort((a,b)=>a.filename.localeCompare(b.filename,undefined,{{numeric:true}})); 
            for(let x of ie) blbs_{s_id}.push(URL.createObjectURL(await x.getData(new zip.BlobWriter()))); await z.close(); 
            document.getElementById('setup-box-{s_id}').style.display='none'; document.getElementById('comic-viewer-{s_id}').style.display='block'; rP_{s_id}(); 
            document.addEventListener('keydown', ev=>{{ if(document.getElementById('comic-viewer-{s_id}').style.display==='block'){{ if(ev.key==='ArrowRight') nextPage_{s_id}(); if(ev.key==='ArrowLeft') prevPage_{s_id}(); }} }}); document.getElementById('status-box-{s_id}').innerText=''; 
        }} catch(err) {{ document.getElementById('status-box-{s_id}').innerText='Lỗi xác thực khóa tệp: ' + err.message; }} 
    }}
    function rP_{s_id}() {{ if(!blbs_{s_id}.length)return; document.getElementById('manga-page-{s_id}').src=blbs_{s_id}[cIdx_{s_id}]; document.getElementById('page-counter-{s_id}').innerText=(cIdx_{s_id}+1)+' / '+blbs_{s_id}.length; }}
    function prevPage_{s_id}() {{ if(cIdx_{s_id}>0) {{ cIdx_{s_id}--; rP_{s_id}(); }} }}
    function nextPage_{s_id}() {{ if(cIdx_{s_id}<blbs_{s_id}.length-1) {{ cIdx_{s_id}++; rP_{s_id}(); }} }}
</script>
'''
        txt_out.delete("1.0", tk.END); txt_out.insert("1.0", (cb + core).strip())

    def copy_to_clip(self, text, ent, txt):
        if not text.strip(): return
        self.clipboard_clear(); self.clipboard_append(text.strip())
        for e in ent: e.delete(0, tk.END)
        for t in txt: t.delete("1.0", tk.END)
        messagebox.showinfo("OK", "Đã lưu khối mã nhúng hệ thống!")

    # ================= TAB 4: QUẢN LÝ TÀI KHOẢN (DB) & BOOKMARK (DB) THEO YÊU CẦU =================
    def build_tab_account_bookmark(self):
        self.subtabs_acc_bm = ctk.CTkTabview(self.tab4)
        self.subtabs_acc_bm.pack(fill="both", expand=True)
        self.subtabs_acc_bm._segmented_button.configure(font=("Arial", 13, "bold"))
        
        st_acc = self.subtabs_acc_bm.add("🪪 Quản Lý Tài Khoản")
        st_bm = self.subtabs_acc_bm.add("📌 Bookmark Liên Kết")

        # --- GIAO DIỆN QUẢN LÝ TÀI KHOẢN (Chuẩn theo ảnh chụp) ---
        st_acc.grid_columnconfigure(0, weight=0, minsize=260)
        st_acc.grid_columnconfigure(1, weight=1)
        st_acc.grid_rowconfigure(0, weight=1)
        
        left_c = ctk.CTkFrame(st_acc, fg_color="#f8f9fa", border_width=1, border_color="#dadce0", corner_radius=8)
        left_c.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_c.grid_propagate(False)
        
        ctk.CTkLabel(left_c, text="🗂️ NHÓM TÀI KHOẢN", font=("Arial", 13, "bold")).pack(anchor="w", padx=15, pady=(15, 10))
        
        self.cat_scroll = ctk.CTkScrollableFrame(left_c, fg_color="transparent")
        self.cat_scroll.pack(fill="both", expand=True, padx=5)
        
        row_new_cat = ctk.CTkFrame(left_c, fg_color="transparent")
        row_new_cat.pack(fill="x", padx=10, pady=10)
        self.ent_new_cat = ctk.CTkEntry(row_new_cat, placeholder_text="Tên nhóm mới...", height=35)
        self.ent_new_cat.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row_new_cat, text="➕", width=40, height=35, command=self.add_category).pack(side="right", padx=(5,0))

        right_c = ctk.CTkFrame(st_acc, fg_color="transparent")
        right_c.grid(row=0, column=1, sticky="nsew")
        self.lbl_current_cat = ctk.CTkLabel(right_c, text="📋 Nhóm: Chung", font=("Arial", 14, "bold"))
        self.lbl_current_cat.pack(anchor="w", pady=(0, 10))
        
        form_f = ctk.CTkFrame(right_c, fg_color="#ffffff", border_width=1, border_color="#dadce0", corner_radius=8)
        form_f.pack(fill="x", pady=(0, 10))
        self.lbl_form_title = ctk.CTkLabel(form_f, text="➕ THÊM TÀI KHOẢN", font=("Arial", 12, "bold"), text_color="#10b981")
        self.lbl_form_title.pack(anchor="w", padx=15, pady=(10, 5))
        
        r_f1 = ctk.CTkFrame(form_f, fg_color="transparent")
        r_f1.pack(fill="x", padx=15, pady=3)
        self.acc_site = ctk.CTkEntry(r_f1, placeholder_text="Website...", height=32)
        self.acc_site.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.acc_user = ctk.CTkEntry(r_f1, placeholder_text="Username...", height=32)
        self.acc_user.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        r_f2 = ctk.CTkFrame(form_f, fg_color="transparent")
        r_f2.pack(fill="x", padx=15, pady=3)
        self.acc_pass = ctk.CTkEntry(r_f2, placeholder_text="Password...", height=32)
        self.acc_pass.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.acc_mail = ctk.CTkEntry(r_f2, placeholder_text="Email...", height=32)
        self.acc_mail.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        r_f3 = ctk.CTkFrame(form_f, fg_color="transparent")
        r_f3.pack(fill="x", padx=15, pady=(3, 10))
        self.acc_note = ctk.CTkEntry(r_f3, placeholder_text="Note...", height=32)
        self.acc_note.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.btn_save_acc = ctk.CTkButton(r_f3, text="💾 THÊM MỚI", fg_color="#10b981", width=120, height=32, command=self.save_account)
        self.btn_save_acc.pack(side="right")
        self.btn_cancel_edit = ctk.CTkButton(r_f3, text="❌ HỦY", fg_color="#e51661", width=60, height=32, command=self.clear_acc_form)

        self.acc_list_scroll = ctk.CTkScrollableFrame(right_c, fg_color="transparent")
        self.acc_list_scroll.pack(fill="both", expand=True)
        self.selected_category = "Chung"
        self.refresh_account_ui()

        # --- GIAO DIỆN BOOKMARK (Chuẩn V168) ---
        bm_top = ctk.CTkFrame(st_bm, fg_color="#ffffff", border_width=1, border_color="#dadce0", corner_radius=8)
        bm_top.pack(fill="x", padx=10, pady=(5, 10))
        
        r = ctk.CTkFrame(bm_top, fg_color="transparent")
        r.pack(fill="x", padx=15, pady=15)
        
        self.bm_n, self.bm_u = tk.StringVar(), tk.StringVar()
        cmd_add = lambda: self.add_db_list("bookmarks", ["name", "url"], [self.bm_n, self.bm_u], self.bm_list_frame, self.render_bm_item)
        
        f1 = ctk.CTkFrame(r, fg_color="transparent")
        f1.pack(side="left", fill="x", expand=True, padx=(0, 15))
        ctk.CTkLabel(f1, text="Tên Bookmark", font=("Arial", 11, "bold"), text_color="#656e77").pack(anchor="w")
        ent_n = ctk.CTkEntry(f1, textvariable=self.bm_n, height=35)
        ent_n.pack(fill="x", pady=(2,0))
        
        f2 = ctk.CTkFrame(r, fg_color="transparent")
        f2.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f2, text="URL (Đường dẫn liên kết)", font=("Arial", 11, "bold"), text_color="#656e77").pack(anchor="w")
        ent_u = ctk.CTkEntry(f2, textvariable=self.bm_u, height=35)
        ent_u.pack(fill="x", pady=(2,0))
        
        ent_n.bind("<Return>", lambda e: cmd_add())
        ent_u.bind("<Return>", lambda e: cmd_add())

        ctk.CTkButton(bm_top, text="➕ THÊM BOOKMARK", fg_color="#3740ff", height=35, font=("Arial", 12, "bold"), command=cmd_add).pack(anchor="w", padx=15, pady=(0,15))
        
        self.bm_list_frame = ctk.CTkScrollableFrame(st_bm, fg_color="transparent")
        self.bm_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.load_db_list("bookmarks", self.bm_list_frame, self.render_bm_item)

    # --- HÀM XỬ LÝ LOGIC QUẢN LÝ TÀI KHOẢN (THEO NHÓM ĐỘNG DB) ---
    def refresh_account_ui(self):
        for w in self.cat_scroll.winfo_children(): w.destroy()
        cats = [r[0] for r in db.fetchall("SELECT DISTINCT category FROM accounts ORDER BY category ASC")]
        if "Chung" not in cats: cats.insert(0, "Chung")
        for cat in cats:
            ctk.CTkButton(self.cat_scroll, text=f"🗂️ {cat}", fg_color="#3740ff" if cat == self.selected_category else "transparent", text_color="#fff" if cat == self.selected_category else "#333", anchor="w", height=38, command=lambda c=cat: self.select_cat(c)).pack(fill="x", pady=2)
            
        self.lbl_current_cat.configure(text=f"📋 Nhóm: {self.selected_category}")
        for w in self.acc_list_scroll.winfo_children(): w.destroy()
        rows = db.fetchall("SELECT id, site, username, password, email, note FROM accounts WHERE category=? ORDER BY id DESC", (self.selected_category,))
        if not rows: return
        
        self.account_checkboxes = [] 
        for r_id, site, user, passwd, mail, note in rows:
            card = ctk.CTkFrame(self.acc_list_scroll, fg_color="#ffffff", border_width=1, border_color="#dadce0", corner_radius=8)
            card.pack(fill="x", pady=4)
            chk_var = tk.IntVar()
            chk = ctk.CTkCheckBox(card, text="", width=24, variable=chk_var)
            chk.configure(command=lambda c=chk, cv=chk_var, i=r_id, s=site, u=user, p=passwd, m=mail, n=note: self.toggle_edit_mode(c, cv, i, s, u, p, m, n))
            chk.pack(side="left", padx=(15, 0))
            self.account_checkboxes.append(chk)
            
            inf = ctk.CTkFrame(card, fg_color="transparent")
            inf.pack(side="left", fill="both", expand=True, padx=(10, 15), pady=10)
            ctk.CTkLabel(inf, text=f"🌐 {site}", font=("Arial", 13, "bold"), text_color="#1a73e8").pack(anchor="w")
            
            safe_pass = passwd or ""
            ctk.CTkLabel(inf, text=f"👤 {user}   |   🔑 {'*' * len(safe_pass)}", font=("Arial", 12)).pack(anchor="w", pady=(2, 0))
            
            btn_f = ctk.CTkFrame(card, fg_color="transparent")
            btn_f.pack(side="right", padx=15, pady=10)
            ctk.CTkButton(btn_f, text="🔍", width=40, height=32, command=lambda s=site, u=user, p=passwd, m=mail, n=note: self.open_details_modal(s, u, p, m, n)).pack(side="left", padx=(0, 5))
            ctk.CTkButton(btn_f, text="❌", width=40, height=32, fg_color="#e51661", command=lambda i=r_id: (db.execute("DELETE FROM accounts WHERE id=?", (i,)), self.refresh_account_ui())).pack(side="left")

    def toggle_edit_mode(self, chk_obj, chk_var, r_id, site, user, passwd, mail, note):
        if chk_var.get() == 1:
            for c in self.account_checkboxes:
                if c != chk_obj: c.deselect()
            self.current_edit_id = r_id
            for e in [self.acc_site, self.acc_user, self.acc_pass, self.acc_mail, self.acc_note]: e.delete(0, tk.END)
            self.acc_site.insert(0, site); self.acc_user.insert(0, user); self.acc_pass.insert(0, passwd or ""); self.acc_mail.insert(0, mail or ""); self.acc_note.insert(0, note or "")
            self.btn_save_acc.configure(text="💾 CẬP NHẬT", fg_color="#f39c12")
            self.lbl_form_title.configure(text="✏️ ĐANG SỬA TÀI KHOẢN", text_color="#f39c12")
            self.btn_cancel_edit.pack(side="right", padx=(0, 5))
        else: self.clear_acc_form()

    def clear_acc_form(self):
        self.current_edit_id = None
        for e in [self.acc_site, self.acc_user, self.acc_pass, self.acc_mail, self.acc_note]: e.delete(0, tk.END)
        self.btn_save_acc.configure(text="💾 THÊM MỚI", fg_color="#10b981")
        self.lbl_form_title.configure(text="➕ THÊM TÀI KHOẢN MỚI", text_color="#10b981")
        self.btn_cancel_edit.pack_forget()
        if hasattr(self, "account_checkboxes"):
            for chk in self.account_checkboxes: chk.deselect()

    def select_cat(self, cat): self.selected_category = cat; self.clear_acc_form(); self.refresh_account_ui()
    
    def add_category(self):
        if self.ent_new_cat.get().strip(): 
            db.execute("INSERT INTO accounts (category, site, username, password, email, note) VALUES (?,?,?,?,?,?)", (self.ent_new_cat.get().strip(), "Mẫu", "user", "pass", "", ""))
            self.selected_category = self.ent_new_cat.get().strip(); self.ent_new_cat.delete(0, tk.END); self.refresh_account_ui()

    def save_account(self):
        s, u, p = self.acc_site.get().strip(), self.acc_user.get().strip(), self.acc_pass.get().strip()
        if not s or not u or not p: return messagebox.showwarning("Cảnh báo", "Nhập đủ Site, User, Pass!")
        m, n = self.acc_mail.get().strip(), self.acc_note.get().strip()
        if self.current_edit_id: db.execute("UPDATE accounts SET site=?, username=?, password=?, email=?, note=? WHERE id=?", (s, u, p, m, n, self.current_edit_id))
        else: db.execute("INSERT INTO accounts (category, site, username, password, email, note) VALUES (?,?,?,?,?,?)", (self.selected_category, s, u, p, m, n))
        self.clear_acc_form(); self.refresh_account_ui()

    def open_details_modal(self, s, u, p, m, n):
        dlg = ctk.CTkToplevel(self); dlg.title(f"🪪 Chi Tiết: {s}"); dlg.geometry("450x380"); dlg.grab_set()
        def mk(txt, val):
            r = ctk.CTkFrame(dlg, fg_color="transparent"); r.pack(fill="x", padx=20, pady=8)
            ctk.CTkLabel(r, text=txt, width=80, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
            e = ctk.CTkEntry(r, height=32); e.pack(side="left", fill="x", expand=True, padx=(5, 10)); e.insert(0, val or ""); e.configure(state="readonly")
            ctk.CTkButton(r, text="Copy", width=60, height=32, command=lambda v=val: (self.clipboard_clear(), self.clipboard_append(v or ""))).pack(side="right")
        mk("Website:", s); mk("User:", u); mk("Pass:", p); mk("Email:", m); mk("Ghi chú:", n)

    # --- HÀM LOGIC BOOKMARK (TỪ V168) ---
    def load_db_list(self, table, frame, render_func):
        for w in frame.winfo_children(): w.destroy()
        for row in db.fetchall(f"SELECT * FROM {table} ORDER BY id DESC"): render_func(frame, row)

    def add_db_list(self, table, cols, vars_list, frame, render_func):
        vals = [v.get().strip() for v in vars_list]
        if not any(vals): return
        q = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})"
        db.execute(q, vals)
        for v in vars_list: v.set("")
        self.load_db_list(table, frame, render_func)

    def del_db_list(self, table, r_id, frame, render_func):
        db.execute(f"DELETE FROM {table} WHERE id=?", (r_id,))
        self.load_db_list(table, frame, render_func)

    def render_bm_item(self, f, r):
        c = ctk.CTkFrame(f, fg_color="#ffffff", border_width=1); c.pack(fill="x", pady=2)
        ctk.CTkLabel(c, text=f"🔖 {r[2]} ({r[1]})", font=("Arial", 12, "bold"), text_color="#1a73e8").pack(side="left", padx=15, pady=8)
        ctk.CTkButton(c, text="❌ Xóa", width=40, height=28, fg_color="#e51661", command=lambda: self.del_db_list("bookmarks", r[0], f, self.render_bm_item)).pack(side="right", padx=10)
        ctk.CTkButton(c, text="Mở Link", width=60, height=28, command=lambda: webbrowser.open(r[1])).pack(side="right")

    def create_entry(self, parent, label, var, expand=True):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=4)
        ctk.CTkLabel(f, text=label, font=("Arial", 11, "bold"), text_color="#656e77").pack(anchor="w")
        ent = ctk.CTkEntry(f, textvariable=var, height=35)
        ent.pack(fill="x", pady=(2, 0))
        return ent

if __name__ == "__main__":
    app = AIOPortalApp()
    app.mainloop()
