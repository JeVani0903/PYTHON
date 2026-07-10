import streamlit as st
import re
import json
import base64
import random
import string
import pandas as pd

# =========================================================================
# CẤU HÌNH GIAO DIỆN STREAMLIT
# =========================================================================
st.set_page_config(page_title="E With Bich Jane - Creator Studio", layout="wide", page_icon="⚡")

DRIVE_REGEX = re.compile(r'(?:id=|/d/)([\w-]+)')

def extract_gdrive_id(url):
    if not url: return ""
    match = DRIVE_REGEX.search(url.strip())
    return match.group(1) if match else url.strip()

def optimize_url(url):
    """Tự động chuyển Github Raw sang jsDelivr CDN để load siêu nhanh"""
    url = url.strip()
    gh_pattern = r'https://github\.com/([^/]+)/([^/]+)/raw/(?:refs/heads/)?([^/]+)/(.*)'
    match = re.search(gh_pattern, url)
    if match:
        u, r, b, f = match.groups()
        return f"https://cdn.jsdelivr.net/gh/{u}/{r}@{b}/{f}"
    return url

def parse_media(txt, sys_id):
    """Tự móc ảnh, audio ra khỏi chữ và chuyển hóa thành HTML"""
    audio_btn = ""
    img_html = ""
    display_txt = txt
    
    urls = re.findall(r'(https?://[^\s<"]+)', txt)
    for raw_url in urls:
        url = optimize_url(raw_url)
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

def parse_audio(txt, sys_id):
    txt, img, aud = parse_media(txt, sys_id)
    return txt, aud

def text_to_html(text):
    """Chuyển đổi xuống dòng thành thẻ <br> cho Blogspot"""
    if not text: return ""
    return text.replace('\n', '<br>')

# =========================================================================
# KHỞI TẠO SESSION STATE (LƯU TRỮ DỮ LIỆU)
# =========================================================================
if 'lecture_data' not in st.session_state: st.session_state.lecture_data = []
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = []
if 'student_data' not in st.session_state: st.session_state.student_data = pd.DataFrame(columns=["Tên/Username", "Mật khẩu", "Lớp"])
if 'global_cover' not in st.session_state: st.session_state.global_cover = ""

# =========================================================================
# GIAO DIỆN CHÍNH
# =========================================================================
st.title("⚡ E With Bich Jane - Creator Studio")

