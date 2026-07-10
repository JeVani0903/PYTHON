import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, colorchooser, ttk, filedialog
import re
import os
import ctypes
import random
import string
import json
import base64

# =========================================================================
# ẨN BẢNG ĐEN & TỐI ƯU HIỆU SUẤT
# =========================================================================
if os.name == 'nt':
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 0)
    except: pass

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

DRIVE_REGEX = re.compile(r'(?:id=|/d/)([\w-]+)')
RE_HTML_TAGS = re.compile(r'<[^>]+>')

def extract_gdrive_id(url):
    if not url: return ""
    match = DRIVE_REGEX.search(url.strip())
    return match.group(1) if match else url.strip()

def remove_dynamic_row(row_frame, row_list):
    row_frame.destroy() 
    row_list[:] = [r for r in row_list if r["frame"] != row_frame]

# =========================================================================
# COMPONENT: BỘ SOẠN THẢO TRỰC QUAN (WYSIWYG RICH TEXT EDITOR)
# =========================================================================
class CTkHTMLEditor(ctk.CTkFrame):
    def __init__(self, master, height=80, placeholder="", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.toolbar = ctk.CTkFrame(self, height=35, fg_color="#e8f0fe", corner_radius=6)
        self.toolbar.pack(fill="x", pady=(0, 5))
        
        btn_b = ctk.CTkButton(self.toolbar, text="B", width=30, font=("Arial", 13, "bold"), fg_color="transparent", text_color="#1a73e8", hover_color="#d2e3fc", command=lambda: self.toggle_tag("b"))
        btn_b.pack(side="left", padx=2, pady=2)
        btn_i = ctk.CTkButton(self.toolbar, text="I", width=30, font=("Arial", 13, "italic"), fg_color="transparent", text_color="#1a73e8", hover_color="#d2e3fc", command=lambda: self.toggle_tag("i"))
        btn_i.pack(side="left", padx=2, pady=2)
        btn_u = ctk.CTkButton(self.toolbar, text="U", width=30, font=("Arial", 13, "underline"), fg_color="transparent", text_color="#1a73e8", hover_color="#d2e3fc", command=lambda: self.toggle_tag("u"))
        btn_u.pack(side="left", padx=2, pady=2)
        ctk.CTkLabel(self.toolbar, text="|", text_color="#a0c2fa").pack(side="left", padx=2)
        btn_color = ctk.CTkButton(self.toolbar, text="Màu Chữ", width=60, font=("Arial", 12, "bold"), fg_color="transparent", text_color="#1a73e8", hover_color="#d2e3fc", command=self.set_color)
        btn_color.pack(side="left", padx=2, pady=2)
        btn_bg = ctk.CTkButton(self.toolbar, text="Bôi Nền", width=60, font=("Arial", 12, "bold"), fg_color="transparent", text_color="#1a73e8", hover_color="#d2e3fc", command=self.set_bg)
        btn_bg.pack(side="left", padx=2, pady=2)

        self.textbox = ctk.CTkTextbox(self, height=height, font=("Arial", 14), wrap="word")
        self.textbox.pack(fill="x", expand=True)
        
        self.tk_text = self.textbox._textbox
        self.tk_text.tag_configure("b", font=("Arial", 14, "bold"))
        self.tk_text.tag_configure("i", font=("Arial", 14, "italic"))
        self.tk_text.tag_configure("u", underline=True)
        
        if placeholder: self.textbox.insert("1.0", placeholder)
            
        self.textbox.bind("<Control-v>", self.custom_paste)
        self.textbox.bind("<Command-v>", self.custom_paste)
            
    def custom_paste(self, event):
        try:
            text = self.clipboard_get()
            text = text.replace('\r\n', '\n').replace('\x0b', '\n').replace('\u2028', '\n').replace('\u2029', '\n').replace('\t', ' ')
            text = re.sub(r'([\.?!])([A-Z])', r'\1 \2', text)
            self.textbox.insert(tk.INSERT, text)
            return "break"
        except: return "break"

    def toggle_tag(self, tag_name):
        try:
            start = self.textbox.index(tk.SEL_FIRST); end = self.textbox.index(tk.SEL_LAST)
            if tag_name in self.tk_text.tag_names(start): self.tk_text.tag_remove(tag_name, start, end)
            else: self.tk_text.tag_add(tag_name, start, end)
        except tk.TclError: pass

    def set_color(self):
        color = colorchooser.askcolor(title="Chọn màu chữ")[1]
        if color:
            tag = f"fg_{color}"
            self.tk_text.tag_configure(tag, foreground=color)
            try:
                start = self.textbox.index(tk.SEL_FIRST); end = self.textbox.index(tk.SEL_LAST)
                for t in self.tk_text.tag_names(start):
                    if t.startswith("fg_"): self.tk_text.tag_remove(t, start, end)
                self.tk_text.tag_add(tag, start, end)
            except tk.TclError: pass

    def set_bg(self):
        color = colorchooser.askcolor(title="Chọn màu nền")[1]
        if color:
            tag = f"bg_{color}"
            self.tk_text.tag_configure(tag, background=color)
            try:
                start = self.textbox.index(tk.SEL_FIRST); end = self.textbox.index(tk.SEL_LAST)
                for t in self.tk_text.tag_names(start):
                    if t.startswith("bg_"): self.tk_text.tag_remove(t, start, end)
                self.tk_text.tag_add(tag, start, end)
            except tk.TclError: pass

    def get_html(self):
        try:
            dump_data = self.tk_text.dump("1.0", "end-1c", tag=True, text=True)
            html_output = ""
            for item_type, value, index in dump_data:
                if item_type == 'text': html_output += value.replace('\n', '<br>')
                elif item_type == 'tagon':
                    if value == 'b': html_output += '<b>'
                    elif value == 'i': html_output += '<i>'
                    elif value == 'u': html_output += '<u>'
                    elif value.startswith('fg_'): html_output += f'<span style="color: {value.split("_")[1]};">'
                    elif value.startswith('bg_'): html_output += f'<span style="background-color: {value.split("_")[1]};">'
                elif item_type == 'tagoff':
                    if value in ('b', 'i', 'u'): html_output += f'</{value}>'
                    elif value.startswith('fg_') or value.startswith('bg_'): html_output += '</span>'
            return html_output
        except: return ""
        
    def get_raw(self): return self.textbox.get("1.0", tk.END).strip()

    def get_state(self):
        try:
            text = self.tk_text.get("1.0", "end-1c")
            tags = []
            for tag in self.tk_text.tag_names():
                if tag in ("sel", "insert"): continue
                ranges = self.tk_text.tag_ranges(tag)
                range_tuples = [(str(ranges[i]), str(ranges[i+1])) for i in range(0, len(ranges), 2)]
                if range_tuples: tags.append({"name": tag, "ranges": range_tuples})
            return json.dumps({"text": text, "tags": tags})
        except: return "{}"

    def load_state(self, state_json):
        self.textbox.delete("1.0", tk.END)
        if not state_json: return
        try:
            data = json.loads(state_json)
            self.textbox.insert("1.0", data.get("text", ""))
            for td in data.get("tags", []):
                t_name = td["name"]
                if t_name.startswith("fg_"): self.tk_text.tag_configure(t_name, foreground=t_name.split("_")[1])
                elif t_name.startswith("bg_"): self.tk_text.tag_configure(t_name, background=t_name.split("_")[1])
                for start, end in td["ranges"]: self.tk_text.tag_add(t_name, start, end)
        except: pass

# =========================================================================
# VIRTUAL UI VIEWS
# =========================================================================
class ItemView(ctk.CTkFrame):
    def __init__(self, master, index, title, on_edit, on_clone, on_delete):
        super().__init__(master, fg_color="#f8f9fa", corner_radius=8, border_width=1, border_color="#e4e3e1")
        self.pack(fill="x", pady=4, padx=5)
        
        disp_title = title if title.strip() else "(Chưa có nội dung)"
        disp = disp_title[:70] + "..." if len(disp_title) > 70 else disp_title
        
        lbl = ctk.CTkLabel(self, text=f"Mục {index}: {disp}", font=("Arial", 14, "bold"), text_color="#1a73e8")
        lbl.pack(side="left", padx=15, pady=12)

        ctk.CTkButton(self, text="❌ Xóa", width=60, fg_color="#e51661", hover_color="#c81054", command=on_delete).pack(side="right", padx=10, pady=10)
        ctk.CTkButton(self, text="📑 Nhân bản", width=80, fg_color="#17a2b8", hover_color="#138496", command=on_clone).pack(side="right", padx=5, pady=10)
        ctk.CTkButton(self, text="✏️ Sửa", width=80, fg_color="#f39c12", hover_color="#e08e0b", command=on_edit).pack(side="right", padx=5, pady=10)

# =========================================================================
# LÕI SOẠN THẢO BÀI GIẢNG 
# =========================================================================
class LectureEditorForm(ctk.CTkFrame):
    def __init__(self, master, app, edit_index=None, data=None):
        super().__init__(master, fg_color="#ffffff", border_width=1, border_color="#dadce0", corner_radius=12)
        self.app = app
        self.edit_index = edit_index
        
        disp_idx = edit_index + 1 if edit_index is not None else len(app.lecture_data) + 1
        
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(hdr, text=f"Đang soạn Bài Giảng {disp_idx}", font=("Arial", 16, "bold"), text_color="#1a73e8").pack(side="left")
        ctk.CTkButton(hdr, text="❌ Hủy bỏ", width=60, fg_color="#6c757d", hover_color="#5a6268", command=self.cancel_edit).pack(side="right")

        tf = ctk.CTkFrame(self, fg_color="transparent")
        tf.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(tf, text="Loại nội dung:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 10))
        self.l_type_var = ctk.StringVar(value="🎬 Video Bài Học")
        ctk.CTkOptionMenu(tf, values=["🎬 Video Bài Học", "📇 Danh sách Flashcard", "📖 Ngữ Pháp", "🎧 Audio Độc Lập"], variable=self.l_type_var, command=self.toggle_inputs).pack(side="left")

        self.entry_title = ctk.CTkEntry(self, placeholder_text="Nhập tiêu đề hiển thị cho mục này...", height=35, font=("Arial", 13, "bold"))
        self.entry_title.pack(fill="x", padx=15, pady=5)
        
        self.dynamic_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dynamic_frame.pack(fill="x", padx=15, pady=5)

        self.link_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
        self.entry_link = ctk.CTkEntry(self.link_frame, placeholder_text="Dán Link Video G-Drive hoặc Link Audio (.mp3) trực tiếp...", height=35)
        self.entry_link.pack(fill="x", pady=2)

        self.fc_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
        self.fc_rows = []
        self.fc_list_frame = ctk.CTkFrame(self.fc_frame, fg_color="transparent")
        self.fc_list_frame.pack(fill="x")
        ctk.CTkButton(self.fc_frame, text="➕ Thêm Từ Vựng", fg_color="#17a2b8", height=30, command=self.add_fc_row).pack(anchor="w", pady=(5, 0))

        self.gr_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
        self.gr_rows = []
        self.gr_list_frame = ctk.CTkFrame(self.gr_frame, fg_color="transparent")
        self.gr_list_frame.pack(fill="x")
        ctk.CTkButton(self.gr_frame, text="➕ Thêm Cấu Trúc Ngữ Pháp", fg_color="#f39c12", height=30, command=self.add_gr_row).pack(anchor="w", pady=(5, 0))

        ctk.CTkButton(self, text="✔ XÁC NHẬN LƯU BÀI GIẢNG", fg_color="#28a745", hover_color="#218838", height=45, font=("Arial", 14, "bold"), command=self.save_data).pack(pady=(15, 20))

        if data: self.load_data(data)
        else: self.add_fc_row(); self.add_gr_row()
        
        self.toggle_inputs(self.l_type_var.get())

    def add_fc_row(self, d=None):
        r = ctk.CTkFrame(self.fc_list_frame, fg_color="transparent"); r.pack(fill="x", pady=2)
        w = ctk.CTkEntry(r, placeholder_text="Từ vựng", height=32); w.pack(side="left", fill="x", expand=True, padx=2)
        m = ctk.CTkEntry(r, placeholder_text="Nghĩa", height=32); m.pack(side="left", fill="x", expand=True, padx=2)
        a = ctk.CTkEntry(r, placeholder_text="Link Audio", height=32); a.pack(side="left", fill="x", expand=True, padx=2)
        i = ctk.CTkEntry(r, placeholder_text="Link Ảnh", height=32); i.pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(r, text="❌", width=30, height=32, fg_color="#e51661", command=lambda: r.destroy() or self.fc_rows.remove(next(item for item in self.fc_rows if item["frame"] == r))).pack(side="left", padx=2)
        if d: w.insert(0, d.get('w','')); m.insert(0, d.get('m','')); a.insert(0, d.get('a','')); i.insert(0, d.get('i',''))
        self.fc_rows.append({"frame": r, "w": w, "m": m, "a": a, "i": i})

    def add_gr_row(self, d=None):
        r = ctk.CTkFrame(self.gr_list_frame, fg_color="#fef7e0", border_width=1, border_color="#fbbc04", corner_radius=8); r.pack(fill="x", pady=5)
        tb = ctk.CTkFrame(r, fg_color="transparent"); tb.pack(fill="x", padx=10, pady=(10, 5))
        t = ctk.CTkEntry(tb, placeholder_text="Tên cấu trúc (VD: Câu điều kiện)", height=32, font=("Arial", 12, "bold")); t.pack(side="left", fill="x", expand=True, padx=(0, 5))
        a = ctk.CTkEntry(tb, placeholder_text="Link Audio", height=32); a.pack(side="left", fill="x", expand=True, padx=5)
        i = ctk.CTkEntry(tb, placeholder_text="Link Ảnh", height=32); i.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(tb, text="❌", width=30, height=32, fg_color="#e51661", command=lambda: r.destroy() or self.gr_rows.remove(next(item for item in self.gr_rows if item["frame"] == r))).pack(side="left")
        ed = CTkHTMLEditor(r, height=100); ed.pack(fill="x", padx=10, pady=(0, 10))
        if d: t.insert(0, d.get('t','')); a.insert(0, d.get('a','')); i.insert(0, d.get('i','')); ed.load_state(d.get('d_state',''))
        self.gr_rows.append({"frame": r, "t": t, "a": a, "i": i, "d": ed})

    def toggle_inputs(self, choice):
        self.link_frame.pack_forget(); self.fc_frame.pack_forget(); self.gr_frame.pack_forget()
        if choice in ["🎬 Video Bài Học", "🎧 Audio Độc Lập"]: self.link_frame.pack(fill="x")
        elif choice == "📇 Danh sách Flashcard": self.fc_frame.pack(fill="x")
        elif choice == "📖 Ngữ Pháp": self.gr_frame.pack(fill="x")

    def load_data(self, data):
        self.l_type_var.set(data.get('type', "🎬 Video Bài Học"))
        self.entry_title.insert(0, data.get('title', ''))
        self.entry_link.insert(0, data.get('link', ''))
        for r in data.get('fc_rows', []): self.add_fc_row(r)
        for r in data.get('gr_rows', []): self.add_gr_row(r)
        if not self.fc_rows: self.add_fc_row()
        if not self.gr_rows: self.add_gr_row()

    def save_data(self):
        data = {
            "type": self.l_type_var.get(),
            "title": self.entry_title.get().strip(),
            "link": self.entry_link.get().strip(),
            "fc_rows": [{"w": r["w"].get().strip(), "m": r["m"].get().strip(), "a": r["a"].get().strip(), "i": r["i"].get().strip()} for r in self.fc_rows],
            "gr_rows": [{"t": r["t"].get().strip(), "a": r["a"].get().strip(), "i": r["i"].get().strip(), "d_html": r["d"].get_html(), "d_state": r["d"].get_state()} for r in self.gr_rows]
        }
        self.app.commit_lecture_edit(data, self.edit_index)

    def cancel_edit(self):
        self.app.cancel_edit()

# =========================================================================
# LÕI SOẠN THẢO BÀI TẬP (STUDIO MODE 2 CỘT)
# =========================================================================
class QuizEditorForm(ctk.CTkFrame):
    def __init__(self, master, app, edit_index=None, data=None):
        super().__init__(master, fg_color="#ffffff", border_width=1, border_color="#dadce0", corner_radius=12)
        self.app = app
        self.edit_index = edit_index
        
        disp_idx = edit_index + 1 if edit_index is not None else len(app.quiz_data) + 1
        
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(hdr, text=f"Đang soạn Câu hỏi {disp_idx}", font=("Arial", 16, "bold"), text_color="#1a73e8").pack(side="left")
        
        self.btn_toggle = ctk.CTkButton(hdr, text="👁 Ẩn/Hiện Cột", width=120, fg_color="#f39c12", hover_color="#e08e0b", font=("Arial", 12, "bold"), command=self.toggle_body)
        self.btn_toggle.pack(side="right", padx=(10, 0))
        ctk.CTkButton(hdr, text="❌ Hủy bỏ", width=60, fg_color="#6c757d", hover_color="#5a6268", command=self.cancel_edit).pack(side="right", padx=5)

        self.entry_q_topic = ctk.CTkEntry(self, placeholder_text="📌 Nhập chủ đề câu hỏi (Tùy chọn)...", height=35, font=("Arial", 13, "bold"), fg_color="#e8f0fe", text_color="#1a73e8")
        self.entry_q_topic.pack(fill="x", padx=15, pady=(5, 0))

        self.body_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # --- CỘT 1 ---
        self.left_col = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        self.left_col.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(self.left_col, text="Nội dung câu hỏi (Dán link Ảnh/Audio thẳng vào):", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 0))
        self.entry_question = CTkHTMLEditor(self.left_col, height=350)
        self.entry_question.pack(fill="both", expand=True, pady=5)

        # --- CỘT 2 ---
        self.right_col = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        self.right_col.pack(side="right", fill="both", expand=True, padx=(5, 0))

        tf = ctk.CTkFrame(self.right_col, fg_color="transparent")
        tf.pack(fill="x", pady=5)
        ctk.CTkLabel(tf, text="Loại câu hỏi:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 10))
        self.q_type_var = ctk.StringVar(value="Trắc nghiệm")
        ctk.CTkOptionMenu(tf, values=["Trắc nghiệm", "Điền từ (Ngắn)", "Nối câu"], variable=self.q_type_var, command=self.toggle_inputs).pack(side="left")

        self.dynamic_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.dynamic_frame.pack(fill="both", expand=True, pady=5)

        # Trắc nghiệm
        self.mcq_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
        ctk.CTkLabel(self.mcq_frame, text="* Mẹo: Dán thẳng link Google Drive HOẶC link .mp3", font=("Arial", 11, "italic"), text_color="#656e77").pack(anchor="w", pady=(0, 5))
        self.opt_a = ctk.CTkEntry(self.mcq_frame, placeholder_text="Đáp án A", height=35); self.opt_a.pack(fill="x", pady=2)
        self.opt_b = ctk.CTkEntry(self.mcq_frame, placeholder_text="Đáp án B", height=35); self.opt_b.pack(fill="x", pady=2)
        self.opt_c = ctk.CTkEntry(self.mcq_frame, placeholder_text="Đáp án C", height=35); self.opt_c.pack(fill="x", pady=2)
        self.opt_d = ctk.CTkEntry(self.mcq_frame, placeholder_text="Đáp án D", height=35); self.opt_d.pack(fill="x", pady=2)
        
        af = ctk.CTkFrame(self.mcq_frame, fg_color="transparent"); af.pack(fill="x", pady=5)
        ctk.CTkLabel(af, text="Đáp án ĐÚNG:").pack(side="left", padx=(0, 10))
        self.mcq_correct = ctk.CTkOptionMenu(af, values=["A", "B", "C", "D"], width=70)
        self.mcq_correct.pack(side="left")

        # Điền từ
        self.fill_frame = ctk.CTkScrollableFrame(self.dynamic_frame, fg_color="transparent")
        ctk.CTkLabel(self.fill_frame, text="Mỗi dòng 1 ô cần điền (Nhiều đáp án cách nhau bằng dấu phẩy):", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0,5))
        self.fill_rows = []
        self.fill_list_frame = ctk.CTkFrame(self.fill_frame, fg_color="transparent"); self.fill_list_frame.pack(fill="x")
        ctk.CTkButton(self.fill_frame, text="➕ Thêm Câu Trả Lời", fg_color="#17a2b8", height=30, command=self.add_fill_row).pack(anchor="w", pady=(5, 0))

        # Nối câu
        self.match_frame = ctk.CTkScrollableFrame(self.dynamic_frame, fg_color="transparent")
        ctk.CTkLabel(self.match_frame, text="Nhập các cặp Nối câu (Hệ thống tự đảo lộn vế phải):", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0,5))
        self.match_rows = []
        self.match_list_frame = ctk.CTkFrame(self.match_frame, fg_color="transparent"); self.match_list_frame.pack(fill="x")
        ctk.CTkButton(self.match_frame, text="➕ Thêm Cặp Nối", fg_color="#17a2b8", height=30, command=self.add_match_row).pack(anchor="w", pady=(5, 0))

        ctk.CTkLabel(self.right_col, text="Giải thích / Đáp án mẫu:", anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=(10, 0))
        self.text_explanation = CTkHTMLEditor(self.right_col, height=100)
        self.text_explanation.pack(fill="both", expand=True, pady=(5, 10))

        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.pack(fill="x", padx=15, pady=(15, 20))
        ctk.CTkButton(self.bottom_frame, text="✔ XÁC NHẬN LƯU CÂU HỎI", fg_color="#28a745", hover_color="#218838", height=45, font=("Arial", 14, "bold"), command=self.save_data).pack()

        if data: self.load_data(data)
        else: self.add_fill_row(); self.add_match_row()
        
        self.toggle_inputs(self.q_type_var.get())

    def toggle_body(self):
        if self.body_frame.winfo_ismapped():
            self.body_frame.pack_forget()
        else:
            self.body_frame.pack(fill="both", expand=True, padx=15, pady=5, before=self.bottom_frame)

    def add_fill_row(self, d=""):
        r = ctk.CTkFrame(self.fill_list_frame, fg_color="transparent"); r.pack(fill="x", pady=2)
        lbl = ctk.CTkLabel(r, text=f"Ô {len(self.fill_rows)+1}:", font=("Arial", 12, "bold"), width=40, anchor="w"); lbl.pack(side="left", padx=(0, 5))
        ans = ctk.CTkEntry(r, placeholder_text="Đáp án", height=32); ans.pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(r, text="❌", width=30, height=32, fg_color="#e51661", command=lambda: r.destroy() or self.fill_rows.remove(next(item for item in self.fill_rows if item["frame"] == r))).pack(side="left", padx=2)
        if d: ans.insert(0, d)
        self.fill_rows.append({"frame": r, "ans": ans, "lbl": lbl})
        self.reindex_fill_rows()

    def add_match_row(self, d=None):
        r = ctk.CTkFrame(self.match_list_frame, fg_color="transparent"); r.pack(fill="x", pady=2)
        lbl = ctk.CTkLabel(r, text=f"{len(self.match_rows)+1}.", font=("Arial", 12, "bold")); lbl.pack(side="left", padx=(0, 5))
        left = ctk.CTkEntry(r, placeholder_text="Vế trái", height=32); left.pack(side="left", fill="x", expand=True, padx=2)
        right = ctk.CTkEntry(r, placeholder_text="Vế phải (Đúng)", height=32); right.pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(r, text="❌", width=30, height=32, fg_color="#e51661", command=lambda: r.destroy() or self.match_rows.remove(next(item for item in self.match_rows if item["frame"] == r))).pack(side="left", padx=2)
        if d: left.insert(0, d.get('l','')); right.insert(0, d.get('r',''))
        self.match_rows.append({"frame": r, "l": left, "r": right, "lbl": lbl})
        self.reindex_match_rows()

    def reindex_fill_rows(self):
        for i, row in enumerate(self.fill_rows): row["lbl"].configure(text=f"Ô {i+1}:")
        
    def reindex_match_rows(self):
        for i, row in enumerate(self.match_rows): row["lbl"].configure(text=f"{i+1}.")

    def toggle_inputs(self, choice):
        self.mcq_frame.pack_forget(); self.fill_frame.pack_forget(); self.match_frame.pack_forget()
        if choice == "Trắc nghiệm": self.mcq_frame.pack(fill="both", expand=True)
        elif choice == "Điền từ (Ngắn)": self.fill_frame.pack(fill="both", expand=True)
        elif choice == "Nối câu": self.match_frame.pack(fill="both", expand=True)

    def load_data(self, data):
        self.entry_q_topic.insert(0, data.get('topic', ''))
        self.entry_question.load_state(data.get('q_state', ''))
        self.q_type_var.set(data.get('q_type', 'Trắc nghiệm'))
        
        mcq = data.get('mcq', {})
        self.opt_a.insert(0, mcq.get('a', '')); self.opt_b.insert(0, mcq.get('b', ''))
        self.opt_c.insert(0, mcq.get('c', '')); self.opt_d.insert(0, mcq.get('d', ''))
        if mcq.get('correct'): self.mcq_correct.set(mcq['correct'])

        for f_ans in data.get('fills', []): self.add_fill_row(f_ans)
        for m_data in data.get('matches', []): self.add_match_row(m_data)
        
        if not self.fill_rows: self.add_fill_row()
        if not self.match_rows: self.add_match_row()
        
        self.text_explanation.load_state(data.get('exp_state', ''))

    def save_data(self):
        data = {
            "topic": self.entry_q_topic.get().strip(),
            "q_raw": self.entry_question.get_raw(),
            "q_html": self.entry_question.get_html(),
            "q_state": self.entry_question.get_state(),
            "q_type": self.q_type_var.get(),
            "mcq": {
                "a": self.opt_a.get().strip(), "b": self.opt_b.get().strip(),
                "c": self.opt_c.get().strip(), "d": self.opt_d.get().strip(),
                "correct": self.mcq_correct.get()
            },
            "fills": [r["ans"].get().strip() for r in self.fill_rows],
            "matches": [{"l": r["l"].get().strip(), "r": r["r"].get().strip()} for r in self.match_rows],
            "exp_raw": self.text_explanation.get_raw(),
            "exp_html": self.text_explanation.get_html(),
            "exp_state": self.text_explanation.get_state()
        }
        self.app.commit_quiz_edit(data, self.edit_index)

    def cancel_edit(self):
        self.app.cancel_edit()

