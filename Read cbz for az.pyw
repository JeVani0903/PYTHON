import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import re
import os
import ctypes
import base64

# =========================================================================
# ⚙️ CẤU HÌNH CỐ ĐỊNH GOOGLE API KEY TẠI ĐÂY
# =========================================================================
FIXED_GOOGLE_API_KEY = "AIzaSyD8zQpA869UKNitk1jZteUBLLsL_hFLXfE"

if os.name == 'nt':
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 0)
    except: pass

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class CBZApiReaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("E With Bich Jane - Trình Đọc CBZ API (V2 MỚI)")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        self.cover_base64 = "" 
        self.full_html_code = ""

        # --- HEADER ---
        self.lbl_title = ctk.CTkLabel(self, text="⚡ TRÌNH TẠO MÃ ĐỌC CBZ BẰNG GOOGLE API (V2 MỚI)", font=("Arial", 22, "bold"), text_color="#1a73e8")
        self.lbl_title.pack(pady=(15, 5))
        ctk.CTkLabel(self, text="Sửa lỗi nút bấm | Tự động chuyển Link thành ID | Ẩn khung Pass sau khi mở", font=("Arial", 13, "italic"), text_color="#5f6368").pack(pady=(0, 15))

        # --- KHUNG CHÍNH (CHIA 2 CỘT) ---
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # ==========================================
        # CỘT TRÁI: NHẬP THÔNG TIN
        # ==========================================
        left_col = ctk.CTkFrame(main_frame, fg_color="#f8f9fa", border_width=1, border_color="#dadce0", corner_radius=10)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 1. Google API Key 
        ctk.CTkLabel(left_col, text="1. Google Drive API Key (Đã cố định):", font=("Arial", 14, "bold"), text_color="#333").pack(anchor="w", padx=20, pady=(20, 5))
        self.entry_api = ctk.CTkEntry(left_col, height=40, font=("Arial", 14), fg_color="#e8eaed", text_color="#5f6368")
        self.entry_api.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_api.insert(0, FIXED_GOOGLE_API_KEY)
        self.entry_api.configure(state="readonly") 

        # 2. Link Google Drive -> ID
        ctk.CTkLabel(left_col, text="2. Nhập ID hoặc Dán link Google Drive (Sẽ tự động bóc ID):", font=("Arial", 14, "bold"), text_color="#333").pack(anchor="w", padx=20, pady=(10, 5))
        self.entry_link = ctk.CTkEntry(left_col, placeholder_text="Dán Link hoặc nhập ID vào đây...", height=45, font=("Arial", 14))
        self.entry_link.pack(fill="x", padx=20, pady=(0, 15))
        
        # Bắt sự kiện mỗi khi người dùng dán vào ô Link/ID
        self.entry_link.bind("<KeyRelease>", self.auto_format_id)

        # 3. ẢNH COVER 
        ctk.CTkLabel(left_col, text="3. Ảnh Cover (Bị ẩn trong bài, làm Thumbnail ngoài trang chủ):", font=("Arial", 14, "bold"), text_color="#333").pack(anchor="w", padx=20, pady=(10, 5))
        
        cover_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        cover_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_cover = ctk.CTkButton(cover_frame, text="📂 Chọn file ảnh", height=45, fg_color="#f39c12", hover_color="#e08e0b", command=self.select_cover_image)
        self.btn_cover.pack(side="left", padx=(0, 10))

        self.entry_cover_link = ctk.CTkEntry(cover_frame, placeholder_text="Hoặc dán Link ảnh trực tiếp...", height=45, font=("Arial", 14))
        self.entry_cover_link.pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(left_col, fg_color="transparent").pack(fill="both", expand=True)

        # 4. NÚT TẠO MÃ
        self.btn_generate = ctk.CTkButton(left_col, text="🚀 TẠO MÃ NHÚNG (Enter)", height=50, font=("Arial", 15, "bold"), fg_color="#10b981", hover_color="#0d9a6c", command=self.generate_code)
        self.btn_generate.pack(fill="x", padx=20, pady=20)

        # ==========================================
        # CỘT PHẢI: KẾT QUẢ VÀ COPY
        # ==========================================
        right_col = ctk.CTkFrame(main_frame, fg_color="#f8f9fa", border_width=1, border_color="#dadce0", corner_radius=10)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        ctk.CTkLabel(right_col, text="🖥️ ĐOẠN MÃ NHÚNG BLOGSPOT", font=("Arial", 14, "bold"), text_color="#333").pack(anchor="w", padx=20, pady=(20, 5))

        self.textbox_code = ctk.CTkTextbox(right_col, font=("Consolas", 13), fg_color="#1e1e1e", text_color="#00ff00", corner_radius=6)
        self.textbox_code.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.btn_copy = ctk.CTkButton(right_col, text="📋 COPY MÃ & TỰ ĐỘNG XÓA", height=50, font=("Arial", 15, "bold"), fg_color="#e91e63", hover_color="#c2185b", command=self.copy_to_clipboard)
        self.btn_copy.pack(fill="x", padx=20, pady=20)

        self.bind('<Return>', lambda event: self.generate_code())

    def auto_format_id(self, event=None):
        """Tự động chuyển đổi Link Google Drive thành ID ngay khi người dùng dán vào ô"""
        content = self.entry_link.get().strip()
        match = re.search(r'(?:id=|/d/)([\w-]+)', content)
        if match:
            extracted_id = match.group(1)
            # Thay thế nội dung cũ bằng ID đã lọc
            if extracted_id != content:
                self.entry_link.delete(0, tk.END)
                self.entry_link.insert(0, extracted_id)

    def select_cover_image(self):
        filepath = filedialog.askopenfilename(title="Chọn ảnh Cover", filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.gif")])
        if filepath:
            try:
                with open(filepath, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                
                ext = os.path.splitext(filepath)[1][1:].lower()
                if ext == "jpg": ext = "jpeg"
                
                self.cover_base64 = f"data:image/{ext};base64,{b64_string}"
                
                filename = os.path.basename(filepath)
                self.btn_cover.configure(text=f"✅ Đã chọn: {filename[:10]}...")
                self.entry_cover_link.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file ảnh: {e}")

    def generate_code(self):
        # Lúc này nội dung trong ô link chắc chắn chỉ là ID
        file_id = self.entry_link.get().strip()
        api_key = self.entry_api.get().strip()
        cover_link = self.entry_cover_link.get().strip()

        if not file_id:
            messagebox.showwarning("Lỗi", "Vui lòng nhập ID hoặc dán link Google Drive chứa file CBZ!")
            return
        
        # CHỐNG LỖI CÚ PHÁP JAVASCRIPT: Chuẩn hóa ID để dùng cho tên Hàm (Xóa dấu gạch ngang/kí tự lạ)
        safe_id = re.sub(r'[^a-zA-Z0-9]', 'X', file_id)
        
        # Xử lý Cover
        final_cover_src_actual = cover_link if cover_link else self.cover_base64
        final_cover_src_display = cover_link if cover_link else "data:image/... [MÃ BASE64 ĐÃ ĐƯỢC ẨN ĐỂ TRÁNH LAG APP] ..."

        cover_html_block_actual = ""
        cover_html_block_display = ""
        
        if final_cover_src_actual:
            cover_html_block_actual = f"""
<!-- ẢNH THUMBNAIL TÀNG HÌNH -->
<div style="display: none !important; opacity: 0; height: 0; width: 0; overflow: hidden;">
    <img src="{final_cover_src_actual}" alt="Cover Thumbnail" />
</div>
"""
            cover_html_block_display = f"""
<!-- ẢNH THUMBNAIL TÀNG HÌNH -->
<div style="display: none !important; opacity: 0; height: 0; width: 0; overflow: hidden;">
    <img src="{final_cover_src_display}" alt="Cover Thumbnail" />
</div>
"""

        # ==========================================================
        # LÕI MÃ HTML - CẬP NHẬT ẨN BẢNG VÀ CHUẨN HÓA HÀM (SAFE_ID)
        # ==========================================================
        core_html = f"""
<!-- TẢI THƯ VIỆN ZIP.JS -->
<script src="https://unpkg.com/@zip.js/zip.js/dist/zip.min.js"></script>

<!-- KHUNG THÔNG TIN -->
<div id="setup-box-{safe_id}" style="background: rgb(26, 26, 26); border-radius: 10px; color: white; font-family: sans-serif; margin-bottom: 20px; padding: 20px; text-align: center;"> 
    <input id="cbz-password-{safe_id}" placeholder="Mật khẩu giải nén (nếu có)..." onkeypress="if(event.key === 'Enter') fetchFromGoogleAPI_{safe_id}();" style="color: black; border-radius: 5px; border: 1px solid rgb(204, 204, 204); margin-bottom: 10px; max-width: 250px; padding: 10px; width: 60%; outline: none;" type="password" />
    <br />
    
    <button id="read-btn-{safe_id}" onclick="fetchFromGoogleAPI_{safe_id}()" style="background-color: #e91e63; border-radius: 5px; border: none; color: white; cursor: pointer; font-size: 16px; font-weight: bold; padding: 12px 25px; transition: 0.2s;">
        📖 Khởi chạy File Truyện
    </button>
</div>

<!-- KHUNG HIỂN THỊ TRẠNG THÁI -->
<div id="status-box-{safe_id}" style="color: #4caf50; font-weight: bold; margin-bottom: 15px; text-align: center;"></div>

<!-- KHUNG ĐỌC TRUYỆN NGANG -->
<div id="comic-viewer-{safe_id}" style="display: none; background: rgb(44, 44, 44); border-radius: 5px; padding: 10px; text-align: center; position: relative;">
    
    <!-- Thanh điều hướng -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: white;">
        <button onclick="prevPage_{safe_id}()" style="padding: 8px 15px; cursor: pointer; background: #3498db; border: none; color: white; border-radius: 4px; font-weight: bold;">◀ Trước</button>
        <span id="page-counter-{safe_id}" style="font-weight: bold; font-size: 16px; color: #f1c40f;">1 / ?</span>
        <button onclick="nextPage_{safe_id}()" style="padding: 8px 15px; cursor: pointer; background: #3498db; border: none; color: white; border-radius: 4px; font-weight: bold;">Sau ▶</button>
    </div>

    <!-- Vùng hiển thị ảnh -->
    <div style="position: relative; width: 100%; height: 85vh; min-height: 400px; display: flex; justify-content: center; align-items: center; background: #000; overflow: hidden; border-radius: 4px;">
        <div onclick="prevPage_{safe_id}()" style="position: absolute; top: 0; left: 0; width: 50%; height: 100%; cursor: w-resize; z-index: 10;" title="Trang trước"></div>
        <div onclick="nextPage_{safe_id}()" style="position: absolute; top: 0; right: 0; width: 50%; height: 100%; cursor: e-resize; z-index: 10;" title="Trang sau"></div>
        
        <img id="manga-page-{safe_id}" src="" style="max-width: 100%; max-height: 100%; object-fit: contain; user-select: none;" alt="Truyện" />
    </div>
</div>

<script>
    const GOOGLE_API_KEY_{safe_id} = '{api_key}'; 
    const FILE_ID_{safe_id} = '{file_id}';
    
    let imageBlobs_{safe_id} = [];
    let currentIndex_{safe_id} = 0;

    async function fetchFromGoogleAPI_{safe_id}() {{
        const password = document.getElementById('cbz-password-{safe_id}').value;
        const viewer = document.getElementById('comic-viewer-{safe_id}');
        const statusBox = document.getElementById('status-box-{safe_id}');
        const btn = document.getElementById('read-btn-{safe_id}');
        const setupBox = document.getElementById('setup-box-{safe_id}');
        
        btn.disabled = true;
        btn.style.opacity = '0.5';
        viewer.style.display = 'none';
        statusBox.innerText = 'Đang kéo dữ liệu từ Google Drive...';

        try {{
            if (typeof zip === 'undefined') {{
                statusBox.innerText = 'Lỗi: Chưa tải được thư viện zip.js (Vui lòng kiểm tra lại thẻ <head>). Đang thử tải lại...';
                await new Promise((resolve, reject) => {{
                    const script = document.createElement('script');
                    script.src = "https://unpkg.com/@zip.js/zip.js/dist/zip.min.js";
                    script.onload = resolve;
                    script.onerror = () => reject(new Error("Mạng đang chặn thư viện!"));
                    document.head.appendChild(script);
                }});
            }}

            const apiUrl = `https://www.googleapis.com/drive/v3/files/${{FILE_ID_{safe_id}}}?alt=media&key=${{GOOGLE_API_KEY_{safe_id}}}`;
            const response = await fetch(apiUrl);
            
            if (!response.ok) {{
                throw new Error(`Google API từ chối kết nối (Mã lỗi: ${{response.status}}). Hãy kiểm tra lại API Key hoặc quyền chia sẻ của file.`);
            }}
            
            statusBox.innerText = 'Tải xong! Đang mở khóa và giải nén...';
            
            const blob = await response.blob();
            const zipOptions = password ? {{ password: password }} : {{}};
            const zipReader = new zip.ZipReader(new zip.BlobReader(blob), zipOptions);
            const entries = await zipReader.getEntries();
            const imageEntries = entries.filter(entry => !entry.directory && entry.filename.match(/\.(jpg|jpeg|png|webp|gif)$/i));
            
            imageEntries.sort((a, b) => a.filename.localeCompare(b.filename, undefined, {{numeric: true}}));

            if(imageEntries.length === 0) {{
                statusBox.innerText = 'Lỗi: Không tìm thấy ảnh định dạng hợp lệ trong file này.';
                await zipReader.close();
                return;
            }}

            statusBox.innerText = 'Đang xuất hình ảnh ra màn hình...';
            imageBlobs_{safe_id} = [];

            for (let entry of imageEntries) {{
                const imgBlob = await entry.getData(new zip.BlobWriter(), zipOptions);
                imageBlobs_{safe_id}.push(URL.createObjectURL(imgBlob));
            }}
            
            statusBox.innerText = 'Hoàn tất! Hãy sử dụng các nút hoặc phím mũi tên để lật trang.';
            await zipReader.close();

            // Ẩn khung nhập pass và nút Khởi chạy sau khi thành công
            setupBox.style.display = 'none';

            currentIndex_{safe_id} = 0;
            viewer.style.display = 'block';
            renderPage_{safe_id}();

            document.addEventListener('keydown', function(event) {{
                if (viewer.style.display === 'block') {{
                    if (event.key === 'ArrowRight') nextPage_{safe_id}();
                    if (event.key === 'ArrowLeft') prevPage_{safe_id}();
                }}
            }});

        }} catch (error) {{
            console.error(error);
            const errStr = String(error).toLowerCase();
            if (errStr.includes('password') || errStr.includes('invalid password') || errStr.includes('encrypted') || errStr.includes('crc')) {{
                statusBox.innerText = 'Lỗi: Mật khẩu không đúng hoặc file bị mã hóa!';
            }} else {{
                statusBox.innerText = 'Lỗi hệ thống: ' + error.message;
            }}
        }} finally {{
            btn.disabled = false;
            btn.style.opacity = '1';
        }}
    }}

    function renderPage_{safe_id}() {{
        if (imageBlobs_{safe_id}.length === 0) return;
        
        document.getElementById("manga-page-{safe_id}").src = imageBlobs_{safe_id}[currentIndex_{safe_id}];
        document.getElementById("page-counter-{safe_id}").innerText = (currentIndex_{safe_id} + 1) + " / " + imageBlobs_{safe_id}.length;
        
        document.getElementById("comic-viewer-{safe_id}").scrollIntoView({{ behavior: "smooth", block: "start" }});
    }}

    function prevPage_{safe_id}() {{
        if (currentIndex_{safe_id} > 0) {{
            currentIndex_{safe_id}--;
            renderPage_{safe_id}();
        }}
    }}

    function nextPage_{safe_id}() {{
        if (currentIndex_{safe_id} < imageBlobs_{safe_id}.length - 1) {{
            currentIndex_{safe_id}++;
            renderPage_{safe_id}();
        }}
    }}
</script>"""

        self.full_html_code = f"{cover_html_block_actual}{core_html}".strip()
        display_html_code = f"{cover_html_block_display}{core_html}".strip()

        self.textbox_code.delete("1.0", tk.END)
        self.textbox_code.insert("1.0", display_html_code)
        
    def copy_to_clipboard(self):
        if hasattr(self, 'full_html_code') and self.full_html_code:
            self.clipboard_clear()
            self.clipboard_append(self.full_html_code)
            
            self.textbox_code.delete("1.0", tk.END)
            self.entry_link.delete(0, tk.END)
            self.full_html_code = "" 
            
            messagebox.showinfo("Thành công", "Đã copy mã nhúng!\nKhung chứa mã đã tự động làm sạch.")
        else:
            messagebox.showwarning("Lỗi", "Chưa có mã để copy! Hãy nhấn Enter.")

if __name__ == "__main__":
    app = CBZApiReaderApp()
    app.mainloop()
