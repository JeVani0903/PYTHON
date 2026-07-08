import sys, os, sqlite3, re, math, traceback, time, threading, ctypes, webbrowser, shutil, tempfile, random, subprocess, json
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk
from PIL import Image
from urllib.parse import urlparse, urljoin

# 1. ÉP HỆ THỐNG TÌM ĐÚNG VÀO THƯ MỤC
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 2. ẨN BẢNG ĐEN CONSOLE
if os.name == 'nt':
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 0)
    except: pass

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

def global_exception_handler(exc_type, exc_value, exc_traceback):
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Lỗi Hệ Thống", f"Gặp sự cố:\n\n{err_msg}")
    root.destroy()
    sys.exit(1)

sys.excepthook = global_exception_handler

def get_optimized_image(path, size=(105, 150)):
    try:
        if path and os.path.exists(path):
            img = Image.open(path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return img
    except: pass
    return Image.new("RGB", size, "#d2d3d7")

# =========================================================================
# LÕI QUẢN LÝ TÀI KHOẢN
# =========================================================================
HARDCODED_ACCOUNTS = [
    {"site": "Gmail Công Việc", "user": "admin_work@gmail.com", "pass": "WorkPass123!@", "email": "recovery1@gmail.com", "note": "Mail chính của công ty"},
    {"site": "MangaDex", "user": "manga_scraper", "pass": "Scrape!99", "email": "bot@md.org", "note": "Dùng để kéo API"},
    {"site": "PCloud Storage", "user": "storage_admin", "pass": "Cloud@2026", "email": "admin@cloud.com", "note": "Lưu trữ tài liệu 500GB"},
    {"site": "Tài khoản Phụ", "user": "backup_acc", "pass": "Backup#999", "email": "", "note": ""}
]

# =========================================================================
# LÕI DATABASE SQLITE
# =========================================================================
class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        queries = [
            '''CREATE TABLE IF NOT EXISTS albums (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, album_name TEXT NOT NULL, cover_path TEXT, chu_de TEXT, phan_loai TEXT, quoc_gia TEXT, the_loai TEXT, tac_gia TEXT, note TEXT)''',
            '''CREATE TABLE IF NOT EXISTS download_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, name TEXT, start_num INTEGER DEFAULT 1, total_img INTEGER DEFAULT 59, source TEXT DEFAULT 'Unknown')''',
            '''CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, name TEXT NOT NULL)'''
        ]
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            for q in queries: c.execute(q)
            conn.commit()

    def execute(self, query, params=()):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return c.lastrowid

    def fetchall(self, query, params=()):
        with sqlite3.connect(self.db_path) as conn:
            return conn.cursor().execute(query, params).fetchall()

# =========================================================================
# CORE ENGINE: LÕI XỬ LÝ NGẦM 
# =========================================================================
class CoreEngine:
    def __init__(self, log_callback, base_dir):
        self.log_callback = log_callback
        self.base_dir = base_dir

    def safe_log(self, text, overwrite=False):
        try: self.log_callback(text, overwrite)
        except: pass

    def run_curl_command(self, url, output_file, referer=None, need_lang=True, is_video=False):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        max_time = 3600 if is_video else 60
        cmd = f'curl.exe -g -s -L -C - --compressed --connect-timeout 15 --max-time {max_time} -A "{ua}"'
        if referer: cmd += f' -e "{referer}"'
        if need_lang: cmd += f' -H "Accept-Language: en-US,en;q=0.9"'
        cmd += f' -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/jpeg,image/png,*/*;q=0.8"'
        cmd += f' -o "{output_file}" "{url}"'
        try:
            subprocess.run(cmd, shell=True, creationflags=0x08000000)
            return True
        except: return False

    def validate_video_file(self, filepath, target_ext=".mp4"):
        try:
            if not os.path.exists(filepath): return False
            if os.path.getsize(filepath) < 1024:
                os.remove(filepath)
                return False
            with open(filepath, 'rb') as f:
                header = f.read(32)
                
            header_lower = header.lower()
            if b'<html' in header_lower or b'<!doctype' in header_lower or b'{"' in header_lower or b'cloudflare' in header_lower or b'<?xml' in header_lower or b'<error' in header_lower:
                os.remove(filepath)
                return False
                
            valid_sig = False
            if b'ftyp' in header_lower: valid_sig = True 
            elif len(header) > 0 and header[0] == 0x47: valid_sig = True 
            elif header.startswith(b'\x1aE\xdf\xa3'): valid_sig = True 
            elif header.startswith(b'\x00\x00\x00') and b'moov' in header_lower: valid_sig = True
            
            if not valid_sig:
                os.remove(filepath)
                return False
                
            if filepath.lower().endswith('.tmp'):
                new_path = os.path.splitext(filepath)[0] + target_ext
                if os.path.exists(new_path): os.remove(new_path)
                os.rename(filepath, new_path)
            return True
        except:
            return False

    def validate_and_fix_image(self, filepath):
        try:
            if not os.path.exists(filepath): return False
            if os.path.getsize(filepath) < 200:
                os.remove(filepath)
                return False
                
            with open(filepath, 'rb') as f:
                header = f.read(12)
                
            ext = None
            is_webp = False
            
            if header.startswith(b'\xff\xd8'): ext = '.jpg'
            elif header.startswith(b'\x89PNG\r\n\x1a\n'): ext = '.png'
            elif header.startswith(b'RIFF') and header[8:12] == b'WEBP': 
                ext = '.webp'
                is_webp = True
            elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'): ext = '.gif'
            
            if not ext:
                os.remove(filepath)
                return False
                
            if is_webp:
                try:
                    with Image.open(filepath) as img:
                        rgb_im = img.convert("RGB")
                    jpg_path = os.path.splitext(filepath)[0] + ".jpg"
                    if filepath != jpg_path:
                        os.remove(filepath)
                    rgb_im.save(jpg_path, "JPEG", quality=95)
                    return True
                except:
                    pass 
                    
            if not filepath.lower().endswith(ext):
                new_path = os.path.splitext(filepath)[0] + ext
                if os.path.exists(new_path): os.remove(new_path)
                os.rename(filepath, new_path)
            return True
        except:
            return False

    def _dl_m3u8_with_ffmpeg(self, m3u8_url, output_file, referer):
        uid = f"{int(time.time()*1000)}_{random.randint(100,999)}"
        tmp_dir = os.path.join(tempfile.gettempdir(), f"xc_vid_{uid}")
        os.makedirs(tmp_dir, exist_ok=True)
        
        ffmpeg_path = os.path.join(self.base_dir, "ffmpeg.exe")
        if not os.path.exists(ffmpeg_path): return False

        def to_abs(url_str):
            return urljoin(m3u8_url, url_str)

        tmp_m3u8_path = os.path.join(tmp_dir, "master.m3u8")
        if not self.run_curl_command(m3u8_url, tmp_m3u8_path, referer=referer): return False
            
        with open(tmp_m3u8_path, 'r', encoding='utf-8') as f: lines = f.read().splitlines()
            
        for line in lines:
            if line.strip() and not line.startswith('#') and '.m3u8' in line:
                sub_url = to_abs(line.strip())
                return self._dl_m3u8_with_ffmpeg(sub_url, output_file, referer)

        new_lines = []
        ts_urls = []
        key_url = None
        
        for line in lines:
            if line.startswith('#EXT-X-KEY:'):
                match = re.search(r'URI=["\'](.*?)["\']', line)
                if match:
                    key_url = to_abs(match.group(1))
                    line = line.replace(match.group(1), "key.bin")
                new_lines.append(line)
            elif line.strip() and not line.startswith('#'):
                ts_url = to_abs(line.strip())
                ts_urls.append(ts_url)
                ts_filename = f"seg_{len(ts_urls)-1:05d}.ts"
                new_lines.append(ts_filename)
            else:
                new_lines.append(line)
                
        if not ts_urls: return False

        if key_url:
            self.safe_log("    + Đang bóc tách Chìa khóa Giải mã (AES-128 Key)...\n")
            key_path = os.path.join(tmp_dir, "key.bin")
            self.run_curl_command(key_url, key_path, referer=referer, need_lang=False)
            if os.path.exists(key_path) and os.path.getsize(key_path) not in [16, 32]:
                self.safe_log("    [!] CẢNH BÁO: Key giải mã bị chặn. Video có thể lỗi!\n")
            
        for idx, t_url in enumerate(ts_urls):
            t_path = os.path.join(tmp_dir, f"seg_{idx:05d}.ts")
            perc = int(((idx+1)/len(ts_urls))*100)
            self.safe_log(f"    + Kéo cục dữ liệu Video: [{idx+1}/{len(ts_urls)}] ({perc}%)", overwrite=(idx>0))
            
            self.run_curl_command(t_url, t_path, referer=referer, need_lang=False, is_video=True)
            if not self.validate_video_file(t_path, ".ts"):
                time.sleep(1)
                self.run_curl_command(t_url, t_path, referer=referer, need_lang=False, is_video=True)

        self.safe_log("\n    + Kích hoạt FFmpeg: Tiến hành Mở khóa (Decrypt) và Đóng gói MP4...\n")
        local_m3u8 = os.path.join(tmp_dir, "local.m3u8")
        with open(local_m3u8, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_lines))

        cmd = f'"{ffmpeg_path}" -y -allowed_extensions ALL -i "local.m3u8" -c copy "{output_file}"'
        try:
            res = subprocess.run(cmd, shell=True, cwd=tmp_dir, creationflags=0x08000000)
            if res.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return True
            else:
                self.safe_log(f"    [!] FFmpeg báo lỗi đóng gói. Mã thoát: {res.returncode}\n")
                return False
        except Exception as e:
            self.safe_log(f"    [!] Lỗi gọi FFmpeg: {e}\n")
            return False

    def _dl_m3u8_pure_python(self, m3u8_url, output_file, referer):
        uid = f"{int(time.time()*1000)}_{random.randint(100,999)}"
        tmp_m3u8 = os.path.join(tempfile.gettempdir(), f"v_{uid}.m3u8")
        if not self.run_curl_command(m3u8_url, tmp_m3u8, referer=referer): return False
        
        with open(tmp_m3u8, 'r', encoding='utf-8') as f: content = f.read()
        os.remove(tmp_m3u8)
        
        lines = content.split('\n')
        ts_urls = []
        sub_m3u8 = None
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if '.m3u8' in line:
                    sub_m3u8 = urljoin(m3u8_url, line)
                    break
                else: ts_urls.append(urljoin(m3u8_url, line))
                    
        if sub_m3u8: return self._dl_m3u8_pure_python(sub_m3u8, output_file, referer)
        if not ts_urls: return False
        
        ts_files = []
        for idx, ts_url in enumerate(ts_urls):
            ts_path = os.path.join(tempfile.gettempdir(), f"ts_{uid}_{idx:04d}.ts")
            perc = int(((idx+1)/len(ts_urls))*100)
            self.safe_log(f"    + Kéo cục dữ liệu Video: [{idx+1}/{len(ts_urls)}] ({perc}%)", overwrite=(idx>0))
            self.run_curl_command(ts_url, ts_path, referer=referer, need_lang=False, is_video=True)
            if self.validate_video_file(ts_path, ".ts"): ts_files.append(ts_path)
            else:
                time.sleep(1)
                self.run_curl_command(ts_url, ts_path, referer=referer, need_lang=False, is_video=True)
                if self.validate_video_file(ts_path, ".ts"): ts_files.append(ts_path)
        
        if not ts_files: return False
            
        self.safe_log("\n    + Đang ghép luồng dữ liệu thô (.ts)... ")
        try:
            with open(output_file, 'wb') as merged:
                for ts_file in ts_files:
                    with open(ts_file, 'rb') as f: shutil.copyfileobj(f, merged)
                    os.remove(ts_file)
            self.safe_log("Xong!\n")
            return True
        except Exception as e:
            self.safe_log(f"Lỗi khi ghép file: {e}\n")
            return False

    def dl_core_xchina(self, url, custom_name, start_num, max_img, target_base_dir):
        self.safe_log(f"[*] XCHINA: Bắt đầu dò dữ liệu Đa phương tiện...\n")
        m = re.search(r'id-([a-zA-Z0-9]+)', url) or re.search(r'id=([^&]+)', url)
        if not m: self.safe_log("[!] URL lỗi.\n"); return False
        album_id = m.group(1)
        
        try: start_num = int(start_num); max_img = int(max_img)
        except: start_num = 1; max_img = 59
        
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
        
        if not html: self.safe_log("[!] Bị chặn bởi Cloudflare.\n"); return False
        
        all_html = html
        domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        max_page = 1
        page_matches = re.findall(r'id-' + re.escape(album_id) + r'(?:/|_|/index_)(\d+)\.html', html)
        if page_matches: max_page = max(max_page, max([int(p) for p in page_matches]))
        page_matches_2 = re.findall(r'[?&]page=(\d+)', html)
        if page_matches_2: max_page = max(max_page, max([int(p) for p in page_matches_2]))
        max_page = min(max_page, 50) 
        
        if max_page > 1:
            self.safe_log(f"  ➔ Phát hiện Album có nhiều trang (Tổng: {max_page} trang). Đang thu thập...\n")
            for p in range(2, max_page + 1):
                self.safe_log(f"    + Đang quét trang phụ {p}/{max_page}...", overwrite=(p>2))
                p_url = f"{domain}/photo/id-{album_id}/{p}.html"
                tmp_p = os.path.join(tempfile.gettempdir(), f"xc_p_{uid}_{p}.html")
                if not self.run_curl_command(p_url, tmp_p, referer=url) or os.path.getsize(tmp_p) < 1000:
                    self.run_curl_command(f"{domain}/photo/id-{album_id}_{p}.html", tmp_p, referer=url)
                if os.path.exists(tmp_p) and os.path.getsize(tmp_p) > 0:
                    with open(tmp_p, 'r', encoding='utf-8', errors='ignore') as f:
                        p_html = f.read()
                        if "Cloudflare" not in p_html: all_html += p_html
                if os.path.exists(tmp_p): os.remove(tmp_p)
                time.sleep(1)
            self.safe_log("\n")

        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', all_html, re.IGNORECASE)
        for idx, ifr in enumerate(iframes):
            ifr_url = urljoin(domain, ifr)
            if 'xchina' in ifr_url or 'embed' in ifr_url or 'player' in ifr_url:
                tmp_i = os.path.join(tempfile.gettempdir(), f"xc_ifr_{uid}_{idx}.html")
                self.run_curl_command(ifr_url, tmp_i, referer=url)
                if os.path.exists(tmp_i):
                    with open(tmp_i, 'r', encoding='utf-8', errors='ignore') as f:
                        all_html += f.read()
                    os.remove(tmp_i)

        html_clean = all_html.replace('\\/', '/')
        
        if not custom_name:
            t = re.search(r'<title>(.*?)</title>', html, re.I)
            if t: custom_name = re.sub(r'[<>:"/\\|?*]', '', t.group(1)).strip()
        custom_name = custom_name or f"Album_{album_id}"
        custom_name = re.sub(r'[\\/*?:"<>|]', "", custom_name)
        target_dir = os.path.join(target_base_dir, custom_name); os.makedirs(target_dir, exist_ok=True)
        
        download_success = False

        def get_media_id(v_url):
            parsed = urlparse(v_url).path
            m_id = re.search(r'/([^/]+)(?:\.[^/]+)$', parsed)
            if m_id:
                name = m_id.group(1)
                if name.lower() in ['720p', '1080p', '480p', 'index', 'master', 'playlist']:
                    m_fold = re.search(r'/([^/]+)/[^/]+$', parsed)
                    if m_fold: return m_fold.group(1)
                return name
            return parsed

        # --- BƯỚC 1: XỬ LÝ VIDEO TRƯỚC (DEDUPLICATOR BẢO TOÀN URL) ---
        seen_media_ids = set()
        unique_videos = []
        
        pattern_m3u8 = r'(https?://[^\s"\'<>\[\]{},]+\.m3u8[^\s"\'<>\[\]{},]*)'
        raw_m3u8s = re.findall(pattern_m3u8, html_clean)
        
        for m_url in raw_m3u8s:
            clean_url = m_url.strip('\\')
            if not clean_url.startswith('http'): 
                if any(x in clean_url for x in ['/photos', '/upload', '/images', '/video']):
                    clean_url = "https://img.xchina.io" + (clean_url if clean_url.startswith('/') else '/' + clean_url)
                else:
                    clean_url = urljoin(domain, clean_url)
            
            mid = get_media_id(clean_url)
            if mid not in seen_media_ids:
                seen_media_ids.add(mid)
                unique_videos.append(clean_url)
                
        for m_str in re.finditer(r'["\']([^"\']+\.mp4[^"\']*)["\']', html_clean, re.IGNORECASE):
            v_u = m_str.group(1).strip('\\')
            if '?' in v_u: v_u = v_u.split('?')[0]
            if not v_u.startswith('http'): 
                if any(x in v_u for x in ['/photos', '/upload', '/images', '/video']):
                    v_u = "https://img.xchina.io" + (v_u if v_u.startswith('/') else '/' + v_u)
                else:
                    v_u = urljoin(domain, v_u)
                    
            if 'ad' not in v_u.lower() and 'banner' not in v_u.lower() and 'logo' not in v_u.lower() and 'blank' not in v_u.lower():
                mid = get_media_id(v_u)
                if mid not in seen_media_ids:
                    seen_media_ids.add(mid)
                    unique_videos.append(v_u)
                
        if unique_videos:
            self.safe_log(f"  ➔ Đã phát hiện {len(unique_videos)} Video. Tiến hành tải...\n")
            ffmpeg_path = os.path.join(self.base_dir, "ffmpeg.exe")
            has_ffmpeg = os.path.exists(ffmpeg_path)
            
            for v_idx, v_url in enumerate(unique_videos, 1):
                suffix = f"_Vid_{v_idx:02d}" if len(unique_videos) > 1 else "_Vid"
                out_mp4 = os.path.join(target_dir, f"{custom_name}{suffix}.mp4")
                out_ts = os.path.join(target_dir, f"{custom_name}{suffix}.ts")
                
                if os.path.exists(out_mp4) or os.path.exists(out_ts):
                    self.safe_log(f"  [✓] Video {v_idx} đã tồn tại.\n")
                    download_success = True
                    continue
                    
                self.safe_log(f"  ➔ Đang tải Video [{v_idx}/{len(unique_videos)}]...\n")
                
                if '.mp4' in v_url.lower() and '.m3u8' not in v_url.lower():
                    tmp_vid = out_mp4 + ".tmp"
                    self.run_curl_command(v_url, tmp_vid, referer=url, need_lang=False, is_video=True)
                    if self.validate_video_file(tmp_vid, ".mp4"):
                        download_success = True
                else:
                    if has_ffmpeg:
                        if self._dl_m3u8_with_ffmpeg(v_url, out_mp4, referer=url): download_success = True
                    else:
                        if self._dl_m3u8_pure_python(v_url, out_ts, referer=url): download_success = True

        # --- BƯỚC 2: XỬ LÝ ẢNH TRONG CÙNG THƯ MỤC ---
        self.safe_log(f"  ➔ Phân tích và thu thập thư viện Hình ảnh...\n")
        valid_b = valid_f = ""
        found = is_sequential = False
        
        pattern = r'(photos|photos2|photos3|upload|images)/' + re.escape(album_id) + r'/([^/"\'\s>]+?\.(?:jpg|jpeg|png|webp))'
        unique_names = []
        found_folder = "photos"
        
        for m_str in re.finditer(pattern, html_clean, re.IGNORECASE):
            folder = m_str.group(1)
            filename = m_str.group(2)
            name_no_ext, _ = os.path.splitext(filename)
            if name_no_ext.lower() == 'cover': continue 
            
            pure_name = re.sub(r'^(?:thumb_|cover_)', '', name_no_ext, flags=re.I)
            pure_name = re.sub(r'(?:_thumb|_cover)$', '', pure_name, flags=re.I)
            if pure_name and pure_name not in unique_names:
                unique_names.append(pure_name)
                found_folder = folder

        if unique_names:
            valid_b = f"https://img.xchina.io/{found_folder}/{album_id}"
            for pure_name in unique_names:
                if len(pure_name) > 20: continue 
                m_num = re.search(r'(\d+)$', pure_name)
                if m_num:
                    prefix = pure_name[:m_num.start()]
                    num_len = len(m_num.group(1))
                    same_prefix_count = sum(1 for n in unique_names if n.startswith(prefix) and re.search(r'(\d+)$', n))
                    if same_prefix_count >= 2 or len(unique_names) == 1:
                        valid_f = prefix + ("{0:0" + str(num_len) + "d}" if num_len > 1 and pure_name[m_num.start()] == '0' else "{0}")
                        is_sequential = True
                        found = True
                        break

        if not found and not unique_names:
            if download_success:
                self.safe_log("\n[✓] HOÀN TẤT XCHINA (Chỉ chứa Video)!\n\n")
                return True
                
            self.safe_log("  ➔ Chạy dò mù Hình ảnh (Fallback Mode)...\n")
            formats = ["{0}", "{0:02d}", "{0:03d}", "{0:04d}", "{0:05d}"]
            folders = ["photos", "photos2", "photos3", "upload"]
            for folder in folders:
                base = f"https://img.xchina.io/{folder}/{album_id}"
                for offset in range(3):
                    tn = start_num + offset
                    for fmt in formats:
                        for test_ext in ['.jpg', '.webp']:
                            tf = os.path.join(tempfile.gettempdir(), f"t_xc.tmp")
                            self.run_curl_command(f"{base}/{fmt.format(tn)}{test_ext}", tf, referer=url, need_lang=False)
                            if self.validate_and_fix_image(tf):
                                valid_b, valid_f, start_num = base, fmt, tn
                                found = True
                                is_sequential = True
                                break
                        if found: break
                    if found: break
                if found: break

        if not found and not unique_names and not download_success:
            self.safe_log("[!] Không thể bóc tách cấu trúc file ảnh/video.\n")
            return False

        if is_sequential:
            self.safe_log("  ➔ Chế độ Hình ảnh Sequence (JPG Full HD)...\n")
            saved = start_num
            miss = 0
            i = start_num
            
            while saved < (start_num + max_img) and miss < 30:
                base_path = os.path.join(target_dir, f"{saved:04d}")
                perc = int(((saved - start_num + 1)/max_img)*100); perc = min(100, perc)
                self.safe_log(f"  ➔ Kéo ảnh: [{saved - start_num + 1}/{max_img}] ({perc}%)", overwrite=(i>start_num))
                
                if not any(os.path.exists(base_path + e) for e in ['.jpg', '.png', '.webp', '.gif', '.mp4', '.ts']):
                    tmp_path = base_path + ".tmp"
                    if self.run_curl_command(f"{valid_b}/{valid_f.format(i)}.jpg", tmp_path, referer=url, need_lang=False) and self.validate_and_fix_image(tmp_path):
                        miss = 0
                        download_success = True
                    elif self.run_curl_command(f"{valid_b}/{valid_f.format(i)}.webp", tmp_path, referer=url, need_lang=False) and self.validate_and_fix_image(tmp_path):
                        miss = 0
                        download_success = True
                    else:
                        miss += 1
                        
                    # V168: Tạm dừng 3-5s để tránh bị Cloudflare chặn do tải quá nhanh
                    time.sleep(random.uniform(3.0, 5.0))
                else: miss = 0
                i += 1; saved += 1
                
        elif not is_sequential and unique_names:
            self.safe_log("  ➔ Chế độ Hình ảnh Randomized (Base62 Array)...\n")
            max_dl = len(unique_names) 
            saved = start_num
            
            for idx in range(max_dl):
                pure_name = unique_names[idx]
                base_path = os.path.join(target_dir, f"{saved:04d}")
                perc = int(((idx + 1) / max_dl) * 100)
                self.safe_log(f"  ➔ Kéo ảnh: [{idx + 1}/{max_dl}] ({perc}%)", overwrite=(idx > 0))
                
                if not any(os.path.exists(base_path + e) for e in ['.jpg', '.png', '.webp', '.gif', '.mp4', '.ts']):
                    tmp_path = base_path + ".tmp"
                    if self.run_curl_command(f"{valid_b}/{pure_name}.jpg", tmp_path, referer=url, need_lang=False) and self.validate_and_fix_image(tmp_path):
                        download_success = True
                    elif self.run_curl_command(f"{valid_b}/{pure_name}.webp", tmp_path, referer=url, need_lang=False) and self.validate_and_fix_image(tmp_path):
                        download_success = True
                        
                    # V168: Tạm dừng 3-5s
                    time.sleep(random.uniform(3.0, 5.0))
                saved += 1
                
        self.safe_log("\n[✓] HOÀN TẤT XCHINA!\n\n")
        return download_success

    def dl_core_nettruyen(self, url, custom_name, target_base_dir):
        self.safe_log(f"[*] Đang tải NETTRUYEN: {url}\n")
        uid = f"{int(time.time() * 1000)}_{random.randint(1, 10000)}"
        temp_html = os.path.join(tempfile.gettempdir(), f"nt_tmp_{uid}.html")
        self.run_curl_command(url, temp_html, referer=url)
        if not os.path.exists(temp_html) or os.path.getsize(temp_html) == 0: 
            self.safe_log(f"[!] Lỗi kết nối máy chủ.\n"); return False
        with open(temp_html, 'r', encoding='utf-8', errors='ignore') as f: html = f.read()
        if os.path.exists(temp_html): os.remove(temp_html)
        if not custom_name:
            t = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I)
            custom_name = re.sub(r'[\\/:*?"<>|]', '', re.sub(r'<[^>]+>', '', t.group(1))).strip() if t else "Nettruyen_Tai_Ve"
        manga_dir = os.path.join(target_base_dir, custom_name); os.makedirs(manga_dir, exist_ok=True)
        domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        chapters = []
        for m in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+(?:chapter|chuong|chap)[^"\']+)["\'][^>]*>(.*?)</a>', html, re.I):
            abs_url = urljoin(domain, m.group(1))
            cname = re.sub(r'[\\/:*?"<>|]', '_', re.sub(r'<[^>]+>', '', m.group(2)).strip())
            cname = re.sub(r'\s+', ' ', cname).strip() 
            if cname and (abs_url, cname) not in chapters: chapters.append((abs_url, cname))
        chapters.reverse()
        if not chapters and re.search(r'(?:chapter|chuong|chap)-', url, re.I):
            cname = re.sub(r'[\\/:*?"<>|]', '_', url.split('/')[-1] or "Chapter")
            chapters.append((url, cname))
        if not chapters: self.safe_log("[!] Không dò được chương.\n"); return False
        for url_c, name_c in chapters:
            c_dir = os.path.join(manga_dir, name_c); os.makedirs(c_dir, exist_ok=True)
            self.safe_log(f"  ➔ Kéo Data: {name_c}\n")
            c_tmp = os.path.join(tempfile.gettempdir(), f"nt_c_{uid}.html")
            self.run_curl_command(url_c, c_tmp, referer=url_c)
            if not os.path.exists(c_tmp) or os.path.getsize(c_tmp) == 0: continue
            with open(c_tmp, 'r', encoding='utf-8', errors='ignore') as f: c_html = f.read()
            if os.path.exists(c_tmp): os.remove(c_tmp)
            imgs = [urljoin(domain, i) for i in re.findall(r'<img[^>]+(?:data-original|data-src|src)=["\']([^"\']+)["\']', c_html, re.I) if not re.search(r'(?i)(logo|banner|icon|lazy)', i)]
            for idx, img_url in enumerate(imgs, 1):
                self.safe_log(f"    ➔ Tải: [{idx}/{len(imgs)}]", overwrite=(idx>1))
                base_path = os.path.join(c_dir, f"{idx:04d}")
                if not any(os.path.exists(base_path + ext) for ext in ['.jpg', '.png', '.webp', '.gif']):
                    f_path = base_path + ".tmp"
                    self.run_curl_command(img_url, f_path, referer=url_c, need_lang=False)
                    self.validate_and_fix_image(f_path)
            self.safe_log("\n")
        self.safe_log(f"[✓] HOÀN TẤT NETTRUYEN!\n\n"); return True

    def dl_core_mangadex(self, url_or_id, custom_name, target_base_dir):
        m = re.search(r'([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})', url_or_id)
        if not m:
            self.safe_log(f"[!] Lỗi: Không tìm thấy ID MangaDex hợp lệ trong chuỗi.\n")
            return False
            
        m_id = m.group(1)
        folder_name = custom_name if custom_name else m_id
        folder = os.path.join(target_base_dir, folder_name)
        os.makedirs(folder, exist_ok=True)
        
        self.safe_log(f"[*] MANGADEX: Kéo API Cover của ID: {m_id}\n")
        covers, offset = [], 0
        
        while True:
            query = urllib.parse.urlencode({'limit': 100, 'offset': offset, 'manga[]': m_id})
            api_url = f"https://api.mangadex.org/cover?{query}"
            
            try:
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    content = response.read().decode('utf-8')
                    data = json.loads(content)
                    
                    if "errors" in data:
                        self.safe_log(f"[!] Bị chặn bởi MangaDex: {data['errors'][0].get('detail')}\n")
                        break
                        
                    batch = data.get('data', [])
                    covers.extend(batch)
                    if len(batch) < 100: break
                    offset += 100
            except Exception as e:
                self.safe_log(f"[!] Lỗi truy vấn API MangaDex: {e}\n")
                break
                
        if not covers: 
            self.safe_log("[!] Cảnh báo: ID không tồn tại hoặc truyện không có ảnh cover.\n")
            return False
            
        for i, c in enumerate(covers, 1):
            fn = c['attributes']['fileName']
            self.safe_log(f"  ➔ Đang tải Cover: [{i}/{len(covers)}]", overwrite=(i>1))
            base_path = os.path.join(folder, f"Cover_{i:03d}")
            
            if not any(os.path.exists(base_path + ext) for ext in ['.jpg', '.png', '.webp', '.gif']):
                fp = base_path + ".tmp"
                self.run_curl_command(f"https://uploads.mangadex.org/covers/{m_id}/{fn}", fp, need_lang=False)
                self.validate_and_fix_image(fp)
                
        self.safe_log(f"\n[✓] HOÀN TẤT TẢI MANGADEX!\n\n")
        return True

    def task_winrar(self, winrar_exe, target, password, del_opt):
        if not os.path.exists(winrar_exe): self.safe_log("[!] Lỗi: Không tìm thấy WinRAR.\n"); return
        self.safe_log("[*] Đang Nén File ngầm...\n")
        items = os.listdir(target)
        cmd = [winrar_exe, "a", "-cfg-", "-m0", "-ep1", "-ibck", "-inul", "-x*.bat", "-x*.py"]
        if password: cmd.append(f"-p{password}")

        temp_comment_path = None
        cmt_text = f"Password giai nen: {password}" if password else "File khong co mat khau."
        uid = f"cmt_{int(time.time() * 1000)}"
        temp_comment_path = os.path.join(tempfile.gettempdir(), f"{uid}.txt")
        try:
            with open(temp_comment_path, 'w', encoding='utf-16') as f: f.write(cmt_text)
            cmd.extend(["-scuc", f"-z{temp_comment_path}"])
        except: pass

        for item in [i for i in items if os.path.isdir(os.path.join(target, i))]:
            ipath = os.path.join(target, item)
            self.safe_log(f"  ➔ Đang nén: {item} ")
            res = subprocess.run(cmd + [os.path.join(target, f"{item}.cbz"), ipath], stdout=subprocess.PIPE, creationflags=0x08000000)
            if res.returncode in [0, 1]:
                self.safe_log("- Xong\n", overwrite=True)
                if del_opt: shutil.rmtree(ipath, ignore_errors=True)

        if temp_comment_path and os.path.exists(temp_comment_path): os.remove(temp_comment_path)
        self.safe_log("[✓] HOÀN TẤT ĐÓNG GÓI.\n\n")

    def task_create_folders(self, target, name, vol_str):
        try: vol = int(vol_str)
        except: return
        for i in range(1, vol + 1): os.makedirs(os.path.join(target, f"{name} T{i:02d}"), exist_ok=True)
        self.safe_log(f"[✓] Đã tạo {vol} Thư mục thành công.\n")

    def task_rename_files(self, target, prefix):
        if not os.path.exists(target): return
        files = sorted([f for f in os.listdir(target) if os.path.isfile(os.path.join(target, f))])
        for idx, f in enumerate(files, 1):
            ext = os.path.splitext(f)[1]
            new_name = f"{prefix}_{idx:04d}{ext}" if prefix else f"{idx:04d}{ext}"
            try: os.rename(os.path.join(target, f), os.path.join(target, new_name))
            except: pass
        self.safe_log(f"[✓] Đã đổi tên {len(files)} file.\n")