# =========================================================================
# LÕI ỨNG DỤNG CHÍNH (V266.0 - SMART HEADER INTEGRATION)
# =========================================================================
class BJ2SystemApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("E With Bich Jane - V266.0 (Smart Header Integration)")
        self.geometry("1300x850")
        self.minsize(1100, 700)
        
        self.lecture_data = []
        self.quiz_data = []
        self.global_cover_base64 = "" 
        
        self.active_editor = None
        self.current_tab = "Bài Giảng"

        self.setup_ui()
        self.open_lecture_editor()

    def setup_ui(self):
        self.side_frame = ctk.CTkFrame(self, width=400, fg_color="#ffffff", border_width=1, border_color="#e4e3e1")
        self.side_frame.pack(side="right", fill="y", padx=10, pady=10)
        self.side_frame.pack_propagate(False)

        ctk.CTkLabel(self.side_frame, text="BẢNG ĐIỀU KHIỂN", font=("Arial", 18, "bold")).pack(fill="x", padx=10, pady=(20, 10))
        ctk.CTkButton(self.side_frame, text="🔄 LÀM MỚI BÀI SOẠN", height=45, font=("Arial", 13, "bold"), fg_color="#dc3545", hover_color="#c82333", command=self.reset_all).pack(fill="x", padx=20, pady=(10, 20))
        ctk.CTkButton(self.side_frame, text="🚀 XUẤT MÃ / DỮ LIỆU", height=55, font=("Arial", 15, "bold"), fg_color="#10b981", hover_color="#0d9a6c", command=self.generate_code).pack(fill="x", padx=20, pady=10)
        
        self.output_text = ctk.CTkTextbox(self.side_frame, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#00ff00", wrap="none")
        self.output_text.pack(fill="both", expand=True, padx=20, pady=10)
        ctk.CTkButton(self.side_frame, text="📋 COPY CLIPBOARD", height=45, font=("Arial", 14, "bold"), fg_color="#e91e63", hover_color="#c2185b", command=self.copy_code).pack(fill="x", padx=20, pady=(0, 20))

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.tab_var = tk.StringVar(value="Bài Giảng")
        seg = ctk.CTkSegmentedButton(self.main_container, values=["Cấu Hình Chung", "Bài Giảng", "Bài Tập", "Học Sinh"], variable=self.tab_var, command=self.switch_tab, font=("Arial", 15, "bold"), height=40)
        seg.pack(fill="x", pady=(0, 10))

        self.tab_config_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_lecture_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_quiz_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_student_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")

        # --- CẤU TRÚC TAB CẤU HÌNH CHUNG ---
        cf = ctk.CTkFrame(self.tab_config_frame, fg_color="#ffffff", border_width=1, border_color="#dadce0", corner_radius=12)
        cf.pack(fill="x", pady=10)
        ctk.CTkLabel(cf, text="CẤU HÌNH BÀI VIẾT (Áp dụng chung)", font=("Arial", 16, "bold"), text_color="#1a73e8").pack(anchor="w", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(cf, text="Ảnh Cover (Tàng hình trong bài, làm Thumbnail Blogspot):", font=("Arial", 13, "bold"), text_color="#e51661").pack(anchor="w", padx=15, pady=(10, 0))
        self.entry_global_cover = ctk.CTkEntry(cf, placeholder_text="Dán Link ảnh Cover trực tiếp vào đây...", height=40, font=("Arial", 13))
        self.entry_global_cover.pack(fill="x", padx=15, pady=5)
        
        self.btn_global_cover = ctk.CTkButton(cf, text="📂 Click chọn file ảnh từ máy tính", height=40, fg_color="#f39c12", hover_color="#e08e0b", command=self.select_global_cover)
        self.btn_global_cover.pack(anchor="w", padx=15, pady=(0, 15))

        # --- CẤU TRÚC TAB BÀI GIẢNG ---
        self.lec_list_scroll = ctk.CTkScrollableFrame(self.tab_lecture_frame, fg_color="transparent")
        self.btn_add_lec = ctk.CTkButton(self.tab_lecture_frame, text="➕ THÊM MỤC BÀI GIẢNG", height=45, fg_color="#3740ff", command=self.open_lecture_editor)

        # --- CẤU TRÚC TAB BÀI TẬP ---
        self.quiz_list_scroll = ctk.CTkScrollableFrame(self.tab_quiz_frame, fg_color="transparent")
        self.btn_add_quiz = ctk.CTkButton(self.tab_quiz_frame, text="➕ THÊM CÂU HỎI", height=45, fg_color="#3740ff", command=self.open_quiz_editor)

        # --- CẤU TRÚC TAB HỌC SINH ---
        st_input = ctk.CTkFrame(self.tab_student_frame, fg_color="#ffffff", border_width=1, border_color="#dadce0", corner_radius=12)
        st_input.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(st_input, text="Nhập tay Học sinh mới", font=("Arial", 14, "bold"), text_color="#1a73e8").pack(anchor="w", padx=15, pady=(15, 5))
        
        row1 = ctk.CTkFrame(st_input, fg_color="transparent"); row1.pack(fill="x", padx=15, pady=5)
        self.st_user = ctk.CTkEntry(row1, placeholder_text="Tên / Username", height=35); self.st_user.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.st_pass = ctk.CTkEntry(row1, placeholder_text="Mật khẩu", height=35); self.st_pass.pack(side="left", fill="x", expand=True, padx=5)
        self.st_class = ctk.CTkEntry(row1, placeholder_text="Lớp", height=35); self.st_class.pack(side="left", fill="x", expand=True, padx=(5, 10))
        ctk.CTkButton(row1, text="➕ Thêm", width=80, height=35, fg_color="#28a745", hover_color="#218838", command=self.add_student).pack(side="left")
        ctk.CTkButton(st_input, text="📄 Nhập hàng loạt từ file .TXT (Cú pháp: Tên; Pass; Lớp)", height=40, fg_color="#f39c12", hover_color="#e08e0b", command=self.import_students_txt).pack(fill="x", padx=15, pady=(10, 15))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#ffffff", foreground="#000000", rowheight=30, fieldbackground="#ffffff", borderwidth=0, font=('Arial', 12))
        style.map('Treeview', background=[('selected', '#1a73e8')])
        style.configure("Treeview.Heading", background="#f8f9fa", foreground="#1a73e8", font=('Arial', 12, 'bold'))

        self.student_tree = ttk.Treeview(self.tab_student_frame, columns=("user", "pass", "class"), show="headings", height=15)
        self.student_tree.heading("user", text="Tên / Username")
        self.student_tree.heading("pass", text="Mật khẩu")
        self.student_tree.heading("class", text="Lớp")
        self.student_tree.pack(fill="both", expand=True)
        ctk.CTkButton(self.tab_student_frame, text="❌ Xóa các học sinh đang chọn", height=40, fg_color="#e51661", hover_color="#c81054", command=self.delete_students).pack(fill="x", pady=(15, 0))

        self.switch_tab("Bài Giảng")

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        self.cancel_edit()
        self.tab_config_frame.pack_forget(); self.tab_lecture_frame.pack_forget(); self.tab_quiz_frame.pack_forget(); self.tab_student_frame.pack_forget()
        
        if tab_name == "Cấu Hình Chung":
            self.tab_config_frame.pack(fill="both", expand=True)
        elif tab_name == "Bài Giảng":
            self.tab_lecture_frame.pack(fill="both", expand=True)
            self.refresh_lecture_list()
        elif tab_name == "Bài Tập":
            self.tab_quiz_frame.pack(fill="both", expand=True)
            self.refresh_quiz_list()
        elif tab_name == "Học Sinh":
            self.tab_student_frame.pack(fill="both", expand=True)

    def refresh_lecture_list(self):
        try:
            if self.active_editor: 
                self.active_editor.destroy()
                self.active_editor = None
            
            for w in self.lec_list_scroll.winfo_children(): 
                w.destroy()
            
            self.btn_add_lec.pack_forget()
            
            if len(self.lecture_data) > 0:
                self.lec_list_scroll.pack(fill="both", expand=True, padx=10, pady=5)
                for i, data in enumerate(self.lecture_data):
                    title = data.get('title') or data.get('type')
                    ItemView(self.lec_list_scroll, i+1, title, 
                             lambda idx=i: self.open_lecture_editor(idx),
                             lambda idx=i: self.clone_lecture(idx),
                             lambda idx=i: self.delete_lecture(idx))
            else:
                self.lec_list_scroll.pack_forget()
            
            self.btn_add_lec.pack(fill="x", padx=15, pady=10)
        except Exception: pass

    def open_lecture_editor(self, edit_index=None):
        try:
            self.lec_list_scroll.pack_forget()
            self.btn_add_lec.pack_forget()
            data = self.lecture_data[edit_index] if edit_index is not None else None
            self.active_editor = LectureEditorForm(self.tab_lecture_frame, self, edit_index, data)
            self.active_editor.pack(fill="both", expand=True, pady=5)
        except Exception: pass

    def commit_lecture_edit(self, data, edit_index):
        if edit_index is not None: self.lecture_data[edit_index] = data
        else: self.lecture_data.append(data)
        self.refresh_lecture_list()

    def clone_lecture(self, index):
        self.lecture_data.insert(index + 1, dict(self.lecture_data[index]))
        self.refresh_lecture_list()

    def delete_lecture(self, index):
        del self.lecture_data[index]
        self.refresh_lecture_list()

    def refresh_quiz_list(self):
        try:
            if self.active_editor: 
                self.active_editor.destroy()
                self.active_editor = None
            
            for w in self.quiz_list_scroll.winfo_children(): 
                w.destroy()
            
            self.btn_add_quiz.pack_forget()
            
            if len(self.quiz_data) > 0:
                self.quiz_list_scroll.pack(fill="both", expand=True, padx=10, pady=5)
                for i, data in enumerate(self.quiz_data):
                    title = data.get('topic') or data.get('q_raw')[:50]
                    if not title: title = "Câu hỏi " + data.get('q_type')
                    ItemView(self.quiz_list_scroll, i+1, title, 
                             lambda idx=i: self.open_quiz_editor(idx),
                             lambda idx=i: self.clone_quiz(idx),
                             lambda idx=i: self.delete_quiz(idx))
            else:
                self.quiz_list_scroll.pack_forget() 
            
            self.btn_add_quiz.pack(fill="x", padx=15, pady=10)
        except Exception: pass

    def open_quiz_editor(self, edit_index=None):
        try:
            self.quiz_list_scroll.pack_forget()
            self.btn_add_quiz.pack_forget()
            data = self.quiz_data[edit_index] if edit_index is not None else None
            self.active_editor = QuizEditorForm(self.tab_quiz_frame, self, edit_index, data)
            self.active_editor.pack(fill="both", expand=True, pady=5)
        except Exception: pass

    def commit_quiz_edit(self, data, edit_index):
        if edit_index is not None: self.quiz_data[edit_index] = data
        else: self.quiz_data.append(data)
        self.refresh_quiz_list()

    def clone_quiz(self, index):
        self.quiz_data.insert(index + 1, dict(self.quiz_data[index]))
        self.refresh_quiz_list()

    def delete_quiz(self, index):
        del self.quiz_data[index]
        self.refresh_quiz_list()

    def cancel_edit(self):
        if self.current_tab == "Bài Giảng": self.refresh_lecture_list()
        elif self.current_tab == "Bài Tập": self.refresh_quiz_list()

    def add_student(self):
        u = self.st_user.get().strip(); p = self.st_pass.get().strip(); c = self.st_class.get().strip()
        if u and p and c:
            self.student_tree.insert("", "end", values=(u, p, c))
            self.st_user.delete(0, tk.END); self.st_pass.delete(0, tk.END); self.st_class.delete(0, tk.END)
        else: messagebox.showwarning("Lỗi", "Vui lòng nhập đủ Tên, Pass và Lớp!")

    def import_students_txt(self):
        filepath = filedialog.askopenfilename(title="Chọn file TXT Học Sinh", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f: lines = f.readlines()
        except: return
        count = 0
        for line in lines:
            parts = line.split(';')
            if len(parts) >= 3:
                u, p, c = parts[0].strip(), parts[1].strip(), parts[2].strip()
                if u and p and c:
                    self.student_tree.insert("", "end", values=(u, p, c))
                    count += 1
        messagebox.showinfo("Thành công", f"Đã nhập {count} học sinh!")

    def delete_students(self):
        for item in self.student_tree.selection(): self.student_tree.delete(item)

    def reset_all(self):
        if not messagebox.askyesno("Cảnh báo", "Xóa toàn bộ Bài giảng và Bài tập?\n(Danh sách học sinh sẽ KHÔNG bị xóa)"): return
        self.lecture_data.clear(); self.quiz_data.clear()
        self.output_text.delete("1.0", tk.END)
        if self.current_tab == "Bài Giảng": self.refresh_lecture_list()
        elif self.current_tab == "Bài Tập": self.refresh_quiz_list()

    def copy_code(self):
        try:
            code = self.output_text.get("1.0", tk.END).strip()
            if code:
                self.clipboard_clear(); self.clipboard_append(code)
                messagebox.showinfo("Thành công", "Đã copy nội dung vào Clipboard!")
        except Exception: pass

    def select_global_cover(self):
        filepath = filedialog.askopenfilename(title="Chọn ảnh Cover", filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.gif")])
        if filepath:
            file_size = os.path.getsize(filepath)
            if file_size > 1.5 * 1024 * 1024:
                messagebox.showwarning("Cảnh báo", "Ảnh có dung lượng khá lớn (>1.5MB)!\n\nMã Base64 sinh ra sẽ rất dài. Ứng dụng vẫn xử lý được nhưng có thể mất vài giây.\n\n💡 Khuyên dùng: Dán Link Ảnh trực tiếp vào ô, hoặc nén nhỏ ảnh lại trước khi tải.")
            try:
                with open(filepath, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                ext = os.path.splitext(filepath)[1][1:].lower()
                if ext == "jpg": ext = "jpeg"
                self.global_cover_base64 = f"data:image/{ext};base64,{b64_string}"
                filename = os.path.basename(filepath)
                self.btn_global_cover.configure(text=f"✅ Đã tải: {filename[:15]}...")
                self.entry_global_cover.delete(0, tk.END) 
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file ảnh: {e}")

    def optimize_url(self, url):
        url = url.strip()
        gh_pattern = r'https://github\.com/([^/]+)/([^/]+)/raw/(?:refs/heads/)?([^/]+)/(.*)'
        match = re.search(gh_pattern, url)
        if match:
            u, r, b, f = match.groups()
            return f"https://cdn.jsdelivr.net/gh/{u}/{r}@{b}/{f}"
        return url

    def parse_media(self, txt, sys_id):
        audio_btn = ""
        img_html = ""
        display_txt = txt
        
        urls = re.findall(r'(https?://[^\s<"]+)', txt)
        for raw_url in urls:
            url = self.optimize_url(raw_url)
            url_lower = url.lower()
            
            if ".mp3" in url_lower or "audio" in url_lower:
                audio_btn = f'<button type="button" class="audio-icon-btn" onclick="playGlobalAudio_{sys_id}(\'{url}\')" style="margin: 0 0 0 10px; flex-shrink: 0; width: 35px; height: 35px; font-size: 16px;">🔊</button>'
                display_txt = display_txt.replace(raw_url, '')
            elif "drive.google.com" in url_lower or "id=" in url_lower:
                g_id = extract_gdrive_id(url)
                if g_id:
                    img_html = f'<img src="https://drive.google.com/thumbnail?id={g_id}&sz=w400" loading="lazy" style="max-height: 80px; max-width: 150px; border-radius: 6px; margin-right: 10px; object-fit: contain;">'
                    display_txt = display_txt.replace(raw_url, '')
            elif any(ext in url_lower for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']) or "cdn.jsdelivr.net" in url_lower:
                img_html = f'<img src="{url}" loading="lazy" style="max-height: 80px; max-width: 150px; border-radius: 6px; margin-right: 10px; object-fit: contain;">'
                display_txt = display_txt.replace(raw_url, '')

        display_txt = re.sub(r'^(?:<br>|\s)+', '', display_txt)
        display_txt = re.sub(r'(?:<br>|\s)+$', '', display_txt).strip()
        return display_txt, img_html, audio_btn

    def parse_audio(self, txt, sys_id):
        txt, img, aud = self.parse_media(txt, sys_id)
        return txt, aud

    def generate_code(self):
        try:
            if self.active_editor and hasattr(self.active_editor, 'save_data'):
                self.active_editor.save_data()
            self._generate_code_internal()
        except Exception as e:
            messagebox.showerror("Lỗi khi xuất mã", f"Đã có lỗi xảy ra: {str(e)}\nVui lòng kiểm tra lại nội dung.")

    def _generate_code_internal(self):
        if self.current_tab == "Học Sinh":
            student_js = ""
            for child in self.student_tree.get_children():
                vals = self.student_tree.item(child, 'values')
                u = str(vals[0]).replace("'", "\\'"); p = str(vals[1]).replace("'", "\\'"); c = str(vals[2]).replace("'", "\\'")
                student_js += f"    '{u}': {{ pass: '{p}', class: '{c}' }},\n"
            self.output_text.delete("1.0", tk.END); self.output_text.insert(tk.END, student_js)
            messagebox.showinfo("Hoàn tất", "Chỉ hiển thị dữ liệu Học sinh.\nHãy bấm COPY CLIPBOARD.")
            return

        sys_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        lec_html_parts = []
        
        # --- BUILD BÀI GIẢNG ---
        for blk in self.lecture_data:
            b_type = blk.get('type')
            title = blk.get('title') or b_type
            
            if b_type == "🎬 Video Bài Học":
                v_id = extract_gdrive_id(blk.get('link', ''))
                if v_id: lec_html_parts.append(f'<div class="lecture-section"><h3 class="section-title">🎬 {title}</h3><div class="video-container"><iframe src="https://drive.google.com/file/d/{v_id}/preview" allow="autoplay" allowfullscreen></iframe></div></div>')
            
            elif b_type == "📇 Danh sách Flashcard":
                valid_rows = [r for r in blk.get('fc_rows', []) if r['w'] or r['m']]
                if not valid_rows: continue
                fc_content_parts = []
                for i, row in enumerate(valid_rows):
                    word = row['w']; mean = row['m']; a_url = self.optimize_url(row['a']); i_id = extract_gdrive_id(row['i'])
                    audio_btn = f'''<button type="button" class="audio-icon-btn" onclick="playGlobalAudio_{sys_id}('{a_url}')" title="Nghe phát âm">🔊</button>''' if a_url else ""
                    img_col = f'''<div class="fc-img-col"><img src="https://drive.google.com/thumbnail?id={i_id}&sz=w800" loading="lazy" class="fc-img"></div>''' if i_id else ""
                    display_style = 'display: block;' if i == 0 else 'display: none;'
                    fc_content_parts.append(f'<div class="flashcard fc-slide-{sys_id}" style="{display_style}"><div class="flashcard-body">{img_col}<div class="fc-text-col"><strong class="fc-word">{word}</strong><span class="fc-meaning">{mean}</span>{audio_btn}</div></div></div>')
                
                nav_btns_top = ""
                if len(valid_rows) > 1:
                    nav_style = "display: inline-flex; align-items: center; background: #f8f9fa; padding: 4px 10px; border-radius: 6px; border: 1px solid #dadce0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"
                    nav_btns_top = f'<div style="{nav_style}"><button type="button" class="nav-control-btn" onclick="moveFcSlide_{sys_id}(-1)">&#10094; Trước</button><span class="fc-counter" id="fc-counter-top-{sys_id}">1 / {len(valid_rows)}</span><button type="button" class="nav-control-btn" onclick="moveFcSlide_{sys_id}(1)">Sau &#10095;</button></div>'
                
                header_html = f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;"><h3 class="section-title" style="margin-bottom: 0;">📇 {title}</h3>{nav_btns_top}</div>'
                lec_html_parts.append(f'<div class="lecture-section">{header_html}<div class="slider-container-main"><div class="flashcard-container">{"".join(fc_content_parts)}</div></div></div>')
            
            elif b_type == "📖 Ngữ Pháp":
                valid_gr = [r for r in blk.get('gr_rows', []) if r["t"] or r["d_html"]]
                if not valid_gr: continue
                gr_content_parts = []
                for i, row in enumerate(valid_gr):
                    struct = row['t']; a_url = self.optimize_url(row['a']); i_id = extract_gdrive_id(row['i']); desc = row['d_html']
                    audio_btn = f'''<button type="button" class="audio-icon-btn" onclick="playGlobalAudio_{sys_id}('{a_url}')" title="Nghe giải thích">🔊</button>''' if a_url else ""
                    img_col = f'''<div class="fc-img-col"><img src="https://drive.google.com/thumbnail?id={i_id}&sz=w800" loading="lazy" class="fc-img"></div>''' if i_id else ""
                    display_style = 'display: block;' if i == 0 else 'display: none;'
                    gr_content_parts.append(f'<div class="grammar-box gr-slide-{sys_id}" style="{display_style}"><div class="grammar-header"><span>{struct}</span></div><div class="flashcard-body" style="padding: 18px;">{img_col}<div class="fc-text-col" style="padding-top: 0;"><div class="grammar-text">{desc}</div><div style="margin-top:15px;">{audio_btn}</div></div></div></div>')
                
                nav_btns_top = ""
                if len(valid_gr) > 1:
                    nav_style = "display: inline-flex; align-items: center; background: #f8f9fa; padding: 4px 10px; border-radius: 6px; border: 1px solid #dadce0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"
                    nav_btns_top = f'<div style="{nav_style}"><button type="button" class="nav-control-btn" onclick="moveGrSlide_{sys_id}(-1)">&#10094; Trước</button><span class="fc-counter" id="gr-counter-top-{sys_id}">1 / {len(valid_gr)}</span><button type="button" class="nav-control-btn" onclick="moveGrSlide_{sys_id}(1)">Sau &#10095;</button></div>'
                
                header_html = f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;"><h3 class="section-title" style="margin-bottom: 0;">📖 {title}</h3>{nav_btns_top}</div>'
                lec_html_parts.append(f'<div class="lecture-section">{header_html}<div class="slider-container-main">{"".join(gr_content_parts)}</div></div>')
        
            elif b_type == "🎧 Audio Độc Lập":
                a_url = self.optimize_url(blk.get('link', ''))
                if a_url: lec_html_parts.append(f'<div class="lecture-section"><h3 class="section-title">🎧 {title}</h3><div class="standalone-audio"><audio controls><source src="{a_url}" type="audio/mpeg">Trình duyệt không hỗ trợ audio.</audio></div></div>')

        lec_html = "".join(lec_html_parts)

        # --- BUILD BÀI TẬP (QUIZ) ---
        quiz_html_parts = []
        js_grading_parts = []
        js_init_parts = []
        max_score = 0
        
        valid_quizzes = []
        for q in self.quiz_data:
            has_topic = bool(q.get('topic'))
            has_text = bool(q.get('q_raw'))
            has_match = any([r["l"] or r["r"] for r in q.get('matches', [])])
            has_fill = any([ans for ans in q.get('fills', [])])
            has_mcq = any([txt for k, txt in q.get('mcq', {}).items() if k in ['a','b','c','d'] and txt])
            if has_topic or has_text or has_match or has_fill or has_mcq:
                valid_quizzes.append(q)

        for i, q in enumerate(valid_quizzes):
            idx = i + 1
            q_topic = q['topic']
            q_type = q['q_type']
            explanation = q['exp_html']
            
            q_text_html = q['q_html']
            urls_in_html = re.findall(r'(https?://[^\s<"]+)', q_text_html)
            img_urls = []
            q_audio_url = ""
            
            for raw_url in urls_in_html:
                url = self.optimize_url(raw_url)
                url_lower = url.lower()
                if ".mp3" in url_lower or "audio" in url_lower:
                    if not q_audio_url: q_audio_url = url
                elif "drive.google.com" in url_lower or "id=" in url_lower:
                    img_urls.append(url)
                else: img_urls.append(url)
                q_text_html = q_text_html.replace(raw_url, '')
                
            q_text_html = re.sub(r'^(?:<br>|\s)+', '', q_text_html)
            q_text_html = re.sub(r'(?:<br>|\s)+$', '', q_text_html).strip()
            
            topic_html = f'<div class="quiz-topic-badge">📌 {q_topic}</div>' if q_topic else ""
            q_audio_html = f'''<div class="q-audio-container" style="margin-bottom:15px;"><audio controls style="width: 100%; height: 40px; outline: none; border-radius: 8px;"><source src="{q_audio_url}" type="audio/mpeg"></audio></div>''' if q_audio_url else ""
            
            img_html = ""
            if img_urls:
                slides = []
                for j, url in enumerate(img_urls):
                    g_id = extract_gdrive_id(url)
                    display = 'block' if j == 0 else 'none'
                    active_cls = ' active' if j == 0 else ''
                    if g_id:
                        slides.append(f'<img class="quiz-img img-inner-slide-q{idx}-{sys_id}{active_cls}" src="https://drive.google.com/thumbnail?id={g_id}&sz=w1000" loading="lazy" style="display: {display};">')
                    else:
                        slides.append(f'<img class="quiz-img img-inner-slide-q{idx}-{sys_id}{active_cls}" src="{url}" loading="lazy" style="display: {display};">')
                
                nav_btns = f'<button type="button" class="nav-img-btn prev-btn" onclick="moveImgSlide_{sys_id}(\'q{idx}\', -1)">&#10094;</button><button type="button" class="nav-img-btn next-btn" onclick="moveImgSlide_{sys_id}(\'q{idx}\', 1)">&#10095;</button><div class="slide-counter" id="img-counter-q{idx}-{sys_id}">1 / {len(img_urls)}</div>' if len(img_urls) > 1 else ""
                img_html = f'<div class="carousel-container" data-qid="q{idx}" tabindex="0" style="margin-bottom:15px;"><div class="slides-wrapper">{"".join(slides)}</div>{nav_btns}</div>'

            input_html = ""
            
            if q_type == "Trắc nghiệm":
                max_score += 1
                mcq_data = q['mcq']
                correct_opt = mcq_data['correct']
                opts = [("A", mcq_data['a']), ("B", mcq_data['b']), ("C", mcq_data['c']), ("D", mcq_data['d'])]
                labels = []
                for val, txt in opts:
                    if not txt: continue
                    display_txt, audio_btn = self.parse_audio(txt, sys_id)
                    if not display_txt and audio_btn: display_txt = f"Đáp án {val}"
                    labels.append(f'<div style="display: flex; align-items: center; margin-bottom: 8px;"><label class="opt-label" id="label-q{idx}-{val}_{sys_id}" style="flex-grow: 1; margin: 0; display:flex; align-items:center;"><input type="radio" name="q{idx}_{sys_id}" value="{val}" style="margin-right:8px;"> <span style="font-weight:bold; margin-right:5px;">{val}.</span> {display_txt}</label>{audio_btn}</div>')
                input_html = f'<div class="card-options">{"".join(labels)}</div>'
                js_grading_parts.append(f"var q{idx} = container.querySelector('input[name=\"q{idx}_{sys_id}\"]:checked'); var q{idx}Correct = '{correct_opt}'; container.querySelectorAll('#card-q{idx}_{sys_id} .opt-label').forEach(function(lbl) {{ lbl.classList.remove('correct', 'incorrect'); }}); if (q{idx}) {{ if (q{idx}.value === q{idx}Correct) {{ score++; container.querySelector('#label-q{idx}-' + q{idx}.value + '_{sys_id}').classList.add('correct'); }} else {{ container.querySelector('#label-q{idx}-' + q{idx}.value + '_{sys_id}').classList.add('incorrect'); container.querySelector('#label-q{idx}-' + q{idx}Correct + '_{sys_id}').classList.add('correct'); }} }} else {{ container.querySelector('#label-q{idx}-' + q{idx}Correct + '_{sys_id}').classList.add('correct'); }} container.querySelector('#exp-q{idx}_{sys_id}').style.display = 'block';")

            elif q_type == "Điền từ (Ngắn)":
                max_score += 1
                valid_fills = [ans for ans in q['fills'] if ans]
                valid_ans_array = []
                input_tags = []
                for b_idx, ans_str in enumerate(valid_fills):
                    valid_ans_array.append([a.strip().lower() for a in ans_str.split(',')])
                    p_text = "Nhập câu trả lời..." if len(valid_fills) == 1 else f"Nhập câu trả lời {b_idx+1}..."
                    input_tags.append(f'<input type="text" class="essay-input short-input blank-input-q{idx}_{sys_id}" style="width:100%; box-sizing:border-box; margin-bottom:8px;" placeholder="{p_text}">')
                input_html = f'<div class="essay-container"><div class="input-wrapper" style="display:flex; flex-direction:column; align-items:stretch; gap:8px;">{"".join(input_tags)}<div class="status-icon" id="icon-q{idx}_{sys_id}" style="align-self:flex-start;"></div></div></div>'
                js_grading_parts.append(f"var q{idx}Valid = {str(valid_ans_array)}; var q{idx}Inputs = container.querySelectorAll('.blank-input-q{idx}_{sys_id}'); var q{idx}Icon = container.querySelector('#icon-q{idx}_{sys_id}'); var q{idx}AllCorrect = true; if (q{idx}Inputs.length > 0) {{ q{idx}Inputs.forEach(function(inp, b_idx) {{ var ans = inp.value.trim().toLowerCase(); inp.classList.remove('input-correct', 'input-incorrect'); if (q{idx}Valid[b_idx] && q{idx}Valid[b_idx].indexOf(ans) !== -1) {{ inp.classList.add('input-correct'); }} else {{ inp.classList.add('input-incorrect'); q{idx}AllCorrect = false; }} }}); if (q{idx}AllCorrect) {{ score++; q{idx}Icon.className = 'status-icon text-correct'; q{idx}Icon.innerHTML = '✅ Đúng'; }} else {{ q{idx}Icon.className = 'status-icon text-incorrect'; q{idx}Icon.innerHTML = '❌ Sai'; }} }} container.querySelector('#exp-q{idx}_{sys_id}').style.display = 'block';")

            elif q_type == "Nối câu":
                valid_matches = [m for m in q['matches'] if m['l'] or m['r']]
                if valid_matches:
                    max_score += len(valid_matches)
                    right_items = [{"text": m['r'], "orig_idx": i} for i, m in enumerate(valid_matches)]
                    random.shuffle(right_items)
                    
                    letters = list(string.ascii_uppercase)
                    for j, r_item in enumerate(right_items): r_item['id'] = letters[j] if j < len(letters) else str(j)
                    correct_mapping = {r_item['orig_idx']: r_item['id'] for r_item in right_items}
                    
                    left_html = ""; right_html = ""; input_tags = []
                    
                    for j, m in enumerate(valid_matches):
                        l_txt, l_img, l_audio = self.parse_media(m['l'], sys_id)
                        left_content = f'{l_img}<span style="margin-left:5px; flex-grow:1;">{l_txt}</span>{l_audio}'
                        left_html += f'<div class="match-item" style="display:flex; align-items:center;"><strong>{j+1}.</strong> {left_content}</div>'
                        
                    for r_item in right_items:
                        r_txt, r_img, r_audio = self.parse_media(r_item['text'], sys_id)
                        right_content = f'{r_img}<span style="margin-left:5px; flex-grow:1;">{r_txt}</span>{r_audio}'
                        right_html += f'<div class="match-item right-item" data-orig-idx="{r_item["orig_idx"]}" style="display:flex; align-items:center;"><strong class="right-label">{r_item["id"]}.</strong> {right_content}</div>'
                        
                    for j in range(len(valid_matches)):
                        options = '<option value="">---</option>'
                        for r_item in sorted(right_items, key=lambda x: str(x['id'])): options += f'<option value="{r_item["id"]}">{r_item["id"]}</option>'
                        input_tags.append(f'<div style="margin-right:15px; margin-bottom:10px; display:inline-block;"><strong>{j+1}.</strong> <select class="match-select match-input-q{idx}_{sys_id}" data-left-idx="{j}">{options}</select></div>')
                        
                    input_html = f'<div class="match-container" style="display:flex; flex-wrap:wrap; gap:15px; margin-bottom:15px;"><div class="match-col" style="flex:1; min-width:200px;">{left_html}</div><div class="match-col match-right-container-q{idx}_{sys_id}" style="flex:1; min-width:200px;">{right_html}</div></div><div class="match-answers" style="display:block; padding-top:10px; border-top:1px dashed #ccc;">{"".join(input_tags)}<div class="status-icon" id="icon-q{idx}_{sys_id}" style="margin-top: 5px;"></div></div>'
                    
                    correct_json = json.dumps([correct_mapping[j] for j in range(len(valid_matches))])
                    js_grading_parts.append(f"var q{idx}Valid = {correct_json}; var q{idx}Inputs = container.querySelectorAll('.match-input-q{idx}_{sys_id}'); var q{idx}Icon = container.querySelector('#icon-q{idx}_{sys_id}'); var q{idx}AllCorrect = true; if (q{idx}Inputs.length > 0) {{ q{idx}Inputs.forEach(function(inp, b_idx) {{ var ans = inp.value; inp.classList.remove('input-correct', 'input-incorrect'); if (ans === q{idx}Valid[b_idx]) {{ inp.classList.add('input-correct'); score++; }} else {{ inp.classList.add('input-incorrect'); q{idx}AllCorrect = false; }} }}); if (q{idx}AllCorrect) {{ q{idx}Icon.className = 'status-icon text-correct'; q{idx}Icon.innerHTML = '✅ Hoàn toàn chính xác'; }} else {{ q{idx}Icon.className = 'status-icon text-incorrect'; q{idx}Icon.innerHTML = '❌ Còn câu nối sai'; }} }} container.querySelector('#exp-q{idx}_{sys_id}').style.display = 'block';")

            display_style = 'display: block;' if i == 0 else 'display: none;'
            header_content = f'<div class="card-header">Câu {idx}:<br>{q_text_html}</div>' if q_text_html else (f'<div class="card-header">Câu {idx}</div>' if not topic_html else "")
            
            quiz_html_parts.append(f'<div class="quiz-card quiz-master-slide" id="card-q{idx}_{sys_id}" style="{display_style}"><div class="sticky-header">{topic_html}{header_content}</div><div class="quiz-body-scrollable">{img_html}{q_audio_html}{input_html}<div class="explanation-box" id="exp-q{idx}_{sys_id}">💡 <b>Kết quả / Giải thích:</b><br>{explanation}</div></div></div>')

        quiz_html = "".join(quiz_html_parts)
        js_grading = "\n".join(js_grading_parts)
        js_init = "".join(js_init_parts)

        # --- V266.0 ĐƯA THANH ĐIỀU HƯỚNG BÀI TẬP LÊN CÙNG DÒNG TAB ---
        quiz_nav_style = "display: inline-flex; align-items: center; background: #f8f9fa; padding: 4px 10px; border-radius: 6px; border: 1px solid #dadce0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"
        display_next = "inline-block" if len(valid_quizzes) > 1 else "none"
        display_submit = "inline-block" if len(valid_quizzes) == 1 else "none"
        quiz_nav_top = f'<div style="{quiz_nav_style}"><button type="button" class="nav-control-btn" onclick="moveQuizSlide_{sys_id}(-1)" id="quiz-prev-btn-top-{sys_id}" disabled>&#10094; Câu trước</button><span class="fc-counter" id="quiz-counter-top-{sys_id}">Câu 1 / {len(valid_quizzes)}</span><button type="button" class="nav-control-btn" onclick="moveQuizSlide_{sys_id}(1)" id="quiz-next-btn-top-{sys_id}" style="display: {display_next};">Câu tiếp &#10095;</button><button type="button" class="submit-all-btn" id="quiz-submit-btn-top-{sys_id}" onclick="submitQuiz_{sys_id}()" style="display: {display_submit}; margin-left: 5px;">NỘP BÀI</button></div>' if valid_quizzes else ""

        has_lecture = len(lec_html_parts) > 0
        has_quiz = len(valid_quizzes) > 0

        header_wrapper_html = ""
        if has_lecture and has_quiz:
            header_wrapper_html = f"""
    <div class="system-header-wrapper" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #dadce0; margin-bottom: 25px; flex-wrap: wrap; gap: 10px;">
        <div class="tab-buttons" style="border-bottom: none; margin-bottom: 0;">
            <button class="tab-btn active" onclick="openTab_{sys_id}(event, 'tab-lecture')">📚 Thư mục bài giảng</button>
            <button class="tab-btn" onclick="openTab_{sys_id}(event, 'tab-quiz')">📝 Bài tập</button>
        </div>
        <div id="quiz-global-nav-{sys_id}" style="display: none;">
            {quiz_nav_top}
        </div>
    </div>"""
        elif has_quiz and not has_lecture:
            header_wrapper_html = f"""
    <div class="system-header-wrapper" style="display: flex; justify-content: flex-end; align-items: center; border-bottom: 2px solid #dadce0; padding-bottom: 10px; margin-bottom: 25px;">
        <div id="quiz-global-nav-{sys_id}" style="display: block;">
            {quiz_nav_top}
        </div>
    </div>"""

        lecture_display = "block" if has_lecture else "none"
        quiz_display = "block" if (has_quiz and not has_lecture) else "none"
        
        lecture_block_html = f'<div id="tab-lecture_{sys_id}" class="tab-content" style="display: {lecture_display};">{lec_html}</div>' if has_lecture else ""
        quiz_block_html = f'<div id="tab-quiz_{sys_id}" class="tab-content" style="display: {quiz_display};"><div class="quiz-master-container"><div id="quiz-slider-container-{sys_id}" class="slider-content-wrapper">{quiz_html}</div></div><div class="score-board" id="final-score-board-{sys_id}" style="display: none; margin-top: 20px;">🏆 Điểm số tự động của bạn: <strong id="total-score-text-{sys_id}">0 / {max_score}</strong></div></div>' if has_quiz else ""

        cover_html_block = ""
        cover_link = self.entry_global_cover.get().strip()
        final_cover_src = cover_link if cover_link else self.global_cover_base64
        if final_cover_src:
            if "drive.google.com" in final_cover_src.lower() or "id=" in final_cover_src.lower():
                g_id = extract_gdrive_id(final_cover_src)
                cover_opt = f"https://drive.google.com/thumbnail?id={g_id}&sz=w1000" if g_id else final_cover_src
            else:
                cover_opt = self.optimize_url(final_cover_src) if final_cover_src.startswith("http") else final_cover_src
            cover_html_block = f'<div style="display:none!important; opacity:0; width:0; height:0; overflow:hidden;"><img src="{cover_opt}" loading="lazy" alt="Cover Image"></div>\n'

        final_code = f"""
<div class="system-container" id="bj-system-{sys_id}">
    {cover_html_block}
    <h2 class="system-title">E With Bich Jane<span></span></h2>
{header_wrapper_html}
{lecture_block_html}
{quiz_block_html}
</div>

<style>
    .system-container, .tab-content, .lecture-section, .slider-container-main, .quiz-master-container {{ overflow: visible !important; }}
    .system-container {{ font-family: -apple-system, sans-serif; max-width: 720px; margin: 0 auto; padding: 20px 10px; }}
    .system-title {{ text-align: center; color: #1a73e8; margin-bottom: 25px; font-size: 26px; font-weight: bold; }}
    .tab-buttons {{ display: flex; gap: 10px; border-bottom: 2px solid #dadce0; margin-bottom: 25px; }}
    .tab-btn {{ background: none; border: none; padding: 12px 20px; font-size: 16px; font-weight: 600; color: #5f6368; cursor: pointer; transition: 0.3s; border-bottom: 3px solid transparent; margin-bottom: -2px; }}
    .tab-btn:hover {{ color: #1a73e8; background: #f8f9fa; border-radius: 8px 8px 0 0; }}
    .tab-btn.active {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; }}
    .tab-content {{ display: none; animation: fadeIn 0.4s; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .lecture-section {{ margin-bottom: 30px; }}
    .section-title {{ font-size: 18px; color: #202124; border-left: 4px solid #34a853; padding-left: 10px; }}
    
    .slider-container-main, .quiz-master-container {{ display: flex; flex-direction: column; position: relative; }}
    
    .nav-control-btn {{ padding: 6px 12px; border: none; background: #1a73e8; color: white; border-radius: 6px; cursor: pointer; font-weight: bold; transition: 0.2s; font-size: 13px; margin: 0 2px; }}
    .nav-control-btn:hover:not(:disabled) {{ background: #1557b0; transform: translateY(-1px); }}
    .nav-control-btn:disabled {{ background: #dadce0; color: #80868b; cursor: not-allowed; }}
    .fc-counter {{ font-weight: bold; color: #3c4043; font-size: 14px; text-align: center; margin: 0 5px; }}
    
    .flashcard-body {{ display: flex; flex-direction: row; gap: 20px; width: 100%; align-items: flex-start; }}
    .fc-img-col {{ flex: 1; text-align: center; max-width: 50%; }}
    .fc-img {{ max-width: 100%; max-height: 350px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); object-fit: contain; }}
    .fc-text-col {{ flex: 1; display: flex; flex-direction: column; justify-content: flex-start; align-items: flex-start; padding-top: 10px; }}
    .fc-word {{ font-size: 28px; color: #1a73e8; margin: 0 0 10px 0; }}
    .fc-meaning {{ font-size: 18px; color: #5f6368; font-style: italic; margin: 0 0 15px 0; }}
    @media (max-width: 600px) {{ .flashcard-body {{ flex-direction: column; align-items: center; text-align: center; }} .fc-img-col {{ max-width: 100%; }} .fc-text-col {{ align-items: center; text-align: center; }} }}

    .flashcard {{ display: flex; flex-direction: column; align-items: stretch; background: #fff; border: 1px solid #dadce0; border-radius: 10px; padding: 15px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); animation: fadeIn 0.3s ease; }}
    .grammar-box {{ background: #fef7e0; border: 1px solid #fbbc04; border-radius: 10px; overflow: hidden; animation: fadeIn 0.3s ease; }}
    .grammar-header {{ background: #fbbc04; color: #fff; padding: 12px 18px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; align-items: center; }}
    .grammar-text {{ color: #3c4043; font-size: 16px; line-height: 1.8; }}
    .audio-icon-btn {{ background: #e8f0fe; border: none; border-radius: 50%; width: 45px; height: 45px; font-size: 22px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; flex-shrink: 0; }}
    .audio-icon-btn:hover {{ background: #d2e3fc; transform: scale(1.1); box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
    .video-container {{ position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 10px; border: 1px solid #dadce0; }}
    .video-container iframe {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }}
    .standalone-audio {{ background: #f1f3f4; padding: 15px; border-radius: 10px; display: flex; flex-direction: column; gap: 10px; }}
    .standalone-audio audio {{ width: 100%; height: 40px; outline: none; }}
    .standalone-audio p {{ margin: 0; font-weight: 600; color: #3c4043; }}
    
    .quiz-card {{ background: #ffffff; border: 1px solid #dadce0; border-radius: 12px; padding: 24px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); box-sizing: border-box; animation: fadeIn 0.3s ease; width: 100%; }}
    .quiz-topic-badge {{ display: inline-block; background: #e8f0fe; color: #1a73e8; padding: 6px 14px; border-radius: 20px; font-size: 13.5px; font-weight: bold; margin-bottom: 12px; border: 1px solid #d2e3fc; }}
    
    .sticky-header {{ position: -webkit-sticky; position: sticky; top: 0px; background: #ffffff; z-index: 90; padding: 15px 0 10px 0; margin-top: -15px; border-bottom: 2px dashed #e4e3e1; margin-bottom: 15px; }}
    .card-header {{ font-size: 16.5px; font-weight: 600; color: #202124; line-height: 1.5; }}
    
    .carousel-container {{ position: relative; width: 100%; background: transparent; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; outline: none; margin-bottom: 18px; }}
    .quiz-img {{ max-height: 350px; width: 100%; height: auto; object-fit: contain; }} 
    .nav-img-btn {{ position: absolute; top: 50%; transform: translateY(-50%); background: rgba(0, 0, 0, 0.4); color: white; border: none; padding: 12px 15px; cursor: pointer; font-size: 16px; border-radius: 50%; z-index: 2; }}
    .nav-img-btn:hover {{ background: rgba(0, 0, 0, 0.8); }}
    .prev-btn {{ left: 10px; }} .next-btn {{ right: 10px; }}
    .slide-counter {{ position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); background: rgba(0, 0, 0, 0.6); color: white; padding: 4px 12px; border-radius: 20px; font-size: 11.5px; font-weight: bold; z-index: 2; }}
    
    .card-options {{ display: flex; flex-direction: column; gap: 10px; }}
    .opt-label {{ display: block; padding: 14px; border: 1px solid #dadce0; border-radius: 8px; cursor: pointer; font-size: 15px; transition: 0.15s; box-sizing: border-box; }}
    .opt-label:hover {{ background: #f8f9fa; }}
    .opt-label.correct {{ background: #e6f4ea; border-color: #137333; color: #137333; font-weight: bold; }}
    .opt-label.incorrect {{ background: #fce8e6; border-color: #c5221f; color: #c5221f; }}
    
    .essay-container {{ display: flex; flex-direction: column; gap: 12px; width: 100%; }}
    .essay-input {{ padding: 12px; border: 1px solid #dadce0; border-radius: 8px; font-size: 15px; font-family: inherit; transition: 0.2s; }}
    .essay-input:focus {{ border-color: #1a73e8; outline: none; box-shadow: 0 0 0 2px rgba(26,115,232,0.2); }}
    .essay-input.input-correct {{ border-color: #137333; background: #e6f4ea; color: #137333; font-weight: bold; box-shadow: none; }}
    .essay-input.input-incorrect {{ border-color: #c5221f; background: #fce8e6; color: #c5221f; box-shadow: none; }}
    
    .match-item {{ padding: 10px; border: 1px solid #dadce0; border-radius: 6px; margin-bottom: 8px; background: #f8f9fa; display: flex; align-items: center; font-size: 15px; box-sizing: border-box; }}
    .match-select {{ padding: 6px 12px; border-radius: 6px; border: 1px solid #dadce0; font-size: 14px; outline: none; cursor: pointer; }}
    .match-select.input-correct {{ border-color: #137333; background: #e6f4ea; color: #137333; font-weight: bold; }}
    .match-select.input-incorrect {{ border-color: #c5221f; background: #fce8e6; color: #c5221f; font-weight: bold; }}
    
    .status-icon {{ font-weight: bold; font-size: 15px; }}
    .status-icon.text-correct {{ color: #137333; }}
    .status-icon.text-incorrect {{ color: #c5221f; }}
    .submit-all-btn {{ padding: 6px 12px; font-size: 14px; font-weight: bold; background: #34a853; color: white; border: none; border-radius: 6px; cursor: pointer; transition: 0.3s; margin: 0 2px; }}
    .submit-all-btn:hover {{ background: #2d9248; box-shadow: 0 4px 10px rgba(52, 168, 83, 0.3); }}
    .explanation-box {{ display: none; margin-top: 18px; padding: 15px; background: #e8f0fe; color: #1967d2; border-radius: 8px; font-size: 14.5px; border-left: 5px solid #1a73e8; line-height: 1.5; }}
    .score-board {{ margin: 0 auto; padding: 15px 20px; background: #fff3e0; border: 1px solid #ffcc80; border-radius: 8px; color: #e65100; font-size: 18px; box-sizing: border-box; text-align: center; }}
</style>

<script>
(function() {{
    var sysId = '{sys_id}';
    var container = document.getElementById('bj-system-' + sysId);
    if (!container) return;

    {js_init}

    window['openTab_' + sysId] = function(evt, tabName) {{
        var tabcontent = container.querySelectorAll(".tab-content");
        for (var i = 0; i < tabcontent.length; i++) {{ tabcontent[i].style.display = "none"; }}
        var tablinks = container.querySelectorAll(".tab-btn");
        for (var i = 0; i < tablinks.length; i++) {{ tablinks[i].classList.remove("active"); }}
        container.querySelector("#" + tabName + "_" + sysId).style.display = "block";
        evt.currentTarget.classList.add("active");
        
        var globalNav = document.getElementById("quiz-global-nav-" + sysId);
        if (globalNav) {{
            globalNav.style.display = (tabName === "tab-quiz") ? "block" : "none";
        }}
    }};

    window['playGlobalAudio_' + sysId] = function(audioUrl) {{
        if (!audioUrl || audioUrl.trim() === "") {{ alert('Lỗi: Link Audio trống!'); return; }}
        if (window.currentSystemAudio) {{ window.currentSystemAudio.pause(); window.currentSystemAudio.currentTime = 0; }}
        window.currentSystemAudio = new Audio(audioUrl);
        var playPromise = window.currentSystemAudio.play();
        if (playPromise !== undefined) {{ playPromise.catch(function(error) {{ console.error("Lỗi:", error); alert("Không thể phát âm thanh!"); }}); }}
    }};

    window['moveFcSlide_' + sysId] = function(step) {{
        var slides = container.querySelectorAll('.fc-slide-' + sysId);
        if (slides.length === 0) return;
        var idx = Array.from(slides).findIndex(s => s.style.display !== 'none');
        if (idx === -1) idx = 0;
        slides[idx].style.display = "none";
        idx = (idx + step + slides.length) % slides.length;
        slides[idx].style.display = "flex";
        var topC = container.querySelector('#fc-counter-top-' + sysId);
        if(topC) topC.innerText = (idx + 1) + " / " + slides.length;
    }};

    window['moveGrSlide_' + sysId] = function(step) {{
        var slides = container.querySelectorAll('.gr-slide-' + sysId);
        if (slides.length === 0) return;
        var idx = Array.from(slides).findIndex(s => s.style.display !== 'none');
        if (idx === -1) idx = 0;
        slides[idx].style.display = "none";
        idx = (idx + step + slides.length) % slides.length;
        slides[idx].style.display = "block";
        var topC = container.querySelector('#gr-counter-top-' + sysId);
        if(topC) topC.innerText = (idx + 1) + " / " + slides.length;
    }};

    window['showQuizSlide_' + sysId] = function(index) {{
        var slides = container.querySelectorAll('.quiz-master-slide');
        if(slides.length === 0) return;
        slides.forEach(function(s) {{ s.style.display = 'none'; }});
        if (index >= slides.length) index = slides.length - 1;
        if (index < 0) index = 0;
        slides[index].style.display = 'block';
        
        var txt = "Câu " + (index + 1) + " / " + slides.length;
        var topC = container.querySelector('#quiz-counter-top-' + sysId);
        if(topC) topC.innerText = txt;
        
        var pTop = container.querySelector('#quiz-prev-btn-top-' + sysId);
        if(pTop) pTop.disabled = (index === 0);
        
        var nTop = container.querySelector('#quiz-next-btn-top-' + sysId);
        var sTop = container.querySelector('#quiz-submit-btn-top-' + sysId);
        if (index === slides.length - 1) {{
            if(nTop) nTop.style.display = 'none';
            if(sTop) sTop.style.display = 'inline-block';
        }} else {{
            if(nTop) nTop.style.display = 'inline-block';
            if(sTop) sTop.style.display = 'none';
        }}
        container.dataset.currentIndex = index;
    }};
    
    window['moveQuizSlide_' + sysId] = function(step) {{
        var idx = parseInt(container.dataset.currentIndex || 0);
        window['showQuizSlide_' + sysId](idx + step);
    }};

    window['moveImgSlide_' + sysId] = function(questionId, step) {{
        var slides = container.querySelectorAll('.img-inner-slide-' + questionId + '-' + sysId);
        if (slides.length === 0) return;
        var idx = Array.from(slides).findIndex(s => s.style.display !== 'none');
        if (idx === -1) idx = 0;
        slides[idx].style.display = "none";
        idx = (idx + step + slides.length) % slides.length;
        slides[idx].style.display = "block";
        var counterEl = container.querySelector('#img-counter-' + questionId + '-' + sysId);
        if (counterEl) counterEl.innerText = (idx + 1) + " / " + slides.length;
    }};

    window['submitQuiz_' + sysId] = function() {{
        var score = 0;
        {js_grading}
        container.querySelectorAll('.quiz-master-slide').forEach(function(c) {{ c.style.display = 'block'; }});
        var navTop = container.querySelector('#quiz-global-nav-' + sysId);
        if (navTop) navTop.style.display = 'none';
        container.querySelector('#total-score-text-' + sysId).innerText = score + " / {max_score}";
        var scoreBoard = container.querySelector('#final-score-board-' + sysId);
        if (scoreBoard) {{
            scoreBoard.style.display = 'block';
            scoreBoard.scrollIntoView({{ behavior: 'smooth', block: 'end' }});
        }}
    }};

    container.addEventListener('keydown', function(event) {{
        var activeElement = document.activeElement;
        if (activeElement && activeElement.classList.contains('carousel-container')) {{
            var qId = activeElement.getAttribute('data-qid');
            if (event.key === 'ArrowLeft') {{ window['moveImgSlide_' + sysId](qId, -1); event.preventDefault(); }}
            else if (event.key === 'ArrowRight') {{ window['moveImgSlide_' + sysId](qId, 1); event.preventDefault(); }}
        }}
    }});
}})();
</script>
"""
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, final_code)
        messagebox.showinfo("Hoàn tất", "Đã xuất xong HTML Giao diện Bài học.")

if __name__ == "__main__":
    app = BJ2SystemApp()
    app.mainloop()
