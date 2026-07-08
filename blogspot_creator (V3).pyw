import sys
import base64
import re
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QLineEdit, QTextEdit, QPushButton, QDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont

class ImageDropLabel(QLabel):
    """Lớp xử lý khu vực kéo thả hình ảnh ở cột bên trái"""
    def __init__(self):
        super().__init__()
        self.setText("\n\nKéo thả hình ảnh vào đây\n\n")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #888;
                border-radius: 10px;
                background-color: #f8f9fa;
                font-size: 16px;
                color: #555;
            }
        """)
        self.setAcceptDrops(True)
        self.image_path = ""

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.image_path = urls[0].toLocalFile()
            self.display_image()

    def display_image(self):
        pixmap = QPixmap(self.image_path)
        self.setPixmap(pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

class BlogspotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Phần mềm tạo bài viết Blogspot (v3.0)")
        self.resize(1000, 600)

        main_layout = QHBoxLayout()

        # ================= CỘT TRÁI: HÌNH ẢNH =================
        left_layout = QVBoxLayout()
        left_label = QLabel("<b>Cột 1: Hình ảnh đại diện</b>")
        self.image_drop = ImageDropLabel()
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.image_drop)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget, 1)

        # ================= CỘT PHẢI: NỘI DUNG =================
        right_layout = QVBoxLayout()
        right_label = QLabel("<b>Cột 2: Thông tin bài viết</b>")
        right_layout.addWidget(right_label)

        # 1. Ô chứa tiêu đề
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Nhập tiêu đề bài viết...")
        self.title_input.setStyleSheet("font-size: 16px; padding: 5px;")
        right_layout.addWidget(self.title_input)

        # Toolbar cho soạn thảo
        toolbar_layout = QHBoxLayout()
        btn_bold = QPushButton("B")
        btn_bold.setStyleSheet("font-weight: bold;")
        btn_bold.clicked.connect(lambda: self.content_input.setFontWeight(QFont.Bold if self.content_input.fontWeight() != QFont.Bold else QFont.Normal))
        
        btn_italic = QPushButton("I")
        btn_italic.setStyleSheet("font-style: italic;")
        btn_italic.clicked.connect(lambda: self.content_input.setFontItalic(not self.content_input.fontItalic()))
        
        btn_underline = QPushButton("U")
        btn_underline.setStyleSheet("text-decoration: underline;")
        btn_underline.clicked.connect(lambda: self.content_input.setFontUnderline(not self.content_input.fontUnderline()))
        
        toolbar_layout.addWidget(btn_bold)
        toolbar_layout.addWidget(btn_italic)
        toolbar_layout.addWidget(btn_underline)
        toolbar_layout.addStretch()
        right_layout.addLayout(toolbar_layout)

        # 2. Ô chứa nội dung
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Soạn thảo nội dung ở đây... (Khi copy nội dung từ nguồn khác dán vào, nền đen sẽ tự động được xóa)")
        right_layout.addWidget(self.content_input)

        # 3. Ô chứa link
        link_layout = QHBoxLayout()
        link_icon_label = QLabel("🔗")
        link_icon_label.setStyleSheet("font-size: 20px;")
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Nhập đường dẫn link...")
        self.link_input.setStyleSheet("padding: 5px;")
        link_layout.addWidget(link_icon_label)
        link_layout.addWidget(self.link_input)
        right_layout.addLayout(link_layout)

        # Nút tạo HTML
        btn_generate = QPushButton("TẠO MÃ HTML CHO BLOGSPOT")
        btn_generate.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; margin-top: 10px;")
        btn_generate.clicked.connect(self.generate_html)
        right_layout.addWidget(btn_generate)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, 2)

        self.setLayout(main_layout)

    def generate_html(self):
        title = self.title_input.text()
        link = self.link_input.text()
        
        raw_html = self.content_input.toHtml()
        body_match = re.search(r'<body[^>]*>(.*?)</body>', raw_html, re.IGNORECASE | re.DOTALL)
        content_html = body_match.group(1) if body_match else raw_html

        # Bộ lọc khử nền đen và chữ tàng hình từ bản v2
        content_html = re.sub(r'background(?:-color)?\s*:\s*[^;"\'>]+;?', '', content_html, flags=re.IGNORECASE)
        content_html = re.sub(r'color\s*:\s*[^;"\'>]+;?', '', content_html, flags=re.IGNORECASE)
        content_html = re.sub(r'<span style="\s*">\s*(.*?)\s*</span>', r'\1', content_html, flags=re.IGNORECASE)

        img_tag = "<p><i>(Chưa có hình ảnh)</i></p>"
        if self.image_drop.image_path:
            try:
                with open(self.image_drop.image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = self.image_drop.image_path.split('.')[-1].lower()
                    if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                        ext = 'png'
                    img_tag = f'<img src="data:image/{ext};base64,{b64_string}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" alt="{title}" />'
            except Exception as e:
                img_tag = f"<p>Lỗi đọc hình ảnh: {e}</p>"

        final_html = f"""
<div style="display: flex; flex-wrap: wrap; gap: 20px; font-family: Arial, sans-serif; line-height: 1.6;">
    <!-- CỘT TRÁI: HÌNH ẢNH -->
    <div style="flex: 1; min-width: 250px;">
        {img_tag}
    </div>
    
    <!-- CỘT PHẢI: NỘI DUNG -->
    <div style="flex: 2; min-width: 300px;">
        <h2 style="color: #333; margin-top: 0;">{title}</h2>
        
        <div style="color: #222; margin-bottom: 20px;">
            {content_html}
        </div>
        
        <!-- ICON LINK -->
        <div style="margin-top: 15px;">
            <a href="{link}" target="_blank" style="text-decoration: none; display: inline-flex; align-items: center; background-color: #007bff; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; transition: 0.3s;">
                <img src="https://cdn-icons-png.flaticon.com/512/2874/2874808.png" style="width: 20px; height: 20px; margin-right: 8px;" alt="link icon"/>
                Nhấn vào đây để xem chi tiết
            </a>
        </div>
    </div>
</div>
"""
        self.show_output(final_html)

    def show_output(self, html_code):
        # Hộp thoại hiển thị
        dlg = QDialog(self)
        dlg.setWindowTitle("Mã HTML v3.0 - Copy và dán vào 'Chế độ xem HTML'")
        dlg.resize(700, 500)
        
        layout = QVBoxLayout()
        instruction = QLabel("<b>Thành công!</b> Hãy nhấn nút bên dưới để copy mã và tự động đóng hộp thoại này.")
        layout.addWidget(instruction)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(html_code.strip())
        layout.addWidget(text_edit)

        # ==================== BẢN V3: NÚT COPY & ĐÓNG ====================
        btn_copy = QPushButton("📋 COPY MÃ VÀ ĐÓNG")
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #008CBA; 
                color: white; 
                font-weight: bold; 
                padding: 12px; 
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #007399;
            }
        """)
        
        def copy_and_close():
            # 1. Gọi system clipboard để copy văn bản
            clipboard = QApplication.clipboard()
            clipboard.setText(html_code.strip())
            # 2. Đóng hộp thoại
            dlg.accept()

        btn_copy.clicked.connect(copy_and_close)
        layout.addWidget(btn_copy)
        # =================================================================

        dlg.setLayout(layout)
        dlg.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = BlogspotApp()
    ex.show()
    sys.exit(app.exec_())