# --- SIDEBAR (BẢNG ĐIỀU KHIỂN) ---
with st.sidebar:
    st.header("BẢNG ĐIỀU KHIỂN")
    
    if st.button("🔄 LÀM MỚI TOÀN BỘ", use_container_width=True, type="primary"):
        st.session_state.lecture_data = []
        st.session_state.quiz_data = []
        st.session_state.global_cover = ""
        st.rerun()
        
    st.divider()
    
    if st.button("🚀 XUẤT MÃ HTML / JS", use_container_width=True, type="primary"):
        st.session_state.generate_trigger = True

    if st.session_state.get('generate_trigger', False):
        st.subheader("Mã HTML Của Bạn:")
        st.caption("Bấm vào biểu tượng Copy ở góc trên bên phải của ô code dưới đây.")
        
        # --- LOGIC XUẤT MÃ HTML NẰM Ở ĐÂY ---
        sys_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        lec_html_parts = []
        
        # Build Bài Giảng
        for blk in st.session_state.lecture_data:
            b_type = blk.get('type')
            title = blk.get('title') or b_type
            
            if b_type == "🎬 Video Bài Học":
                v_id = extract_gdrive_id(blk.get('link', ''))
                if v_id: lec_html_parts.append(f'<div class="lecture-section"><h3 class="section-title">🎬 {title}</h3><div class="video-container"><iframe src="https://drive.google.com/file/d/{v_id}/preview" allow="autoplay" allowfullscreen></iframe></div></div>')
            
            elif b_type == "📇 Danh sách Flashcard":
                valid_rows = blk.get('fc_rows', [])
                if not valid_rows: continue
                fc_content_parts = []
                for i, row in enumerate(valid_rows):
                    word = row['Từ vựng']; mean = row['Nghĩa']; a_url = optimize_url(row['Link Audio']); i_id = extract_gdrive_id(row['Link Ảnh'])
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
                valid_gr = blk.get('gr_rows', [])
                if not valid_gr: continue
                gr_content_parts = []
                for i, row in enumerate(valid_gr):
                    struct = row['Tên Cấu Trúc']; a_url = optimize_url(row['Link Audio']); i_id = extract_gdrive_id(row['Link Ảnh']); desc = text_to_html(row['Nội dung / Ví dụ'])
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
                a_url = optimize_url(blk.get('link', ''))
                if a_url: lec_html_parts.append(f'<div class="lecture-section"><h3 class="section-title">🎧 {title}</h3><div class="standalone-audio"><audio controls><source src="{a_url}" type="audio/mpeg">Trình duyệt không hỗ trợ audio.</audio></div></div>')

        lec_html = "".join(lec_html_parts)

        # Build Bài Tập
        quiz_html_parts = []
        js_grading_parts = []
        js_init_parts = []
        max_score = 0
        valid_quizzes = st.session_state.quiz_data

        for i, q in enumerate(valid_quizzes):
            idx = i + 1
            q_topic = q['topic']
            q_type = q['q_type']
            explanation = text_to_html(q['exp_raw'])
            
            q_text_html = text_to_html(q['q_raw'])
            urls_in_html = re.findall(r'(https?://[^\s<"]+)', q_text_html)
            img_urls = []
            q_audio_url = ""
            
            for raw_url in urls_in_html:
                url = optimize_url(raw_url)
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
                    display_txt, audio_btn = parse_audio(txt, sys_id)
                    if not display_txt and audio_btn: display_txt = f"Đáp án {val}"
                    labels.append(f'<div style="display: flex; align-items: center; margin-bottom: 8px;"><label class="opt-label" id="label-q{idx}-{val}_{sys_id}" style="flex-grow: 1; margin: 0; display:flex; align-items:center;"><input type="radio" name="q{idx}_{sys_id}" value="{val}" style="margin-right:8px;"> <span style="font-weight:bold; margin-right:5px;">{val}.</span> {display_txt}</label>{audio_btn}</div>')
                input_html = f'<div class="card-options">{"".join(labels)}</div>'
                js_grading_parts.append(f"var q{idx} = container.querySelector('input[name=\"q{idx}_{sys_id}\"]:checked'); var q{idx}Correct = '{correct_opt}'; container.querySelectorAll('#card-q{idx}_{sys_id} .opt-label').forEach(function(lbl) {{ lbl.classList.remove('correct', 'incorrect'); }}); if (q{idx}) {{ if (q{idx}.value === q{idx}Correct) {{ score++; container.querySelector('#label-q{idx}-' + q{idx}.value + '_{sys_id}').classList.add('correct'); }} else {{ container.querySelector('#label-q{idx}-' + q{idx}.value + '_{sys_id}').classList.add('incorrect'); container.querySelector('#label-q{idx}-' + q{idx}Correct + '_{sys_id}').classList.add('correct'); }} }} else {{ container.querySelector('#label-q{idx}-' + q{idx}Correct + '_{sys_id}').classList.add('correct'); }} container.querySelector('#exp-q{idx}_{sys_id}').style.display = 'block';")

            elif q_type == "Điền từ (Ngắn)":
                max_score += 1
                valid_fills = q.get('fills', [])
                valid_ans_array = []
                input_tags = []
                for b_idx, ans_str in enumerate(valid_fills):
                    valid_ans_array.append([a.strip().lower() for a in ans_str.split(',')])
                    p_text = "Nhập câu trả lời..." if len(valid_fills) == 1 else f"Nhập câu trả lời {b_idx+1}..."
                    input_tags.append(f'<input type="text" class="essay-input short-input blank-input-q{idx}_{sys_id}" style="width:100%; box-sizing:border-box; margin-bottom:8px;" placeholder="{p_text}">')
                input_html = f'<div class="essay-container"><div class="input-wrapper" style="display:flex; flex-direction:column; align-items:stretch; gap:8px;">{"".join(input_tags)}<div class="status-icon" id="icon-q{idx}_{sys_id}" style="align-self:flex-start;"></div></div></div>'
                js_grading_parts.append(f"var q{idx}Valid = {str(valid_ans_array)}; var q{idx}Inputs = container.querySelectorAll('.blank-input-q{idx}_{sys_id}'); var q{idx}Icon = container.querySelector('#icon-q{idx}_{sys_id}'); var q{idx}AllCorrect = true; if (q{idx}Inputs.length > 0) {{ q{idx}Inputs.forEach(function(inp, b_idx) {{ var ans = inp.value.trim().toLowerCase(); inp.classList.remove('input-correct', 'input-incorrect'); if (q{idx}Valid[b_idx] && q{idx}Valid[b_idx].indexOf(ans) !== -1) {{ inp.classList.add('input-correct'); }} else {{ inp.classList.add('input-incorrect'); q{idx}AllCorrect = false; }} }}); if (q{idx}AllCorrect) {{ score++; q{idx}Icon.className = 'status-icon text-correct'; q{idx}Icon.innerHTML = '✅ Đúng'; }} else {{ q{idx}Icon.className = 'status-icon text-incorrect'; q{idx}Icon.innerHTML = '❌ Sai'; }} }} container.querySelector('#exp-q{idx}_{sys_id}').style.display = 'block';")

            elif q_type == "Nối câu":
                valid_matches = q.get('matches', [])
                if valid_matches:
                    max_score += len(valid_matches)
                    right_items = [{"text": m['r'], "orig_idx": j} for j, m in enumerate(valid_matches)]
                    random.shuffle(right_items)
                    
                    letters = list(string.ascii_uppercase)
                    for j, r_item in enumerate(right_items): r_item['id'] = letters[j] if j < len(letters) else str(j)
                    correct_mapping = {r_item['orig_idx']: r_item['id'] for r_item in right_items}
                    
                    left_html = ""; right_html = ""; input_tags = []
                    
                    for j, m in enumerate(valid_matches):
                        l_txt, l_img, l_audio = parse_media(m['l'], sys_id)
                        left_content = f'{l_img}<span style="margin-left:5px; flex-grow:1;">{l_txt}</span>{l_audio}'
                        left_html += f'<div class="match-item" style="display:flex; align-items:center;"><strong>{j+1}.</strong> {left_content}</div>'
                        
                    for r_item in right_items:
                        r_txt, r_img, r_audio = parse_media(r_item['text'], sys_id)
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
        final_cover_src = st.session_state.global_cover
        if final_cover_src:
            if "drive.google.com" in final_cover_src.lower() or "id=" in final_cover_src.lower():
                g_id = extract_gdrive_id(final_cover_src)
                cover_opt = f"https://drive.google.com/thumbnail?id={g_id}&sz=w1000" if g_id else final_cover_src
            else:
                cover_opt = optimize_url(final_cover_src) if final_cover_src.startswith("http") else final_cover_src
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
        st.session_state.generated_code = final_code
        st.session_state.generate_trigger = False