# =========================================================================
# GIAO DIỆN CHÍNH
# =========================================================================
ctk.set_appearance_mode("Light")
MEDIAN_BG = "#f5f3f2"
MEDIAN_CARD = "#fffdfc"
MEDIAN_LINK = "#3740ff"
MEDIAN_TEXT = "#0e2045"
MEDIAN_BORDER = "#e4e3e1"

if HAS_DND:
    class AppBase(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class AppBase(ctk.CTk): pass

class AIOPortalApp(AppBase):
    def __init__(self):
        super().__init__()
        self.title("AIO Portal Master - V168.0 (Anti-Ban Delay)")
        self.geometry("1400x850")
        self.minsize(1100, 750) 
        self.configure(fg_color=MEDIAN_BG)
        
        self.base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.db = Database(os.path.join(self.base_dir, "AIO_Portal_Data.db"))
        self.engine = CoreEngine(self.write_log, self.base_dir)
        
        self.album_checkboxes = {}; self.active_cards = []; self.gallery_pool = []; self.list_pool = {}
        self.image_cache = {}
        self.current_page = 1; self.items_per_page = 32; self.total_pages = 1
        self.last_window_width = 0; self._resize_timer = None
        self.is_downloading_all = False
        
        self.setup_ui()
        self.switch_tab("album")
        self.bind("<Configure>", self._on_window_resize)
        
    def setup_ui(self):
        header = ctk.CTkFrame(self, fg_color=MEDIAN_CARD, height=65, corner_radius=0, border_width=1, border_color=MEDIAN_BORDER)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="AIO PORTAL MASTER", font=("Arial", 20, "bold"), text_color=MEDIAN_TEXT).pack(side="left", padx=25, pady=5)
        ctk.CTkLabel(header, text="V168.0 - Bổ sung Delay 3-5s chống Cloudflare Block", font=("Arial", 13), text_color="#656e77").pack(side="left", pady=8)

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        left_col = ctk.CTkFrame(main_container, fg_color="transparent", width=250)
        left_col.pack(side="left", fill="y", expand=False, padx=(0, 20))
        left_col.pack_propagate(False)
        
        menu_frame = ctk.CTkFrame(left_col, fg_color=MEDIAN_CARD, corner_radius=8, border_width=1, border_color=MEDIAN_BORDER)
        menu_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(menu_frame, text="ĐIỀU HƯỚNG CHÍNH", font=("Arial", 11, "bold"), text_color="#9ca3af").pack(fill="x", padx=15, pady=15)
        
        self.tab_buttons = {}
        tabs = [
            ("album", "🗂 Quản Lý Kho Album"),
            ("download", "⬇️ Tải Truyện (Web)"),
            ("tools", "📦 Công Cụ File"),
            ("bookmark", "🔖 Bookmarks"),
            ("account", "🔐 Quản Lý Tài Khoản")
        ]
        
        for tab_id, tab_name in tabs:
            btn = ctk.CTkButton(menu_frame, text=tab_name, font=("Arial", 14, "bold"), fg_color="transparent", text_color=MEDIAN_TEXT, anchor="w", hover_color=MEDIAN_BG, height=40, command=lambda t=tab_id: self.switch_tab(t))
            btn.pack(fill="x", padx=10, pady=2)
            self.tab_buttons[tab_id] = btn

        self.right_col = ctk.CTkFrame(main_container, fg_color="transparent")
        self.right_col.pack(side="right", fill="both", expand=True)
        
        self.frames = {}
        self.build_tab_album()
        self.build_tab_download()
        self.build_tab_tools()
        self.build_tab_bookmark()
        self.build_tab_account()

    def switch_tab(self, target_tab):
        for tab_id, frame in self.frames.items():
            frame.pack_forget()
            self.tab_buttons[tab_id].configure(fg_color="transparent", text_color=MEDIAN_TEXT)
        self.frames[target_tab].pack(fill="both", expand=True)
        self.tab_buttons[target_tab].configure(fg_color=MEDIAN_LINK, text_color="#ffffff")
        
        if target_tab == "album": self.load_manager_grid_ui()
        elif target_tab == "download": self.load_queue_from_db()
        elif target_tab == "bookmark": self.load_db_list("bookmarks", self.bm_list_frame, self.render_bm_item)

    def _on_window_resize(self, event):
        if event.widget == self:
            current_width = event.width
            if abs(getattr(self, 'last_window_width', 0) - current_width) > 20:
                self.last_window_width = current_width
                if getattr(self, '_resize_timer', None): self.after_cancel(self._resize_timer)
                self._resize_timer = self.after(150, self._layout_gallery_cards)

    def write_log(self, text, overwrite=False):
        def update():
            for box in [getattr(self, 'dl_log_box', None), getattr(self, 'tool_log_box', None)]:
                if box:
                    box.configure(state="normal")
                    if overwrite:
                        lines = box.get("1.0", tk.END).splitlines()
                        if len(lines) > 1: box.delete(f"{len(lines)-1}.0", tk.END); box.insert(tk.END, "\n")
                    box.insert(tk.END, text)
                    box.see(tk.END)
                    box.configure(state="disabled")
        self.after(0, update)

    def create_entry(self, parent, label, var, expand=True, on_return=None):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", fill="x", expand=expand, padx=(0, 15))
        ctk.CTkLabel(f, text=label, font=("Arial", 11, "bold"), text_color="#656e77").pack(anchor="w")
        ent = ctk.CTkEntry(f, textvariable=var, height=35)
        ent.pack(fill="x")
        if on_return: ent.bind("<Return>", lambda e: on_return())
        return ent

    # ==================== TẠO TAB ====================
    def build_tab_album(self):
        f = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.frames["album"] = f
        self.album_view_mode = tk.StringVar(value="Gallery")
        ab = ctk.CTkFrame(f, fg_color="transparent"); ab.pack(fill="x", pady=(0, 10))
        ctk.CTkSegmentedButton(ab, values=["Gallery", "Danh Sách"], variable=self.album_view_mode, selected_color=MEDIAN_LINK, unselected_color=MEDIAN_CARD, text_color=MEDIAN_TEXT, command=lambda v: self.load_manager_grid_ui()).pack(side="left")
        ctk.CTkButton(ab, text="🗑️ Xóa Chọn", fg_color="#e51661", hover_color="#c81054", command=self.album_delete).pack(side="right")
        self.db_scroll_grid = ctk.CTkScrollableFrame(f, fg_color="transparent")
        self.db_scroll_grid.pack(fill="both", expand=True)

    def build_tab_download(self):
        f = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.frames["download"] = f
        self.dl_source_var = tk.StringVar(value="Nettruyen.fit")
        self.dl_u = tk.StringVar(); self.dl_n = tk.StringVar(); self.dl_d = tk.StringVar(); self.dl_t = tk.StringVar(value="59")
        
        inp = ctk.CTkFrame(f, fg_color=MEDIAN_CARD, corner_radius=8, border_width=1, border_color=MEDIAN_BORDER)
        inp.pack(fill="x", pady=5)
        
        src_frame = ctk.CTkFrame(inp, fg_color="transparent")
        src_frame.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(src_frame, text="Nguồn Tải:", font=("Arial", 11, "bold")).pack(side="left", padx=(0, 10))
        seg = ctk.CTkSegmentedButton(src_frame, values=["Nettruyen.fit", "MangaDex", "XChina.co"], variable=self.dl_source_var, command=self.update_dl_ui)
        seg.pack(side="left")

        self.dl_dyn_frame = ctk.CTkFrame(inp, fg_color="transparent")
        self.dl_dyn_frame.pack(fill="x", padx=15, pady=5)
        
        btn_frame = ctk.CTkFrame(inp, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(btn_frame, text="➕ THÊM VÀO CHỜ", fg_color="#10b981", command=self.dl_add).pack(side="left")
        ctk.CTkButton(btn_frame, text="⬇️ TẢI TOÀN BỘ CHỜ", fg_color="#3740ff", command=self.dl_all).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="🚀 AUTO XCHINA TXT", fg_color="#f59e0b", hover_color="#d97706", command=self.import_xchina_txt).pack(side="left")
        
        self.queue_progress_var = tk.StringVar(value="Danh sách chờ: 0 mục")
        self.progress_lbl = ctk.CTkLabel(btn_frame, textvariable=self.queue_progress_var, font=("Arial", 13, "bold"), text_color="#e51661")
        self.progress_lbl.pack(side="left", padx=20)
        
        self.queue_frame = ctk.CTkScrollableFrame(f, height=200, fg_color=MEDIAN_CARD, border_color=MEDIAN_BORDER, border_width=1)
        self.queue_frame.pack(fill="x", pady=10)
        self.dl_log_box = ctk.CTkTextbox(f, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#00ff00")
        self.dl_log_box.pack(fill="both", expand=True)
        
        self.update_dl_ui()

    def update_dl_ui(self, *args):
        for w in self.dl_dyn_frame.winfo_children(): w.destroy()
        src = self.dl_source_var.get()
        
        r1 = ctk.CTkFrame(self.dl_dyn_frame, fg_color="transparent")
        r1.pack(fill="x", pady=5)
        r2 = ctk.CTkFrame(self.dl_dyn_frame, fg_color="transparent")
        r2.pack(fill="x", pady=5)
        
        if src == "Nettruyen.fit":
            self.create_entry(r1, "Link Truyện (URL)", self.dl_u, on_return=self.dl_add)
            self.create_entry(r1, "Tên Album", self.dl_n, on_return=self.dl_add)
        elif src == "MangaDex":
            self.create_entry(r1, "Link (URL) hoặc ID MangaDex", self.dl_u, on_return=self.dl_add)
            self.create_entry(r1, "Tên Album chứa Cover", self.dl_n, on_return=self.dl_add)
        elif src == "XChina.co":
            self.create_entry(r1, "Link Album/Video", self.dl_u, on_return=self.dl_add)
            self.create_entry(r1, "Tên Model/Album", self.dl_n, on_return=self.dl_add)
            self.create_entry(r2, "Ngày (VD: 2008.08.26)", self.dl_d, on_return=self.dl_add)
            self.create_entry(r2, "Tổng (VD: 76 hoặc 76P+2V)", self.dl_t, on_return=self.dl_add)

    def build_tab_tools(self):
        f = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.frames["tools"] = f
        
        self.tool_mode_var = tk.StringVar(value="Nén WinRAR")
        self.tl_rar_tgt = tk.StringVar(value="C:\\"); self.tl_rar_pass = tk.StringVar(); self.tl_rar_del = tk.BooleanVar(value=False)
        self.tl_cf_tgt = tk.StringVar(); self.tl_cf_name = tk.StringVar(); self.tl_cf_vol = tk.StringVar(value="5")
        self.tl_ren_tgt = tk.StringVar(); self.tl_ren_pre = tk.StringVar()
        
        inp = ctk.CTkFrame(f, fg_color=MEDIAN_CARD, corner_radius=8, border_width=1, border_color=MEDIAN_BORDER)
        inp.pack(fill="x", pady=5)
        
        src_frame = ctk.CTkFrame(inp, fg_color="transparent")
        src_frame.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(src_frame, text="Chọn Công Cụ:", font=("Arial", 11, "bold")).pack(side="left", padx=(0, 10))
        seg = ctk.CTkSegmentedButton(src_frame, values=["Nén WinRAR", "Tạo Thư Mục", "Đổi Tên File"], variable=self.tool_mode_var, command=self.update_tool_ui)
        seg.pack(side="left")

        self.tool_dyn_frame = ctk.CTkFrame(inp, fg_color="transparent")
        self.tool_dyn_frame.pack(fill="x", padx=15, pady=5)
        
        self.tool_btn_frame = ctk.CTkFrame(inp, fg_color="transparent")
        self.tool_btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.tool_log_box = ctk.CTkTextbox(f, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#00ff00")
        self.tool_log_box.pack(fill="both", expand=True, pady=10)
        
        self.update_tool_ui()

    def update_tool_ui(self, *args):
        for w in self.tool_dyn_frame.winfo_children(): w.destroy()
        for w in self.tool_btn_frame.winfo_children(): w.destroy()
        
        mode = self.tool_mode_var.get()
        r1 = ctk.CTkFrame(self.tool_dyn_frame, fg_color="transparent"); r1.pack(fill="x", pady=5)
        r2 = ctk.CTkFrame(self.tool_dyn_frame, fg_color="transparent"); r2.pack(fill="x", pady=5)

        if mode == "Nén WinRAR":
            cmd_rar = lambda: threading.Thread(target=self.engine.task_winrar, args=("C:\\Program Files\\WinRAR\\WinRAR.exe", self.tl_rar_tgt.get(), self.tl_rar_pass.get(), self.tl_rar_del.get()), daemon=True).start()
            self.create_entry(r1, "Thư mục chứa các folder cần nén:", self.tl_rar_tgt, on_return=cmd_rar)
            self.create_entry(r1, "Password (Tùy chọn):", self.tl_rar_pass, on_return=cmd_rar)
            ctk.CTkCheckBox(r2, text="Xóa thư mục gốc sau khi nén thành công", variable=self.tl_rar_del).pack(anchor="w", padx=5, pady=5)
            ctk.CTkButton(self.tool_btn_frame, text="▶ BẮT ĐẦU NÉN CBZ", fg_color="#10b981", command=cmd_rar).pack(side="left")
            
        elif mode == "Tạo Thư Mục":
            cmd_cf = lambda: threading.Thread(target=self.engine.task_create_folders, args=(self.tl_cf_tgt.get(), self.tl_cf_name.get(), self.tl_cf_vol.get()), daemon=True).start()
            self.create_entry(r1, "Thư mục đích:", self.tl_cf_tgt, on_return=cmd_cf)
            self.create_entry(r1, "Tên gốc (VD: Tập):", self.tl_cf_name, on_return=cmd_cf)
            self.create_entry(r2, "Số lượng:", self.tl_cf_vol, on_return=cmd_cf)
            ctk.CTkButton(self.tool_btn_frame, text="▶ TẠO HÀNG LOẠT", fg_color="#10b981", command=cmd_cf).pack(side="left")
            
        elif mode == "Đổi Tên File":
            cmd_ren = lambda: threading.Thread(target=self.engine.task_rename_files, args=(self.tl_ren_tgt.get(), self.tl_ren_pre.get()), daemon=True).start()
            self.create_entry(r1, "Thư mục chứa file:", self.tl_ren_tgt, on_return=cmd_ren)
            self.create_entry(r1, "Tiền tố (Để trống = 0001.jpg):", self.tl_ren_pre, on_return=cmd_ren)
            ctk.CTkButton(self.tool_btn_frame, text="▶ ĐỔI TÊN HÀNG LOẠT", fg_color="#10b981", command=cmd_ren).pack(side="left")

    def build_tab_bookmark(self):
        f = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.frames["bookmark"] = f
        self.bm_n = tk.StringVar(); self.bm_u = tk.StringVar()
        cmd_add = lambda: self.add_db_list("bookmarks", ["name", "url"], [self.bm_n, self.bm_u], self.bm_list_frame, self.render_bm_item)
        
        i = ctk.CTkFrame(f, fg_color=MEDIAN_CARD, border_width=1, border_color=MEDIAN_BORDER); i.pack(fill="x", pady=5)
        r = ctk.CTkFrame(i, fg_color="transparent"); r.pack(fill="x", padx=15, pady=15)
        self.create_entry(r, "Tên Bookmark", self.bm_n, on_return=cmd_add)
        self.create_entry(r, "URL", self.bm_u, on_return=cmd_add)
        ctk.CTkButton(i, text="➕ THÊM", command=cmd_add).pack(anchor="w", padx=15, pady=(0,15))
        self.bm_list_frame = ctk.CTkScrollableFrame(f, fg_color="transparent"); self.bm_list_frame.pack(fill="both", expand=True)

    def build_tab_account(self):
        f = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.frames["account"] = f
        
        ctk.CTkLabel(f, text="*Dữ liệu Tài khoản được LƯU CỨNG trong code (main.pyw) để bảo mật.\nĐể chỉnh sửa, hãy dùng Notepad mở file code và sửa biến HARDCODED_ACCOUNTS.", text_color="#e51661", font=("Arial", 12, "italic")).pack(pady=10)
        
        scr = ctk.CTkScrollableFrame(f, fg_color="transparent")
        scr.pack(fill="both", expand=True)
        
        for acc in HARDCODED_ACCOUNTS:
            c = ctk.CTkFrame(scr, fg_color=MEDIAN_CARD, border_width=1, border_color=MEDIAN_BORDER)
            c.pack(fill="x", pady=5)
            
            inf = ctk.CTkFrame(c, fg_color="transparent")
            inf.pack(side="left", fill="x", expand=True, padx=15, pady=10)
            
            ctk.CTkLabel(inf, text=f"🌐 {acc.get('site', '')}", font=("Arial", 14, "bold")).pack(anchor="w")
            ctk.CTkLabel(inf, text=f"👤 User: {acc.get('user', '')}    | 🔑 Pass: {acc.get('pass', '')}", font=("Arial", 12)).pack(anchor="w", pady=(5,0))
            
            bot_txt = []
            if acc.get("email"): bot_txt.append(f"📧 Email Recovery: {acc.get('email')}")
            if acc.get("note"): bot_txt.append(f"📝 Note: {acc.get('note')}")
            if bot_txt: 
                ctk.CTkLabel(inf, text="   |   ".join(bot_txt), text_color="#656e77").pack(anchor="w", pady=(2,0))
                
            ctk.CTkButton(c, text="📋 Copy Pass", width=90, fg_color=MEDIAN_LINK, command=lambda p=acc.get('pass', ''): (self.clipboard_clear(), self.clipboard_append(p), messagebox.showinfo("Copied", "Đã copy Mật khẩu!"))).pack(side="right", padx=15)

    # ==================== CÁC HÀM CRUD CHUNG ====================
    def load_db_list(self, table, frame, render_func):
        for w in frame.winfo_children(): w.destroy()
        for row in self.db.fetchall(f"SELECT * FROM {table} ORDER BY id DESC"): render_func(frame, row)

    def add_db_list(self, table, cols, vars_list, frame, render_func):
        vals = [v.get().strip() for v in vars_list]
        if not any(vals): return
        q = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})"
        self.db.execute(q, vals)
        for v in vars_list: v.set("")
        self.load_db_list(table, frame, render_func)

    def del_db_list(self, table, r_id, frame, render_func):
        self.db.execute(f"DELETE FROM {table} WHERE id=?", (r_id,))
        self.load_db_list(table, frame, render_func)

    def render_bm_item(self, f, r):
        c = ctk.CTkFrame(f, fg_color=MEDIAN_CARD, border_width=1); c.pack(fill="x", pady=2)
        ctk.CTkLabel(c, text=f"🔖 {r[2]} ({r[1]})").pack(side="left", padx=10, pady=5)
        ctk.CTkButton(c, text="❌", width=40, fg_color="#e51661", command=lambda: self.del_db_list("bookmarks", r[0], f, self.render_bm_item)).pack(side="right", padx=5)
        ctk.CTkButton(c, text="Mở", width=60, command=lambda: webbrowser.open(r[1])).pack(side="right")

    # ==================== TẢI TRUYỆN VÀ VIDEO ====================
    def dl_add(self):
        src = self.dl_source_var.get()
        u = self.dl_u.get().strip()
        n = self.dl_n.get().strip() 
        d = self.dl_d.get().strip()
        t_raw = self.dl_t.get().strip() or "59"
        
        if u and not n and "/video/" in u.lower():
            n = "Video XChina"
            
        if u and n:
            fn = n
            if src == "XChina.co":
                pm = re.search(r'(\d+)\s*[pP]', t_raw)
                p_count = pm.group(1) if pm else (re.search(r'^(\d+)', t_raw).group(1) if re.search(r'^(\d+)', t_raw) else "59")
                
                vm = re.search(r'(\d+)\s*[vV]', t_raw)
                v_count = vm.group(1) if vm else ("1" if "/video/" in u.lower() else "0")
                
                t_display = f"{p_count}P+{v_count}V"
                
                d_final = d
                if d_final:
                    d_extract = re.search(r'\((.*?)\)', d_final)
                    if d_extract: d_final = d_extract.group(1)
                
                fn = f"{n} ({d_final}) [{t_display}]" if d_final else f"{n} [{t_display}]"
                fn = re.sub(r'[\\/*?:"<>|]', "", fn)
                
                p_val = int(p_count) if p_count.isdigit() else 59
                v_val = int(v_count) if v_count.isdigit() else 0
                total_files = str(p_val + v_val)
                
                self.db.execute("INSERT INTO download_queue (url, name, start_num, total_img, source) VALUES (?,?,?,?,?)", (u, fn, 1, total_files, src))
            else:
                self.db.execute("INSERT INTO download_queue (url, name, start_num, total_img, source) VALUES (?,?,?,?,?)", (u, fn, 1, t_raw, src))
            
            self.dl_u.set(""); self.dl_n.set(""); self.dl_d.set("")
            self.load_queue_from_db()

    def import_xchina_txt(self):
        filepath = filedialog.askopenfilename(title="Chọn file TXT XChina", filetypes=[("Text Files", "*.txt")])
        if not filepath: return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            blocks = content.split("=====================================")
            count = 0
            
            for block in blocks:
                if not block.strip(): continue
                
                name_match = re.search(r'📌 Tên (?:Album|Mục)\s*:\s*(.+)', block)
                model_match = re.search(r'👤 Model\s*:\s*(.+)', block)
                date_match = re.search(r'📅 Note/Ngày\s*:\s*(.+)', block)
                count_match = re.search(r'🖼️ (?:Số lượng|Thông số)\s*:\s*(.+)', block)
                link_match = re.search(r'🔗 Link\s*:\s*(https://en\.xchina\.co/(?:photo|photos|video|videos)/id-[a-zA-Z0-9]+\.html)', block)
                
                if name_match and link_match:
                    raw_name = name_match.group(1).strip()
                    model_name = model_match.group(1).strip() if model_match else "N/A"
                    date_str = date_match.group(1).strip() if date_match else ""
                    
                    if date_str == "N/A": date_str = "" 
                    if date_str:
                        d_extract = re.search(r'\((.*?)\)', date_str)
                        if d_extract: date_str = d_extract.group(1)
                        
                    base_name = model_name if (model_name and model_name.upper() not in ["N/A", "NONE"]) else raw_name
                    u = link_match.group(1).strip()
                    
                    t_raw = count_match.group(1).strip() if count_match else "59"
                    
                    pm = re.search(r'(\d+)\s*[pP]', t_raw)
                    p_count = pm.group(1) if pm else (re.search(r'^(\d+)', t_raw).group(1) if re.search(r'^(\d+)', t_raw) else "59")
                    
                    vm = re.search(r'(\d+)\s*[vV]', t_raw)
                    v_count = vm.group(1) if vm else ("1" if "/video/" in u.lower() else "0")
                    
                    t_display = f"{p_count}P+{v_count}V"
                    fn = f"{base_name} ({date_str}) [{t_display}]" if date_str else f"{base_name} [{t_display}]"
                    fn = re.sub(r'[\\/*?:"<>|]', "", fn)
                    
                    p_val = int(p_count) if p_count.isdigit() else 59
                    v_val = int(v_count) if v_count.isdigit() else 0
                    total_files = str(p_val + v_val)
                    
                    exist = self.db.fetchall("SELECT id FROM download_queue WHERE url=?", (u,))
                    if not exist:
                        self.db.execute("INSERT INTO download_queue (url, name, start_num, total_img, source) VALUES (?,?,?,?,?)", (u, fn, 1, total_files, "XChina.co"))
                        count += 1
                    
            if count > 0:
                self.load_queue_from_db()
                self.write_log(f"\n[*] Đã nạp thành công {count} Mục từ File TXT. Tự động chuyển qua tiến trình tải...\n")
                self.dl_all()
            else:
                messagebox.showwarning("Cảnh Báo", "Không tìm thấy dữ liệu hợp lệ, hoặc các link này đã có sẵn trong tiến trình!")
                
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file hoặc lỗi hệ thống:\n{e}")

    def load_queue_from_db(self):
        for w in self.queue_frame.winfo_children(): w.destroy()
        rows = self.db.fetchall("SELECT id, url, name, start_num, total_img, source FROM download_queue ORDER BY id DESC")
        
        if not getattr(self, 'is_downloading_all', False):
            if hasattr(self, 'queue_progress_var'):
                self.queue_progress_var.set(f"Danh sách chờ: {len(rows)} mục")
                self.progress_lbl.configure(text_color="#e51661")
                
        for r_id, u, n, s, t, src in rows:
            c = ctk.CTkFrame(self.queue_frame, fg_color=MEDIAN_CARD, border_width=1); c.pack(fill="x", pady=2)
            ctk.CTkLabel(c, text=f"📂 [{src}] {n} | 🔗 {u}", font=("Arial", 12, "bold")).pack(side="left", padx=10, pady=10)
            btn = ctk.CTkButton(c, text="⬇ Tải Ngay", width=90, fg_color=MEDIAN_LINK)
            btn.configure(command=lambda i=r_id, ur=u, nm=n, st=s, tt=t, sc=src, b=btn: threading.Thread(target=self._dl_worker, args=(i, ur, nm, st, tt, sc, b), daemon=True).start())
            btn.pack(side="right", padx=(5, 15))
            ctk.CTkButton(c, text="❌", width=40, fg_color="#e51661", command=lambda i=r_id: self.db.execute("DELETE FROM download_queue WHERE id=?", (i,)) or self.load_queue_from_db()).pack(side="right")

    def dl_all(self):
        rows = self.db.fetchall("SELECT id, url, name, start_num, total_img, source FROM download_queue ORDER BY id ASC")
        if not rows: return messagebox.showinfo("Trống", "Không có mục nào trong danh sách chờ!")
        threading.Thread(target=self._dl_all_worker, args=(rows,), daemon=True).start()

    def _dl_all_worker(self, rows):
        self.is_downloading_all = True
        total_items = len(rows)
        completed_items = 0
        
        self.progress_lbl.configure(text_color="#10b981") 
        self.queue_progress_var.set(f"Tiến độ: {completed_items}/{total_items} hoàn thành")
        
        self.write_log(f"\n--- BẮT ĐẦU CHẾ ĐỘ TẢI HÀNG LOẠT ({total_items} MỤC) ---\n")
        for r_id, u, n, s, t, src in rows:
            self._dl_worker(r_id, u, n, s, t, src, b=None)
            
            completed_items += 1
            self.queue_progress_var.set(f"Tiến độ: {completed_items}/{total_items} hoàn thành")
            time.sleep(2)
            
        self.write_log(f"\n--- ĐÃ HOÀN TẤT TẢI HÀNG LOẠT ---\n")
        self.is_downloading_all = False
        self.progress_lbl.configure(text_color="#3740ff") 
        self.queue_progress_var.set(f"Đã tải xong toàn bộ {total_items} mục!")

    def _dl_worker(self, i, u, n, s, t, src, b=None):
        if b: b.configure(state="disabled", text="Đang tải...")
        tg = os.path.join(self.base_dir, "Downloads"); os.makedirs(tg, exist_ok=True)
        suc = False
        self.write_log(f"\n====================================\nĐANG KHỞI ĐỘNG TẢI: [{src}] {n}\n")
        
        if src == "Nettruyen.fit" or "nettruyen" in u.lower(): 
            suc = self.engine.dl_core_nettruyen(u, n, tg)
        elif src == "MangaDex" or "mangadex" in u.lower(): 
            suc = self.engine.dl_core_mangadex(u, n, tg)
        elif src == "XChina.co" or "xchina" in u.lower(): 
            suc = self.engine.dl_core_xchina(u, n, s, t, tg)
                
        if suc:
            self.db.execute("DELETE FROM download_queue WHERE id=?", (i,))
            self.after(0, self.load_queue_from_db)

    # ==================== KHO ALBUM ====================
    def _layout_gallery_cards(self):
        if self.album_view_mode.get() != "Gallery" or not self.active_cards: return
        cw = self.right_col.winfo_width()
        if cw < 200: cw = 1400 
        cm = max(1, cw // 130)
        pad_x = max(5, (cw - (cm * 120)) // (cm * 2))
        for i in range(50): self.db_scroll_grid.grid_columnconfigure(i, weight=0)
        for i, card in enumerate(self.active_cards): card.grid(row=i//cm, column=i%cm, padx=pad_x, pady=10, sticky="n")

    def load_manager_grid_ui(self):
        for c in self.gallery_pool: c.grid_forget()
        self.active_cards = []; self.album_checkboxes = {}
        threading.Thread(target=self._album_fetch_thread, daemon=True).start()

    def _album_fetch_thread(self):
        rs = self.db.fetchall("SELECT id, url, album_name, cover_path FROM albums ORDER BY id DESC LIMIT 40")
        self.after(0, lambda: self._album_render(rs))

    def _album_render(self, rows):
        for i, (r_id, u, n, c) in enumerate(rows):
            if i >= len(self.gallery_pool):
                cd = ctk.CTkFrame(self.db_scroll_grid, width=120, height=205, fg_color=MEDIAN_CARD, border_width=1)
                cd.grid_propagate(False)
                li = ctk.CTkLabel(cd, text=""); li.pack(pady=(6,0))
                cv = tk.BooleanVar()
                ck = ctk.CTkCheckBox(cd, text="", variable=cv, width=16, height=16); ck.place(relx=0.78, rely=0.03)
                lt = ctk.CTkLabel(cd, text="", font=("Arial", 11, "bold")); lt.pack(side="bottom", pady=4)
                cd._refs = {"img": li, "chk": ck, "cv": cv, "title": lt}
                self.gallery_pool.append(cd)
            
            card = self.gallery_pool[i]; refs = card._refs
            refs["cv"].set(False); self.album_checkboxes[r_id] = refs["cv"]
            refs["title"].configure(text=n[:13]+"..." if len(n)>13 else n)
            if c not in self.image_cache: self.image_cache[c] = ctk.CTkImage(light_image=get_optimized_image(c, (105, 150)), size=(105, 150))
            refs["img"].configure(image=self.image_cache[c])
            self.active_cards.append(card)
        self._layout_gallery_cards()

    def album_delete(self):
        ids = [i for i, v in self.album_checkboxes.items() if v.get()]
        if ids and messagebox.askyesno("Xóa", "Xóa các truyện này?"):
            self.db.executemany("DELETE FROM albums WHERE id=?", [(i,) for i in ids])
            self.load_manager_grid_ui()

if __name__ == "__main__":
    app = AIOPortalApp()
    app.mainloop()
