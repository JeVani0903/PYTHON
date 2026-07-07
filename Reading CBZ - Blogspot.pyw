import streamlit as st
import base64
import re
import os

# =========================================================================
# ⚙️ CẤU HÌNH TRANG VÀ BIẾN CỐ ĐỊNH
# =========================================================================
st.set_page_config(
    page_title="Bộ Công Cụ Tạo Mã Nhúng Blogspot & CBZ Reader", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Key Google Drive đã cố định từ file Reading CBZ.pyw
FIXED_GOOGLE_API_KEY = "AIzaSyD8zQpA869UKNitk1jZteUBLLsL_hFLXfE"

# =========================================================================
# 🧭 DROPDOWN LỰA CHỌN CÔNG CỤ
# =========================================================================
st.sidebar.title("🧰 BỘ CÔNG CỤ WEB")
st.sidebar.write("---")

tool_choice = st.sidebar.selectbox(
    "📌 Chọn công cụ bạn muốn sử dụng:",
    [
        "📝 1. Phần mềm tạo bài viết Blogspot (v3.0)", 
        "⚡ 2. Trình Đọc Truyện CBZ API Google Drive (v2.0)"
    ]
)

# Hiển thị tiêu đề chung trên cùng
st.title("🧰 BỘ CÔNG CỤ TẠO MÃ HTML/CBZ ONLINE")
st.write("---")

# =========================================================================
# OPTION 1: PHẦN MỀM TẠO BÀI VIẾT BLOGSPOT (V3.0)
# =========================================================================
if tool_choice == "📝 1. Phần mềm tạo bài viết Blogspot (v3.0)":
    st.header("📝 Phần mềm tạo bài viết Blogspot (v3.0)")
    st.caption("✨ Tạo bố cục 2 cột chuyên nghiệp | Tự động loại bỏ nền đen và chữ tàng hình khi copy/paste")
    
    col1, col2 = st.columns([1, 2])

    # Cột 1: Hình ảnh
    with col1:
        st.subheader("📸 Cột 1: Hình ảnh đại diện")
        uploaded_file = st.file_uploader(
            "Kéo thả hoặc chọn hình ảnh vào đây", 
            type=['png', 'jpg', 'jpeg', 'gif', 'webp'],
            key="blogspot_img"
        )
        
        img_tag = "<p><i>(Chưa có hình ảnh)</i></p>"
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Ảnh xem trước", use_container_width=True)
            bytes_data = uploaded_file.read()
            b64_string = base64.b64encode(bytes_data).decode('utf-8')
            ext = uploaded_file.name.split('.')[-1].lower()
            if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                ext = 'png'
            img_tag = f'<img src="data:image/{ext};base64,{b64_string}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" alt="thumbnail" />'

    # Cột 2: Nội dung
    with col2:
        st.subheader("✍️ Cột 2: Thông tin bài viết")
        title = st.text_input("Nhập tiêu đề bài viết...", placeholder="Ví dụ: Sản phẩm mới chất lượng cao", key="blog_title")
        content_html = st.text_area(
            "Soạn thảo hoặc dán nội dung vào đây...",
            placeholder="Dán đoạn văn bản hoặc mã HTML cần làm sạch nền tại đây...",
            height=250,
            key="blog_content"
        )
        link = st.text_input("🔗 Nhập đường dẫn link...", placeholder="https://example.com", key="blog_link")
        
        st.write("")
        if st.button("🚀 TẠO MÃ HTML CHO BLOGSPOT", type="primary", use_container_width=True):
            if not title:
                st.warning("⚠️ Vui lòng nhập tiêu đề bài viết!")
            else:
                # Logic khử nền đen và chữ tàng hình (Giữ nguyên 100% từ code cũ)
                body_match = re.search(r'<body[^>]*>(.*?)</body>', content_html, re.IGNORECASE | re.DOTALL)
                processed_html = body_match.group(1) if body_match else content_html

                processed_html = re.sub(r'background(?:-color)?\s*:\s*[^;"\'>]+;?', '', processed_html, flags=re.IGNORECASE)
                processed_html = re.sub(r'color\s*:\s*[^;"\'>]+;?', '', processed_html, flags=re.IGNORECASE)
                processed_html = re.sub(r'<span style="\s*">\s*(.*?)\s*</span>', r'\1', processed_html, flags=re.IGNORECASE)

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
                st.success("🎉 Đã tạo mã thành công! Hãy nhấn biểu tượng Copy ở góc trên bên phải khung dưới đây:")
                st.code(final_html.strip(), language="html")
                
                st.write("---")
                st.subheader("👀 Xem trước giao diện thực tế:")
                st.components.v1.html(final_html, height=450, scrolling=True)

# =========================================================================
# OPTION 2: TRÌNH ĐỌC TRUYỆN CBZ API GOOGLE DRIVE (V2.0)
# =========================================================================
elif tool_choice == "⚡ 2. Trình Đọc Truyện CBZ API Google Drive (v2.0)":
    st.header("⚡ Trình Tạo Mã Đọc CBZ Bằng Google API (v2.0)")
    st.caption("🔥 Sửa lỗi nút bấm | Tự động chuyển Link thành ID | Ẩn khung Pass sau khi mở")
    
    col_input, col_output = st.columns([1, 1])
    
    with col_input:
        st.subheader("📥 Cột 1: Nhập thông tin")
        
        # 1. API Key cố định
        st.markdown("**1. Google Drive API Key (Đã cố định):**")
        st.text_input("API Key", value=FIXED_GOOGLE_API_KEY, disabled=True, label_visibility="collapsed")
        st.write("")
        
        # 2. Link Drive -> Tự bóc ID
        st.markdown("**2. Nhập ID hoặc Dán link Google Drive (Sẽ tự động bóc ID):**")
        raw_link_input = st.text_input("Link/ID Google Drive", placeholder="Dán Link hoặc nhập ID vào đây...", label_visibility="collapsed")
        
        # Xử lý tự động chuyển Link thành ID ngay khi có input (thay thế cho sự kiện KeyRelease)
        file_id = raw_link_input.strip()
        match = re.search(r'(?:id=|/d/)([\w-]+)', file_id)
        if match:
            file_id = match.group(1)
            st.info(f"💡 Đã tự động nhận diện ID file: **`{file_id}`**")
            
        st.write("")
        
        # 3. Ảnh Cover (Thumbnail tàng hình)
        st.markdown("**3. Ảnh Cover (Bị ẩn trong bài, làm Thumbnail ngoài trang chủ):**")
        cover_type = st.radio("Chọn nguồn ảnh Cover:", ["📁 Tải ảnh từ máy lên", "🔗 Dán link ảnh trực tiếp"], horizontal=True)
        
        cover_base64 = ""
        cover_link = ""
        
        if cover_type == "📁 Tải ảnh từ máy lên":
            cover_file = st.file_uploader("Chọn file ảnh Cover", type=["jpg", "jpeg", "png", "webp", "gif"], key="cbz_cover_file")
            if cover_file is not None:
                st.image(cover_file, caption="Cover xem trước", width=150)
                bytes_cover = cover_file.read()
                b64_str = base64.b64encode(bytes_cover).decode('utf-8')
                ext_c = cover_file.name.split('.')[-1].lower()
                if ext_c == "jpg": ext_c = "jpeg"
                cover_base64 = f"data:image/{ext_c};base64,{b64_str}"
        else:
            cover_link = st.text_input("Dán link ảnh Cover vào đây...", placeholder="https://example.com/cover.jpg")
            if cover_link:
                st.image(cover_link, caption="Cover từ Link", width=150)
                
        st.write("")
        btn_generate_cbz = st.button("🚀 TẠO MÃ NHÚNG CBZ", type="primary", use_container_width=True)

    with col_output:
        st.subheader("🖥️ Cột 2: Kết quả mã nhúng Blogspot")
        
        if btn_generate_cbz:
            if not file_id:
                st.warning("⚠️ Vui lòng nhập ID hoặc dán link Google Drive chứa file CBZ!")
            else:
                # Chuẩn hóa ID để dùng cho tên Hàm trong JavaScript (tránh lỗi cú pháp)
                safe_id = re.sub(r'[^a-zA-Z0-9]', 'X', file_id)
                api_key = FIXED_GOOGLE_API_KEY
                
                final_cover_src = cover_link if cover_link else cover_base64
                cover_html_block = ""
                if final_cover_src:
                    cover_html_block = f"""
<div style="display: none !important; opacity: 0; height: 0; width: 0; overflow: hidden;">
    <img src="{final_cover_src}" alt="Cover Thumbnail" />
</div>
"""
                # ==========================================================
                # LÕI MÃ HTML TRÌNH ĐỌC TRUYỆN (GIỮ NGUYÊN 100% SỰ KIỆN JS)
                # ==========================================================
                core_html = f"""
<script src="https://unpkg.com/@zip.js/zip.js/dist/zip.min.js"></script>

<div id="setup-box-{safe_id}" style="background: rgb(26, 26, 26); border-radius: 10px; color: white; font-family: sans-serif; margin-bottom: 20px; padding: 20px; text-align: center;"> 
    <input id="cbz-password-{safe_id}" placeholder="Mật khẩu giải nén (nếu có)..." onkeypress="if(event.key === 'Enter') fetchFromGoogleAPI_{safe_id}();" style="color: black; border-radius: 5px; border: 1px solid rgb(204, 204, 204); margin-bottom: 10px; max-width: 250px; padding: 10px; width: 60%; outline: none;" type="password" />
    <br />
    
    <button id="read-btn-{safe_id}" onclick="fetchFromGoogleAPI_{safe_id}()" style="background-color: #e91e63; border-radius: 5px; border: none; color: white; cursor: pointer; font-size: 16px; font-weight: bold; padding: 12px 25px; transition: 0.2s;">
        📖 Khởi chạy File Truyện
    </button>
</div>

<div id="status-box-{safe_id}" style="color: #4caf50; font-weight: bold; margin-bottom: 15px; text-align: center;"></div>

<div id="comic-viewer-{safe_id}" style="display: none; background: rgb(44, 44, 44); border-radius: 5px; padding: 10px; text-align: center; position: relative;">
    
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: white;">
        <button onclick="prevPage_{safe_id}()" style="padding: 8px 15px; cursor: pointer; background: #3498db; border: none; color: white; border-radius: 4px; font-weight: bold;">◀ Trước</button>
        <span id="page-counter-{safe_id}" style="font-weight: bold; font-size: 16px; color: #f1c40f;">1 / ?</span>
        <button onclick="nextPage_{safe_id}()" style="padding: 8px 15px; cursor: pointer; background: #3498db; border: none; color: white; border-radius: 4px; font-weight: bold;">Sau ▶</button>
    </div>

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

                full_cbz_html = f"{cover_html_block}{core_html}".strip()
                
                st.success("🎉 Đã tạo mã nhúng CBZ thành công! Hãy nhấn nút Copy ở góc trên ô dưới đây:")
                st.code(full_cbz_html, language="html")