# --- TẠO TAB ---
tab_config, tab_lecture, tab_quiz, tab_student = st.tabs(["⚙️ Cấu Hình Chung", "📚 Bài Giảng", "📝 Bài Tập", "👨‍🎓 Học Sinh"])

# =========================================================================
# TAB CẤU HÌNH CHUNG
# =========================================================================
with tab_config:
    st.subheader("Cấu Hình Bài Viết (Áp dụng chung)")
    
    st.markdown("**Ảnh Cover (Tàng hình trong bài, làm Thumbnail Blogspot):**")
    
    col_cv1, col_cv2 = st.columns([3, 1])
    with col_cv1:
        st.text_input("Dán Link ảnh Cover trực tiếp vào đây:", key="input_cover_link")
    with col_cv2:
        st.write("Hoặc chọn từ máy:")
        uploaded_cover = st.file_uploader("Chọn ảnh", type=["jpg", "jpeg", "png", "webp", "gif"], label_visibility="collapsed")
    
    if uploaded_cover:
        try:
            b64_string = base64.b64encode(uploaded_cover.read()).decode('utf-8')
            ext = uploaded_cover.name.split('.')[-1].lower()
            if ext == "jpg": ext = "jpeg"
            st.session_state.global_cover = f"data:image/{ext};base64,{b64_string}"
            st.success(f"Đã nạp ảnh: {uploaded_cover.name}")
        except Exception as e:
            st.error(f"Lỗi: {e}")
    elif st.session_state.input_cover_link:
        st.session_state.global_cover = st.session_state.input_cover_link
    else:
        st.session_state.global_cover = ""

