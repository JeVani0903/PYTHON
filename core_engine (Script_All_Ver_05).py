import os, re, time, shutil, subprocess, json, zipfile, random
import urllib.parse, urllib.request

class CoreEngine:
    def __init__(self, base_dir, log_queue):
        self.base_dir = base_dir
        self.log_queue = log_queue
        self.IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
        self.VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.webm', '.m4v', '.avi'}

    def safe_log(self, text, overwrite=False):
        timestamp = time.strftime("[%H:%M:%S] ")
        try:
            self.log_queue.put({"type": "log", "msg": timestamp + text + "\n"})
        except: pass

    def signal_ui_update(self, action):
        self.log_queue.put({"type": "action", "msg": action})

    def run_curl_command(self, url, output_file, referer=None, need_lang=True, is_video=False):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        max_time = 600 if is_video else 30
        cmd = f'curl.exe -s -L -C - --compressed --connect-timeout 15 --max-time {max_time} -A "{ua}"'
        if referer: cmd += f' -e "{referer}"'
        if need_lang: cmd += f' -H "Accept-Language: en-US,en;q=0.9"'
        cmd += f' -o "{output_file}" "{url}"'
        
        try:
            subprocess.run(cmd, shell=True, creationflags=0x08000000 if os.name=='nt' else 0)
            return True
        except Exception as e:
            self.safe_log(f"[!] Lỗi tải file: {str(e)}")
            return False

    def is_valid_media(self, filepath):
        try:
            if not os.path.exists(filepath): return False
            size = os.path.getsize(filepath)
            if size < 1024: return False 
            
            ext = os.path.splitext(filepath)[1].lower()
            if ext in ['.mp4', '.webm', '.mkv', '.mov', '.ts']:
                return size > 102400 
            elif ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                return True
            return False
        except: return False

    def task_rename_files(self, target, prefix):
        if not os.path.exists(target): return
        files = sorted([f for f in os.listdir(target) if os.path.isfile(os.path.join(target, f))])
        pad_length = max(3, len(str(len(files)))) 
        
        for idx, f in enumerate(files, 1):
            ext = os.path.splitext(f)[1]
            try: 
                new_name = f"{prefix}_{str(idx).zfill(pad_length)}{ext}" if prefix else f"{str(idx).zfill(pad_length)}{ext}"
                new_path = os.path.join(target, new_name)
                # Tránh lỗi FileExistsError nếu trùng tên
                if not os.path.exists(new_path):
                    os.rename(os.path.join(target, f), new_path)
            except: pass
        self.safe_log(f"[✓] Đã đổi tên chuẩn cho {len(files)} file media.")

    def dl_core_mangadex(self, url_or_id, custom_name, target_base_dir):
        m = re.search(r'([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})', url_or_id)
        if not m:
            self.safe_log("[!] Lỗi: Không tìm thấy ID MangaDex hợp lệ.")
            return False
            
        m_id = m.group(1)
        folder = os.path.join(target_base_dir, custom_name if custom_name else m_id)
        os.makedirs(folder, exist_ok=True)
        self.safe_log(f"[*] MANGADEX: Kéo API Cover của ID {m_id}")
        
        covers, offset = [], 0
        while True:
            api_url = f"https://api.mangadex.org/cover?{urllib.parse.urlencode({'limit': 100, 'offset': offset, 'manga[]': m_id})}"
            try:
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    if "errors" in data: break
                    batch = data.get('data', [])
                    covers.extend(batch)
                    if len(batch) < 100: break
                    offset += 100
            except: break
                
        if not covers:
            self.safe_log("[!] Cảnh báo: Không tìm thấy ảnh cover nào cho MangaDex ID này.")
            return False
            
        for i, c in enumerate(covers, 1):
            fn = c['attributes']['fileName']
            base_path = os.path.join(folder, f"Cover_{i:03d}")
            if not any(os.path.exists(base_path + ext) for ext in ['.jpg', '.png', '.webp', '.gif']):
                fp = base_path + ".tmp"
                self.run_curl_command(f"https://uploads.mangadex.org/covers/{m_id}/{fn}", fp, need_lang=False)
                if self.is_valid_media(fp):
                    final_path = base_path + os.path.splitext(fn)[1]
                    if os.path.exists(final_path): os.remove(final_path)
                    os.rename(fp, final_path)
                elif os.path.exists(fp): os.remove(fp)
                
        self.safe_log(f"[✓] HOÀN TẤT MANGADEX: {custom_name}")
        return True

    def dl_core_down_img(self, url, custom_name, start_num, max_img, target_base_dir):
        self.safe_log(f"[*] DOWN IMG: Bắt đầu dò Đa phương tiện từ {url}")
        m = re.search(r'id-([a-zA-Z0-9]+)', url) or re.search(r'id=([^&]+)', url)
        if not m: return False
        album_id = m.group(1)
        
        try: start_num, max_img = int(start_num), int(max_img)
        except: start_num, max_img = 1, 59
        
        custom_name = re.sub(r'[\\/*?:"<>|]', "", custom_name or f"Album_{album_id}")
        target_dir = os.path.join(target_base_dir, custom_name)
        os.makedirs(target_dir, exist_ok=True)
        
        self.safe_log("  ➔ Chế độ Hình ảnh Sequence (Delay 3-5s chống Block)...")
        saved, miss, i = start_num, 0, start_num
        valid_b = f"https://img.xchina.io/photos/{album_id}"
        download_success = False
        
        while saved < (start_num + max_img) and miss < 5:
            base_path = os.path.join(target_dir, f"{saved:04d}")
            if not any(os.path.exists(base_path + e) for e in ['.jpg', '.png', '.webp']):
                tmp_path = base_path + ".jpg"
                if self.run_curl_command(f"{valid_b}/{i}.jpg", tmp_path, referer=url, need_lang=False) and self.is_valid_media(tmp_path):
                    miss = 0
                    download_success = True
                    self.safe_log(f"    + Tải thành công ảnh {saved:04d}")
                else: 
                    if os.path.exists(tmp_path): os.remove(tmp_path)
                    miss += 1
                time.sleep(random.uniform(2.0, 4.0))
            else: 
                miss, download_success = 0, True
            i += 1
            saved += 1
            
        self.safe_log(f"[✓] HOÀN TẤT DOWN IMG: {custom_name}")
        return download_success

    def task_winrar(self, target, password, del_opt):
        winrar_paths = [r"C:\Program Files\WinRAR\WinRAR.exe", r"C:\Program Files (x86)\WinRAR\WinRAR.exe"]
        winrar_exe = next((p for p in winrar_paths if os.path.exists(p)), None)
        
        if not os.path.exists(target):
            return self.safe_log("[!] Lỗi: Thư mục đích không tồn tại!")

        items = os.listdir(target)
        dirs_to_pack = [i for i in items if os.path.isdir(os.path.join(target, i))]
        
        if not winrar_exe:
            self.safe_log("[!] Chế độ nén ZIP nội bộ (Không hỗ trợ đặt mật khẩu).")
            for item in dirs_to_pack:
                ipath = os.path.join(target, item)
                archive_name = os.path.join(target, item)
                try:
                    shutil.make_archive(archive_name, 'zip', ipath)
                    if os.path.exists(f"{archive_name}.cbz"): os.remove(f"{archive_name}.cbz")
                    os.rename(f"{archive_name}.zip", f"{archive_name}.cbz")
                    if del_opt: shutil.rmtree(ipath, ignore_errors=True)
                except Exception as e: self.safe_log(f"[!] Lỗi đóng gói: {str(e)}")
            return self.safe_log("[✓] HOÀN TẤT ĐÓNG GÓI CBZ (Nội bộ)!")

        self.safe_log(f"[*] Đang đóng gói CBZ bằng WinRAR tại {target}...")
        cmd = [winrar_exe, "a", "-cfg-", "-m0", "-ep1", "-ibck", "-inul", "-x*.bat", "-x*.py"]
        if password: cmd.append(f"-p{password}")
            
        for item in dirs_to_pack:
            ipath = os.path.join(target, item)
            res = subprocess.run(cmd + [os.path.join(target, f"{item}.cbz"), ipath], stdout=subprocess.PIPE, creationflags=0x08000000 if os.name=='nt' else 0)
            if res.returncode in [0, 1] and del_opt: shutil.rmtree(ipath, ignore_errors=True)
        self.safe_log("[✓] HOÀN TẤT ĐÓNG GÓI BẰNG WINRAR!")
        
    def task_zip_video(self, source_path, dest_path):
        if not os.path.exists(source_path):
            return self.safe_log("[!] Lỗi: Không tìm thấy đường dẫn nguồn.")
        if not dest_path.endswith('.zip'): dest_path += '.zip'
            
        self.safe_log(f"[*] Bắt đầu nén Video thành ZIP: {source_path}")
        try:
            with zipfile.ZipFile(dest_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isfile(source_path):
                    zipf.write(source_path, os.path.basename(source_path))
                elif os.path.isdir(source_path):
                    for root, _, files in os.walk(source_path):
                        for file in files:
                            if file.lower().endswith(tuple(self.VIDEO_EXTS)):
                                file_path = os.path.join(root, file)
                                zipf.write(file_path, os.path.relpath(file_path, source_path))
            self.safe_log(f"[✓] HOÀN TẤT NÉN VIDEO: {dest_path}")
        except Exception as e:
            self.safe_log(f"[!] Lỗi khi nén video: {str(e)}")
