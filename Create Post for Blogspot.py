import streamlit as st
import base64
import re

# Cấu hình trang hiển thị rộng rãi giống ứng dụng cũ
st.set_page_config(
    page_title="Phần mềm tạo bài viết Blogspot (v3.0)", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📝 Phần mềm tạo bài viết Blogspot (v3.0) - Bản Web")
st.write("---")

# Chia giao diện thành 2 cột tương tự bản PyQt5
col1, col2 = st.columns([1, 2])

# ================= CỘT TRÁI: HÌNH ẢNH =================
with col1:
    st.subheader("📸 Cột 1: Hình ảnh đại diện")
    uploaded_file = st.file_uploader(
        "Kéo thả hoặc chọn hình ảnh vào đây", 
        type=['png', 'jpg', 'jpeg', 'gif', 'webp']
    )
    
    img_tag = "<p><i>(Chưa có hình ảnh)</i></p>"
    if uploaded_file is not None:
        # Hiển thị ảnh xem trước trên giao diện web
        st.image(uploaded_file, caption="Ảnh đã chọn", use_container_width=True)
        
        # Xử lý mã hóa Base64 cho ảnh
        bytes_data = uploaded_file.read()
        b64_string = base64.b64encode(bytes_data).decode('utf-8')
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            ext = 'png'
        
        img_tag = f'<img src="data:image/{ext};base64,{b64_string}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" alt="thumbnail" />'

# ================= CỘT PHẢI: NỘI DUNG =================
with col2:
    st.subheader("✍️ Cột 2: Thông tin bài viết")
    
    # 1. Ô chứa tiêu đề
    title = st.text_input("Nhập tiêu đề bài viết...", placeholder="Ví dụ: Sản phẩm gia dụng thông minh mới")
    
    # 2. Ô chứa nội dung
    content_html = st.text_area(
        "Soạn thảo hoặc dán nội dung ở đây...",
        placeholder="Mẹo: Bản web nhận diện tốt nhất khi bạn dán trực tiếp đoạn mã HTML hoặc text thô vào đây.",
        height=250
    )
    
    # 3. Ô chứa link
    link = st.text_input("🔗 Nhập đường dẫn link...", placeholder="https://example.com")
    
    st.write("")
    # Nút tạo mã HTML
    if st.button("🚀 TẠO MÃ HTML CHO BLOGSPOT", type="primary", use_container_width=True):
        if not title:
            st.warning("Vui lòng nhập tiêu đề bài viết!")
        else:
            # Bộ lọc khử nền đen và chữ tàng hình (giữ nguyên logic xử lý chuỗi từ v2/v3 của bạn)
            body_match = re.search(r'<body[^>]*>(.*?)</body>', content_html, re.IGNORECASE | re.DOTALL)
            processed_html = body_match.group(1) if body_match else content_html

            processed_html = re.sub(r'background(?:-color)?\s*:\s*[^;"\'>]+;?', '', processed_html, flags=re.IGNORECASE)
            processed_html = re.sub(r'color\s*:\s*[^;"\'>]+;?', '', processed_html, flags=re.IGNORECASE)
            processed_html = re.sub(r'<span style="\s*">\s*(.*?)\s*</span>', r'\1', processed_html, flags=re.IGNORECASE)

            # Cấu trúc HTML cuối cùng để dán vào Blogspot
            final_html = f"""
<div style="display: flex; flex-wrap: wrap; gap: 20px; font-family: Arial, sans-serif; line-height: 1.6;">
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
</div>
"""
            st.success("🎉 Thành công! Hãy di chuột vào ô dưới và nhấn nút biểu tượng Copy ở góc trên bên phải:")
            
            # Ô hiển thị code kèm nút copy tự động của Streamlit
            st.code(final_html.strip(), language="html")
            
            # Hiển thị trực tiếp giao diện trực quan cho người dùng xem trước
            st.write("---")
            st.subheader("👀 Giao diện hiển thị thực tế trên Blogspot:")
            st.components.v1.html(final_html, height=450, scrolling=True)