# =========================================================================
# TAB BÀI GIẢNG
# =========================================================================
with tab_lecture:
    if len(st.session_state.lecture_data) > 0:
        st.subheader("Danh sách Mục Bài Giảng")
        for i, lec in enumerate(st.session_state.lecture_data):
            title = lec.get('title') or lec.get('type')
            with st.expander(f"Mục {i+1}: {title}"):
                c1, c2 = st.columns([8, 2])
                with c1: st.write(f"Loại: **{lec.get('type')}**")
                with c2:
                    if st.button("❌ Xóa", key=f"del_lec_{i}", type="secondary", use_container_width=True):
                        del st.session_state.lecture_data[i]
                        st.rerun()

    st.divider()
    lec_idx = len(st.session_state.lecture_data)
    with st.expander("➕ SOẠN MỤC BÀI GIẢNG MỚI", expanded=True):
        l_type = st.selectbox("Loại nội dung:", ["🎬 Video Bài Học", "📇 Danh sách Flashcard", "📖 Ngữ Pháp", "🎧 Audio Độc Lập"], key=f"lec_type_{lec_idx}")
        l_title = st.text_input("Tiêu đề hiển thị:", key=f"lec_title_{lec_idx}")
        
        l_link = ""
        fc_data = []
        gr_data = []
        
        if l_type in ["🎬 Video Bài Học", "🎧 Audio Độc Lập"]:
            l_link = st.text_input("Dán Link Video G-Drive hoặc Link Audio (.mp3) trực tiếp:", key=f"lec_link_{lec_idx}")
        
        elif l_type == "📇 Danh sách Flashcard":
            df_fc = pd.DataFrame([{"Từ vựng": "", "Nghĩa": "", "Link Audio": "", "Link Ảnh": ""}])
            fc_data = st.data_editor(df_fc, num_rows="dynamic", use_container_width=True, key=f"lec_fc_{lec_idx}")
            
        elif l_type == "📖 Ngữ Pháp":
            df_gr = pd.DataFrame([{"Tên Cấu Trúc": "", "Link Audio": "", "Link Ảnh": "", "Nội dung / Ví dụ": ""}])
            gr_data = st.data_editor(df_gr, num_rows="dynamic", use_container_width=True, key=f"lec_gr_{lec_idx}")

        if st.button("✔ XÁC NHẬN LƯU BÀI GIẢNG", type="primary", key=f"save_lec_{lec_idx}"):
            new_lec = {
                "type": l_type, "title": l_title, "link": l_link,
                "fc_rows": fc_data.to_dict('records') if isinstance(fc_data, pd.DataFrame) else [],
                "gr_rows": gr_data.to_dict('records') if isinstance(gr_data, pd.DataFrame) else []
            }
            st.session_state.lecture_data.append(new_lec)
            st.rerun()

