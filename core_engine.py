import os, re, time, shutil, subprocess, json, tempfile, random
from urllib.parse import urlparse, urljoin

class CoreEngine:
    def __init__(self, log_callback):
        self.log_callback = log_callback

        # [v160.0] Định nghĩa tập hợp các định dạng hỗ trợ
        self.IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
        self.VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.webm', '.m4v', '.avi'}

    def safe_log(self, text, overwrite=False):
        try: self.log_callback(text, overwrite)
        except: pass

    # [v160.0] Tự động tự điều chỉnh Timeout theo loại file
def run_curl_command(self, url, output_file, referer=None, need_lang=True, is_video=False):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        
        # Nếu là video: Tăng max-time lên 600s (10 phút), hoặc bỏ max-time. Thêm -C - để hỗ trợ resume tải file.
        max_time = 600 if is_video else 30
        
        cmd = f'curl.exe -s -L -C - --compressed --connect-timeout 15 --max-time {max_time} -A "{ua}"'
        if referer: cmd += f' -e "{referer}"'
        if need_lang: cmd += f' -H "Accept-Language: en-US,en;q=0.9"'
        cmd += f' -o "{output_file}" "{url}"'
        
        try:
            # Video có thể tốn tài nguyên, không ẩn hoàn toàn cửa sổ console đối với subprocess nếu cần debug
            subprocess.run(cmd, shell=True, creationflags=0x08000000)
            return True
        except Exception as e:
            self.safe_log(f"[!] Lỗi tải file: {str(e)}\n")
            return False

    # [v160.0] Thay thế/Nâng cấp is_valid_image thành is_valid_media
    def is_valid_media(self, filepath):
        try:
            if not os.path.exists(filepath): return False
            size = os.path.getsize(filepath)
            
            # File quá nhỏ (dưới 1KB) thường là file lỗi hoặc HTML 404
            if size < 1024: return False 
            
            ext = os.path.splitext(filepath)[1].lower()
            video_exts = ['.mp4', '.webm', '.mkv', '.mov', '.ts']
            image_exts = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            
            if ext in video_exts:
                # Video thường phải lớn hơn 100KB
                return size > 102400 
            elif ext in image_exts:
                # Có thể giữ lại logic check header ảnh của bạn ở đây nếu cần thiết
                return True
            else:
                return False
        except:
            return False

    # [v160.0] Đổi tên thông minh giữ nguyên định dạng Ảnh/Video
def task_rename_files(self, target, prefix):
        if not os.path.exists(target): return
        files = sorted([f for f in os.listdir(target) if os.path.isfile(os.path.join(target, f))])
        
        # Tự động tính số chữ số 0 cần đệm (ví dụ: > 100 file thì dùng 001, > 1000 file thì dùng 0001)
        pad_length = max(3, len(str(len(files)))) 
        
        for idx, f in enumerate(files, 1):
            ext = os.path.splitext(f)[1]
            try: 
                new_name = f"{prefix}_{str(idx).zfill(pad_length)}{ext}"
                os.rename(os.path.join(target, f), os.path.join(target, new_name))
            except: pass
        self.safe_log(f"[✓] Đã đổi tên {len(files)} file media.\n")
