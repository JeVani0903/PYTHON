import streamlit as st
import base64
import re
import uuid
import html

# ================= QUẢN LÝ TRẠNG THÁI (SESSION STATE) =================
# Khởi tạo các biến để quản lý việc reset nội dung
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())
if 'title_input' not in st.session_state:
    st.session_state.title_input = ""
if 'content_input' not in st.session_state:
    st.session_state.content_input = ""
if 'link_input' not in st.session_state:
    st.session_state.link_input = ""
if 'html_output' not in st.session_state:
    st.session_state.html_output = ""

# Hàm callback thực hiện việc xóa sạch dữ liệu
def reset_all_data():
    st.session_state.title_input = ""
    st.session_state.content_input = ""
    st.session_state.link_input = ""
    st.session_state.html_output = ""
    # Đổi key của uploader để ép Streamlit tạo mới widget (xóa ảnh cũ)
    st.session_state.uploader_key = str(uuid.uuid4())

# ================= GIAO DIỆN CHÍNH =================
st.set_page_config(
    page_title="Phần mềm tạo bài viết Blogspot (v3.0)", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📝 Phần mềm tạo bài viết Blogspot (v3.0) - Auto Reset")
st.write("---")

col1, col2 = st.columns([1, 2])

# ---------------- CỘT TRÁI: HÌNH ẢNH ----------------
with col1:
    st.subheader("📸 Cột 1: Hình ảnh đại diện")
    uploaded_file = st.file_uploader(
        "Kéo thả hoặc chọn hình ảnh vào đây", 
        type=['png', 'jpg', 'jpeg', 'gif', 'webp'],
        key=st.session_state.uploader_key # Ràng buộc key để reset
    )
    
    img_tag = "<p><i>(Chưa có hình ảnh)</i></p>"
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Ảnh đã chọn", use_container_width=True)
        
        bytes_data = uploaded_file.read()
        b64_string = base64.b64encode(bytes_data).decode('utf-8')
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            ext = 'png'
        
        img_tag = f'<img src="data:image/{ext};base64,{b64_string}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" alt="thumbnail" />'

# ---------------- CỘT PHẢI: NỘI DUNG ----------------
with col2:
    st.subheader("✍️ Cột 2: Thông tin bài viết")
    
    # Ràng buộc các trường nhập liệu với Session State
    title = st.text_input("Nhập tiêu đề bài viết...", key="title_input", placeholder="Ví dụ: Sản phẩm gia dụng thông minh mới")
    
    content_html = st.text_area(
        "Soạn thảo hoặc dán nội dung ở đây...",
        key="content_input",
        placeholder="Mẹo: Bản web nhận diện tốt nhất khi bạn dán trực tiếp đoạn mã HTML hoặc text thô vào đây.",
        height=250
    )
    
    link = st.text_input("🔗 Nhập đường dẫn link...", key="link_input", placeholder="https://example.com")
    
    st.write("")
    
    # Nút tạo mã HTML
    if st.button("🚀 TẠO MÃ HTML CHO BLOGSPOT", type="primary", use_container_width=True):
        if not title:
            st.warning("Vui lòng nhập tiêu đề bài viết!")
        else:
            body_match = re.search(r'<body[^>]*>(.*?)</body>', content_html, re.IGNORECASE | re.DOTALL)
            processed_html = body_match.group(1) if body_match else content_html

            processed_html = re.sub(r'background(?:-color)?\s*:\s*[^;"\'>]+;?', '', processed_html, flags=re.IGNORECASE)
            processed_html = re.sub(r'color\s*:\s*[^;"\'>]+;?', '', processed_html, flags=re.IGNORECASE)
            processed_html = re.sub(r'<span style="\s*">\s*(.*?)\s*</span>', r'\1', processed_html, flags=re.IGNORECASE)

            final_html = f"""<div style="display: flex; flex-wrap: wrap; gap: 20px; font-family: Arial, sans-serif; line-height: 1.6;">
    <div style="flex: 1; min-width: 250px;">
        {img_tag}
    </div>
    
    <div style="flex: 2; min-width: 300px;">
        <h2 style="color: #333; margin-top: 0;">{title}</h2>
        
        <div style="color: #222; margin-bottom: 20px;">
            {processed_html}
        </div>
        
        <div style="margin-top: 15px;">
            <a href="{link}" target="_blank" style="text-decoration: none; display: inline-flex; align-items: center; background-color: #007bff; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; transition: 0.3s;">
                <img src="https://cdn-icons-png.flaticon.com/512/2874/2874808.png" style="width: 20px; height: 20px; margin-right: 8px;" alt="link icon"/>
                Nhấn vào đây để xem chi tiết
            </a>
        </div>
    </div>
</div>"""
            # Lưu kết quả vào state thay vì in ra ngay lập tức
            st.session_state.html_output = final_html.strip()
            st.rerun()

# ================= KHU VỰC HIỂN THỊ & XỬ LÝ AUTO-RESET =================
if st.session_state.html_output:
    st.write("---")
    st.success("🎉 Thành công! Nhấn nút màu đỏ bên dưới để Copy mã và Tự động Reset nội dung:")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    
    # [1] Nút thực thi JS (Copy + Ra lệnh Click Reset)
    with col_btn1:
        escaped_html = html.escape(st.session_state.html_output)
        custom_btn_html = f"""
        <textarea id="hiddenHtml" style="display:none;">{escaped_html}</textarea>
        <button onclick="copyAndReset()" style="
            background-color: #ff4b4b; 
            color: white; 
            border: none; 
            padding: 0.5rem 1rem; 
            border-radius: 0.25rem; 
            cursor: pointer; 
            font-weight: 600; 
            width: 100%;
            height: 42px;
            font-size: 16px;
            font-family: 'Source Sans Pro', sans-serif;">
            📋 COPY MÃ HTML & TỰ ĐỘNG RESET
        </button>
        <script>
            function copyAndReset() {{
                var text = document.getElementById("hiddenHtml").value;
                navigator.clipboard.writeText(text).then(function() {{
                    document.querySelector("button").innerText = "✔ Đã Copy! Đang dọn dẹp...";
                    
                    // Tìm nút Reset của Streamlit (bên ngoài iframe) và mô phỏng click
                    var buttons = window.parent.document.querySelectorAll('button');
                    buttons.forEach(function(btn) {{
                        if (btn.innerText.includes('Xóa dữ liệu (Reset)')) {{
                            btn.click();
                        }}
                    }});
                }}).catch(function(err) {{
                    alert("Không thể copy: " + err);
                }});
            }}
        </script>
        """
        st.components.v1.html(custom_btn_html, height=50)

    # [2] Nút Reset Python bản địa (Đích đến của JS click, đóng vai trò fallback)
    with col_btn2:
        st.button("🔄 Xóa dữ liệu (Reset)", on_click=reset_all_data, use_container_width=True)

    # Hiển thị text thô cho trường hợp muốn copy tay một phần (Nằm trong mục mở rộng để gọn UI)
    with st.expander("Nhấn vào đây nếu muốn xem chi tiết mã HTML thô"):
        st.code(st.session_state.html_output, language="html")
        
    st.write("---")
    st.subheader("👀 Giao diện hiển thị thực tế trên Blogspot:")
    st.components.v1.html(st.session_state.html_output, height=450, scrolling=True)