# =========================================================================
# TAB BÀI TẬP (2 CỘT STUDIO)
# =========================================================================
with tab_quiz:
    if len(st.session_state.quiz_data) > 0:
        st.subheader("Danh sách Câu Hỏi")
        for i, q in enumerate(st.session_state.quiz_data):
            title = q.get('topic') or q.get('q_raw')[:50]
            if not title: title = "Câu hỏi " + q.get('q_type')
            with st.expander(f"Câu {i+1}: {title}"):
                c1, c2 = st.columns([8, 2])
                with c1: st.write(f"Loại: **{q.get('q_type')}**")
                with c2:
                    if st.button("❌ Xóa", key=f"del_quiz_{i}", type="secondary", use_container_width=True):
                        del st.session_state.quiz_data[i]
                        st.rerun()

    st.divider()
    q_idx = len(st.session_state.quiz_data)
    with st.expander("➕ SOẠN CÂU HỎI MỚI (Studio Mode)", expanded=True):
        st.caption("👁 Nếu muốn Ẩn/Hiện nội dung để dễ nhìn, bạn chỉ cần bấm vào tiêu đề '➕ SOẠN CÂU HỎI MỚI' phía trên.")
        
        q_topic = st.text_input("📌 Nhập chủ đề câu hỏi (Tùy chọn)...", key=f"q_topic_{q_idx}")
        
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            st.markdown("**Nội dung câu hỏi (Dán link Ảnh/Audio thẳng vào đây):**")
            q_raw = st.text_area("Hỗ trợ gõ mã HTML cơ bản (<b>, <i>...)", height=350, label_visibility="collapsed", key=f"q_raw_{q_idx}")
            
        with col_q2:
            q_type = st.selectbox("Loại câu hỏi:", ["Trắc nghiệm", "Điền từ (Ngắn)", "Nối câu"], key=f"q_type_{q_idx}")
            
            mcq_data = {"a": "", "b": "", "c": "", "d": "", "correct": "A"}
            fill_data = []
            match_data = []
            
            if q_type == "Trắc nghiệm":
                st.caption("* Mẹo: Dán thẳng link Google Drive HOẶC link .mp3 vào ô đáp án để tạo nút Loa 🔊")
                mcq_data["a"] = st.text_input("Đáp án A", key=f"mcq_a_{q_idx}")
                mcq_data["b"] = st.text_input("Đáp án B", key=f"mcq_b_{q_idx}")
                mcq_data["c"] = st.text_input("Đáp án C", key=f"mcq_c_{q_idx}")
                mcq_data["d"] = st.text_input("Đáp án D", key=f"mcq_d_{q_idx}")
                mcq_data["correct"] = st.selectbox("Đáp án ĐÚNG:", ["A", "B", "C", "D"], key=f"mcq_corr_{q_idx}")
                
            elif q_type == "Điền từ (Ngắn)":
                st.caption("Mỗi dòng 1 ô cần điền (Nhiều đáp án đúng cách nhau bằng dấu phẩy):")
                df_fills = pd.DataFrame([{"Đáp án": ""}])
                fill_df = st.data_editor(df_fills, num_rows="dynamic", use_container_width=True, key=f"fill_{q_idx}")
                fill_data = fill_df["Đáp án"].tolist()
                
            elif q_type == "Nối câu":
                st.caption("Nhập các cặp Nối câu (Hệ thống tự đảo lộn vế phải):")
                df_match = pd.DataFrame([{"Vế Trái": "", "Vế Phải (Đúng)": ""}])
                match_df = st.data_editor(df_match, num_rows="dynamic", use_container_width=True, key=f"match_{q_idx}")
                match_data = [{"l": r["Vế Trái"], "r": r["Vế Phải (Đúng)"]} for _, r in match_df.iterrows()]
                
            st.markdown("**Giải thích / Đáp án mẫu:**")
            exp_raw = st.text_area("Giải thích", height=100, label_visibility="collapsed", key=f"exp_{q_idx}")

        if st.button("✔ XÁC NHẬN LƯU CÂU HỎI", type="primary", use_container_width=True, key=f"save_q_{q_idx}"):
            new_quiz = {
                "topic": q_topic,
                "q_raw": q_raw,
                "q_html": text_to_html(q_raw),
                "q_type": q_type,
                "mcq": mcq_data,
                "fills": fill_data,
                "matches": match_data,
                "exp_raw": exp_raw,
                "exp_html": text_to_html(exp_raw)
            }
            st.session_state.quiz_data.append(new_quiz)
            st.rerun()

# =========================================================================
# TAB HỌC SINH
# =========================================================================
with tab_student:
    st.subheader("Quản lý Dữ liệu Học Sinh")
    st.caption("Thay đổi dữ liệu trực tiếp trên bảng. Nhấn dấu `+` để thêm dòng mới. Nhấn biểu tượng thùng rác để xóa.")
    st.session_state.student_data = st.data_editor(st.session_state.student_data, num_rows="dynamic", use_container_width=True)