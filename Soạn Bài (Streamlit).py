import streamlit as st
import re
import random
import string
import json
import base64
import time
import os

# =========================================================================
# HELPER FUNCTIONS & THUẬT TOÁN
# =========================================================================
DRIVE_REGEX = re.compile(r'(?:id=|/d/)([\w-]+)')

def extract_gdrive_id(url):
    if not url: return ""
    match = DRIVE_REGEX.search(url.strip())
    return match.group(1) if match else ""

def strip_html(text):
    text = re.sub(r'<br\s*/?>', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def optimize_url(url):
    url = url.strip()
    match = re.search(r'https://github\.com/([^/]+)/([^/]+)/raw/(?:refs/heads/)?([^/]+)/(.*)', url)
    if match:
        u, r, b, f = match.groups()
        return f"https://cdn.jsdelivr.net/gh/{u}/{r}@{b}/{f}"
    return url

def get_direct_img_link(raw_url, size="w800"):
    raw_url = raw_url.strip()
    if not raw_url: return ""
    g_id = extract_gdrive_id(raw_url)
    if g_id:
        return f"https://drive.google.com/thumbnail?id={g_id}&sz={size}"
    return optimize_url(raw_url)

def parse_media(txt, sys_id):
    audio_btn, img_html, display_txt = "", "", txt
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

# Crossword Logic
def is_valid_placement(word, x, y, direction, grid):
    for i, char in enumerate(word):
        cx = x + i if direction == 'across' else x
        cy = y if direction == 'across' else y + i
        if (cx, cy) in grid:
            if grid[(cx, cy)] != char: return False
        else:
            if direction == 'across':
                if (cx, cy - 1) in grid or (cx, cy + 1) in grid: return False
            else:
                if (cx - 1, cy) in grid or (cx + 1, cy) in grid: return False
        if i == 0:
            if direction == 'across' and (cx - 1, cy) in grid: return False
            if direction == 'down' and (cx, cy - 1) in grid: return False
        if i == len(word) - 1:
            if direction == 'across' and (cx + 1, cy) in grid: return False
            if direction == 'down' and (cx, cy + 1) in grid: return False
    return True

def generate_crossword_layout(original_word_list):
    max_attempts = 1000
    for attempt in range(max_attempts):
        word_list = original_word_list.copy()
        if attempt == 0:
            word_list.sort(key=lambda x: len(x['word']), reverse=True)
        else:
            random.shuffle(word_list)
            
        placed = []
        grid = {}
        success = True
        
        for item in word_list:
            word = item['word']
            clue = item['clue']
            if not placed:
                placed.append({"word": word, "x": 0, "y": 0, "dir": "across", "clue": clue})
                for i, c in enumerate(word): grid[(i, 0)] = c
                continue
            
            valid_placements = []
            for p in placed:
                for i, p_char in enumerate(p['word']):
                    for j, char in enumerate(word):
                        if p_char == char:
                            if p['dir'] == 'across':
                                start_x, start_y, new_dir = p['x'] + i, p['y'] - j, 'down'
                            else:
                                start_x, start_y, new_dir = p['x'] - j, p['y'] + i, 'across'
                            if is_valid_placement(word, start_x, start_y, new_dir, grid):
                                valid_placements.append((start_x, start_y, new_dir))
            if valid_placements:
                start_x, start_y, new_dir = random.choice(valid_placements)
                placed.append({"word": word, "x": start_x, "y": start_y, "dir": new_dir, "clue": clue})
                for i, char in enumerate(word):
                    if new_dir == 'across': grid[(start_x + i, start_y)] = char
                    else: grid[(start_x, start_y + i)] = char
            else:
                success = False
                break 
        if success:
            min_x = min([p['x'] for p in placed])
            min_y = min([p['y'] for p in placed])
            for p in placed:
                p['x'] -= min_x
                p['y'] -= min_y
            start_coords = []
            for p in placed:
                if (p['x'], p['y']) not in start_coords:
                    start_coords.append((p['x'], p['y']))
            start_coords.sort(key=lambda c: (c[1], c[0])) 
            coord_to_id = {coord: idx + 1 for idx, coord in enumerate(start_coords)}
            for p in placed:
                p['id'] = coord_to_id[(p['x'], p['y'])]
            placed.sort(key=lambda p: (p['id'], p['dir']))
            return placed, "Success"
    return None, "Vẫn không thể xếp được lưới sau 1000 lần thử. Vui lòng đổi/thêm/bớt từ khóa!"

def check_connectivity(words_data):
    n = len(words_data)
    adj = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if set(words_data[i]['word']).intersection(set(words_data[j]['word'])):
                adj[i].append(j)
                adj[j].append(i)
    all_nodes = set(range(n))
    components = []
    while all_nodes:
        start = all_nodes.pop()
        comp = {start}
        q = [start]
        while q:
            curr = q.pop(0)
            for neighbor in adj[curr]:
                if neighbor in all_nodes:
                    all_nodes.remove(neighbor)
                    comp.add(neighbor)
                    q.append(neighbor)
        components.append(comp)
    if len(components) > 1:
        components.sort(key=len)
        smallest_comp = components[0]
        isolated_words = [words_data[i]['word'] for i in smallest_comp]
        return isolated_words
    return []

# =========================================================================
# SYSTEM & DATA MANAGEMENT
# =========================================================================
DATA_FILE = "v3_backup_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"config": {"cover": "", "timer": ""}, "lecture_data": [], "quiz_data": []}

def save_data():
    state = {
        "config": st.session_state.config,
        "lecture_data": st.session_state.lecture_data,
        "quiz_data": st.session_state.quiz_data
    }
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
    except: pass

def init_session():
    if 'initialized' not in st.session_state:
        data = load_data()
        st.session_state.config = data.get("config", {"cover": "", "timer": ""})
        st.session_state.lecture_data = data.get("lecture_data", [])
        st.session_state.quiz_data = data.get("quiz_data", [])
        st.session_state.current_page = "config"
        st.session_state.edit_idx = -1
        st.session_state.initialized = True

def navigate(page, edit_idx=-1):
    st.session_state.current_page = page
    st.session_state.edit_idx = edit_idx
    st.rerun()

# =========================================================================
# CODE GENERATOR
# =========================================================================
def generate_code_block():
    sys_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    try:
        global_timer_mins = float(st.session_state.config.get("timer", "0").strip())
        global_timer_secs = int(global_timer_mins * 60)
    except:
        global_timer_secs = 0
    
    lec_html_parts = []
    for blk in st.session_state.lecture_data:
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
                word = row['w']; mean = row['m']
                has_tts = row.get('a_tts', False)
                if has_tts:
                    tts_text = strip_html(word)
                    b64_tts = base64.b64encode(tts_text.encode('utf-8')).decode('utf-8')
                    audio_btn = f'''<button type="button" class="audio-icon-btn" onclick="speakTTSBase64_{sys_id}('{b64_tts}')" title="Nghe phát âm">🔊</button>'''
                else: audio_btn = ""
                
                img_url = get_direct_img_link(row.get('i', ''), "w800")
                img_col = f'''<div class="fc-img-col"><img src="{img_url}" loading="lazy" class="fc-img"></div>''' if img_url else ""
                display_style = 'display: block;' if i == 0 else 'display: none;'
                fc_content_parts.append(f'<div class="flashcard fc-slide-{sys_id}" style="{display_style}"><div class="flashcard-body">{img_col}<div class="fc-text-col"><strong class="fc-word">{word}</strong><span class="fc-meaning">{mean}</span>{audio_btn}</div></div></div>')
            nav_btns_top = f'<div style="display: inline-flex; align-items: center; background: #f8f9fa; padding: 4px 10px; border-radius: 6px; border: 1px solid #dadce0;"><button type="button" class="nav-control-btn" onclick="moveFcSlide_{sys_id}(-1)">&#10094; Trước</button><span class="fc-counter" id="fc-counter-top-{sys_id}">1 / {len(valid_rows)}</span><button type="button" class="nav-control-btn" onclick="moveFcSlide_{sys_id}(1)">Sau &#10095;</button></div>' if len(valid_rows) > 1 else ""
            header_html = f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;"><h3 class="section-title" style="margin-bottom: 0;">📇 {title}</h3>{nav_btns_top}</div>'
            lec_html_parts.append(f'<div class="lecture-section">{header_html}<div class="slider-container-main"><div class="flashcard-container">{"".join(fc_content_parts)}</div></div></div>')
        elif b_type == "📖 Ngữ Pháp":
            valid_gr = [r for r in blk.get('gr_rows', []) if r["t"] or r["d_html"]]
            if not valid_gr: continue
            gr_content_parts = []
            for i, row in enumerate(valid_gr):
                struct = row['t']; desc = row['d_html']
                has_tts = row.get('a_tts', False)
                tts_text = strip_html(row.get('d_raw', ''))
                if has_tts and tts_text:
                    b64_tts = base64.b64encode(tts_text.encode('utf-8')).decode('utf-8')
                    audio_btn = f'''<button type="button" class="audio-icon-btn" onclick="speakTTSBase64_{sys_id}('{b64_tts}')" title="Nghe giải thích">🔊</button>'''
                else: audio_btn = ""
                
                img_url = get_direct_img_link(row.get('i', ''), "w800")
                img_col = f'''<div class="fc-img-col"><img src="{img_url}" loading="lazy" class="fc-img"></div>''' if img_url else ""
                display_style = 'display: block;' if i == 0 else 'display: none;'
                gr_content_parts.append(f'<div class="grammar-box gr-slide-{sys_id}" style="{display_style}"><div class="grammar-header"><span>{struct}</span></div><div class="flashcard-body" style="padding: 18px;">{img_col}<div class="fc-text-col" style="padding-top: 0;"><div class="grammar-text">{desc}</div><div style="margin-top:15px;">{audio_btn}</div></div></div></div>')
            nav_btns_top = f'<div style="display: inline-flex; align-items: center; background: #f8f9fa; padding: 4px 10px; border-radius: 6px; border: 1px solid #dadce0;"><button type="button" class="nav-control-btn" onclick="moveGrSlide_{sys_id}(-1)">&#10094; Trước</button><span class="fc-counter" id="gr-counter-top-{sys_id}">1 / {len(valid_gr)}</span><button type="button" class="nav-control-btn" onclick="moveGrSlide_{sys_id}(1)">Sau &#10095;</button></div>' if len(valid_gr) > 1 else ""
            header_html = f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;"><h3 class="section-title" style="margin-bottom: 0;">📖 {title}</h3>{nav_btns_top}</div>'
            lec_html_parts.append(f'<div class="lecture-section">{header_html}<div class="slider-container-main">{"".join(gr_content_parts)}</div></div>')
        elif b_type == "🎧 Audio Độc Lập":
            a_url = optimize_url(blk.get('link', ''))
            if a_url: lec_html_parts.append(f'<div class="lecture-section"><h3 class="section-title">🎧 {title}</h3><div class="standalone-audio"><audio controls><source src="{a_url}" type="audio/mpeg"></audio></div></div>')

    # 2. QUIZ
    quiz_html_parts, js_grading_parts, js_init_parts = [], [], []
    max_score = 0
    valid_quizzes = st.session_state.quiz_data
    
    for i, q in enumerate(valid_quizzes):
        idx = i + 1
        q_topic = q.get('topic', '')
        q_type = q.get('q_type', '')
        explanation = q.get('exp_html', '')
        
        q_text_html = q.get('q_html', '')
        urls_in_html = re.findall(r'(https?://[^\s<"]+)', q_text_html)
        img_urls = []
        for raw_url in urls_in_html:
            img_urls.append(raw_url)
            q_text_html = q_text_html.replace(raw_url, '')
        q_text_html = re.sub(r'^(?:<br>|\s)+', '', q_text_html)
        q_text_html = re.sub(r'(?:<br>|\s)+$', '', q_text_html).strip()
        
        topic_html = f'<div class="quiz-topic-badge">📌 {q_topic}</div>' if q_topic else ""
        
        img_html = ""
        if img_urls:
            slides = []
            for j, url in enumerate(img_urls):
                final_url = get_direct_img_link(url, "w1000")
                display = 'block' if j == 0 else 'none'
                active_cls = ' active' if j == 0 else ''
                slides.append(f'<img class="quiz-img img-inner-slide-q{idx}-{sys_id}{active_cls}" src="{final_url}" loading="lazy" style="display: {display};">')
            nav_btns = f'<button type="button" class="nav-img-btn prev-btn" onclick="moveImgSlide_{sys_id}(\'q{idx}\', -1)">&#10094;</button><button type="button" class="nav-img-btn next-btn" onclick="moveImgSlide_{sys_id}(\'q{idx}\', 1)">&#10095;</button><div class="slide-counter" id="img-counter-q{idx}-{sys_id}">1 / {len(img_urls)}</div>' if len(img_urls) > 1 else ""
            img_html = f'<div class="carousel-container" data-qid="q{idx}" tabindex="0" style="margin-bottom:15px;"><div class="slides-wrapper">{"".join(slides)}</div>{nav_btns}</div>'

        input_html = ""
        
        if q_type == "Trắc nghiệm":
            max_score += 1
            mcq_data = q.get('mcq', {})
            correct_opt = mcq_data.get('correct', 'A')
            mcq_tts = q.get('mcq_tts', {})
            opts = [("A", mcq_data.get('a','')), ("B", mcq_data.get('b','')), ("C", mcq_data.get('c','')), ("D", mcq_data.get('d',''))]
            labels = []
            for val, txt in opts:
                if not txt: continue
                display_txt, opt_img_html, audio_btn = parse_media(txt, sys_id)
                if mcq_tts.get(val, False):
                    tts_text = strip_html(display_txt) if display_txt else strip_html(txt)
                    b64_tts = base64.b64encode(tts_text.encode('utf-8')).decode('utf-8')
                    audio_btn = f'<button type="button" class="audio-icon-btn" onclick="speakTTSBase64_{sys_id}(\'{b64_tts}\')" style="margin: 0 0 0 10px; flex-shrink: 0; width: 35px; height: 35px; font-size: 16px;">🔊</button>'
                    display_txt = "" 
                
                if not display_txt and not opt_img_html and audio_btn:
                    display_txt = f"Đáp án {val}"
                    
                inner_content = f"{opt_img_html}<span class='opt-text' style='margin-left: 5px;'>{display_txt}</span>" if display_txt else opt_img_html
                    
                labels.append(f'<div style="display: flex; align-items: center; margin-bottom: 8px;">'
                              f'<label class="opt-label hover-yellow" id="label-q{idx}-{val}_{sys_id}" style="flex-grow: 1; margin: 0; display:flex; align-items:center;">'
                              f'<input type="radio" name="q{idx}_{sys_id}" value="{val}" style="margin-right:8px;"> '
                              f'<span style="font-weight:bold; margin-right:5px;">{val}.</span> {inner_content}</label>{audio_btn}</div>')
            input_html = f'<div class="card-options">{"".join(labels)}</div>'
            js_grading_parts.append(f"var q{idx} = container.querySelector('input[name=\"q{idx}_{sys_id}\"]:checked'); var q{idx}Correct = '{correct_opt}'; container.querySelectorAll('#card-q{idx}_{sys_id} .opt-label').forEach(function(lbl) {{ lbl.classList.remove('correct', 'incorrect'); }}); if (q{idx}) {{ if (q{idx}.value === q{idx}Correct) {{ score++; container.querySelector('#label-q{idx}-' + q{idx}.value + '_{sys_id}').classList.add('correct'); }} else {{ container.querySelector('#label-q{idx}-' + q{idx}.value + '_{sys_id}').classList.add('incorrect'); container.querySelector('#label-q{idx}-' + q{idx}Correct + '_{sys_id}').classList.add('correct'); }} }} else {{ container.querySelector('#label-q{idx}-' + q{idx}Correct + '_{sys_id}').classList.add('correct'); }} container.querySelector('#exp-q{idx}_{sys_id}').style.display = 'block';")

        elif q_type == "Nối câu":
            valid_matches = [m for m in q.get('matches', []) if m['l'] or m['r']]
            if valid_matches:
                max_score += len(valid_matches)
                right_items = [{"text": m['r'], "orig_idx": k, "r_tts": m.get('r_tts', False)} for k, m in enumerate(valid_matches)]
                random.shuffle(right_items)
                letters = list(string.ascii_uppercase)
                for j, r_item in enumerate(right_items): r_item['id'] = letters[j] if j < len(letters) else str(j)
                correct_mapping = {r_item['orig_idx']: r_item['id'] for r_item in right_items}
                left_html, right_html, input_tags = "", "", []
                
                for j, m in enumerate(valid_matches):
                    l_txt, l_img, l_audio = parse_media(m['l'], sys_id)
                    if m.get('l_tts', False):
                        tts_text = strip_html(l_txt)
                        b64_tts = base64.b64encode(tts_text.encode('utf-8')).decode('utf-8')
                        l_audio = f'<button type="button" class="audio-icon-btn" onclick="speakTTSBase64_{sys_id}(\'{b64_tts}\')" style="margin: 0; flex-shrink: 0; width: 35px; height: 35px; font-size: 16px;">🔊</button>'
                        l_txt = ""  
                    left_html += f'<div class="match-item hover-yellow" style="display:flex; align-items:center;"><strong>{j+1}.</strong> {l_img}<span style="margin-left:5px; flex-grow:1;">{l_txt}</span>{l_audio}</div>'
                    
                for r_item in right_items:
                    r_txt, r_img, r_audio = parse_media(r_item['text'], sys_id)
                    if r_item.get('r_tts', False):
                        tts_text = strip_html(r_txt)
                        b64_tts = base64.b64encode(tts_text.encode('utf-8')).decode('utf-8')
                        r_audio = f'<button type="button" class="audio-icon-btn" onclick="speakTTSBase64_{sys_id}(\'{b64_tts}\')" style="margin: 0; flex-shrink: 0; width: 35px; height: 35px; font-size: 16px;">🔊</button>'
                        r_txt = "" 
                    right_html += f'<div class="match-item right-item hover-yellow" data-orig-idx="{r_item["orig_idx"]}" style="display:flex; align-items:center;"><strong class="right-label">{r_item["id"]}.</strong> {r_img}<span style="margin-left:5px; flex-grow:1;">{r_txt}</span>{r_audio}</div>'
                    
                for j in range(len(valid_matches)):
                    options = '<option value="">---</option>'
                    for r_item in sorted(right_items, key=lambda x: str(x['id'])): options += f'<option value="{r_item["id"]}">{r_item["id"]}</option>'
                    input_tags.append(f'<div style="margin-right:15px; margin-bottom:10px; display:inline-block;"><strong>{j+1}.</strong> <select class="match-select match-input-q{idx}_{sys_id} quiz-enter-trigger">{options}</select></div>')
                    
                input_html = f'<div class="match-container" style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:10px;"><div class="match-col" style="flex:1; min-width:200px;">{left_html}</div><div class="match-col match-right-container-q{idx}_{sys_id}" style="flex:1; min-width:200px;">{right_html}</div></div><div class="match-answers" style="display:block; padding-top:10px; border-top:1px dashed #ccc;">{"".join(input_tags)}<div class="status-icon" id="icon-q{idx}_{sys_id}" style="margin-top: 5px;"></div></div>'
                correct_json = json.dumps([correct_mapping[j] for j in range(len(valid_matches))])
                js_grading_parts.append(f"var q{idx}Valid = {correct_json}; var q{idx}Inputs = container.querySelectorAll('.match-input-q{idx}_{sys_id}'); var q{idx}Icon = container.querySelector('#icon-q{idx}_{sys_id}'); var q{idx}AllCorrect = true; if (q{idx}Inputs.length > 0) {{ q{idx}Inputs.forEach(function(inp, b_idx) {{ var ans = inp.value; inp.classList.remove('input-correct', 'input-incorrect'); if (ans === q{idx}Valid[b_idx]) {{ inp.classList.add('input-correct'); score++; }} else {{ inp.classList.add('input-incorrect'); q{idx}AllCorrect = false; }} }}); if (q{idx}AllCorrect) {{ q{idx}Icon.className = 'status-icon text-correct'; q{idx}Icon.innerHTML = '✅ Hoàn toàn chính xác'; }} else {{ q{idx}Icon.className = 'status-icon text-incorrect'; q{idx}Icon.innerHTML = '❌ Còn câu nối sai'; }} }} container.querySelector('#exp-q{idx}_{sys_id}').style.display = 'block';")

        elif q_type == "Điền từ (V3)":
            max_score += 1
            q_html_content = q.get("v3_html_content", "")
            valid_ans_array = q.get('v3_answers', [])
            display_ans_array = [v[0] if isinstance(v, list) and v else v for v in valid_ans_array]
            
            for b_idx in range(len(valid_ans_array)):
                w = max(60, len(str(display_ans_array[b_idx])) * 11) if display_ans_array[b_idx] else 60
                input_field = f'<input type="text" class="blank-input v3-input-q{idx}_{sys_id} quiz-enter-trigger" style="width: {w}px; display:inline-block;" placeholder="...">'
                q_html_content = q_html_content.replace(f'[[BLANK_{b_idx}]]', input_field)
            
            v3_audio_btn = ""
            if q.get("v3_tts", False):
                tts_v3_text = strip_html(q.get("v3_raw_text", ""))
                b64_tts_v3 = base64.b64encode(tts_v3_text.encode('utf-8')).decode('utf-8')
                v3_audio_btn = f'''<div style="margin-bottom: 15px;"><button type="button" style="background:#e8f0fe; border:none; padding:8px 15px; border-radius:20px; color:#1a73e8; font-weight:bold; cursor:pointer;" onclick="speakTTSBase64_{sys_id}('{b64_tts_v3}')">🔊 Nghe Đoạn Văn</button></div>'''

            v3_img_url = get_direct_img_link(q.get("v3_image", ""), "w800")
            v3_img_html = f'''<div style="text-align:center; margin-bottom:15px;"><img src="{v3_img_url}" style="max-width:100%; max-height:350px; border-radius:8px; object-fit:contain;"></div>''' if v3_img_url else ""

            top_v3_elements = ""
            if v3_img_html or v3_audio_btn:
                top_v3_elements = f'<div style="text-align:center; margin-bottom:10px;">{v3_img_html}{v3_audio_btn}</div>'

            input_html = f'{top_v3_elements}<div class="v3-container" style="line-height: 2.2; font-size: 16px; background-color: white; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">{q_html_content}</div><div class="status-icon" id="icon-q{idx}_{sys_id}" style="margin-top: 10px;"></div>'
            
            valid_json = json.dumps(valid_ans_array, ensure_ascii=False); display_json = json.dumps(display_ans_array, ensure_ascii=False)
            js_grading_parts.append(f"var q{idx}Valid = {valid_json}; var q{idx}Display = {display_json}; var q{idx}Inputs = container.querySelectorAll('.v3-input-q{idx}_{sys_id}'); var q{idx}Icon = container.querySelector('#icon-q{idx}_{sys_id}'); var q{idx}AllCorrect = true; if (q{idx}Inputs.length > 0) {{ q{idx}Inputs.forEach(function(inp, b_idx) {{ var ans = inp.value.trim().toLowerCase().replace(/[.,?!;: ]+$/, ''); inp.classList.remove('input-correct', 'input-incorrect'); var nextEl = inp.nextSibling; if (nextEl && nextEl.className === 'correction-span') {{ nextEl.parentNode.removeChild(nextEl); }} var isCorrect = false; if (Array.isArray(q{idx}Valid[b_idx])) {{ isCorrect = q{idx}Valid[b_idx].some(function(v) {{ return v.trim().toLowerCase().replace(/[.,?!;: ]+$/, '') === ans; }}); }} else {{ isCorrect = (q{idx}Valid[b_idx].trim().toLowerCase().replace(/[.,?!;: ]+$/, '') === ans); }} if (isCorrect) {{ inp.classList.add('input-correct'); }} else {{ inp.classList.add('input-incorrect'); q{idx}AllCorrect = false; var corr = document.createElement('span'); corr.className = 'correction-span'; corr.style.color = '#e74c3c'; corr.style.fontWeight = 'bold'; corr.style.marginLeft = '5px'; corr.innerText = '(' + (q{idx}Display[b_idx] || '') + ')'; inp.parentNode.insertBefore(corr, inp.nextSibling); }} }}); if (q{idx}AllCorrect) {{ score++; q{idx}Icon.className = 'status-icon text-correct'; q{idx}Icon.innerHTML = '✅ Đúng hoàn toàn'; }} else {{ q{idx}Icon.className = 'status-icon text-incorrect'; q{idx}Icon.innerHTML = '❌ Có ô điền sai'; }} }} container.querySelector('#exp-q{idx}_{sys_id}').style.display = 'block';")

        elif q_type == "Game: Sắp Xếp Từ":
            wb = q.get('g_scramble_wb', [])
            json_wb = json.dumps(wb, ensure_ascii=False)
            input_html = f"""
            <div class="game-section" style="margin-top:10px; max-width: 500px; margin-left:auto; margin-right:auto; text-align: center; padding: 20px; border: 2px dashed #ccc; border-radius: 10px; background-color: #fafafa;">
              <div style="font-size: 15px; display: flex; justify-content: space-between; padding: 0 10px;">
                <span>Điểm: <strong id="scramble-score-{sys_id}-{idx}" style="color: red;">0</strong></span>
                <span>Câu: <strong id="scramble-count-{sys_id}-{idx}">1</strong></span>
              </div>
              <div id="scramble-play-{sys_id}-{idx}">
                <div id="scramble-text-{sys_id}-{idx}" style="font-size: 28px; font-weight: bold; letter-spacing: 6px; margin: 20px 0; color:#2c3e50;">---</div>
                <div id="scramble-hint-{sys_id}-{idx}" style="font-style: italic; color: #666; margin-bottom: 20px;">Gợi ý: ...</div>
                <input type="text" id="scramble-guess-{sys_id}-{idx}" class="game-enter-trigger" style="padding: 10px; width: 80%; text-transform: uppercase; border: 1px solid #ccc; border-radius: 5px; outline: none;" placeholder="Nhập đáp án (Bấm Enter)...">
                <br><br><button onclick="checkScramble_{sys_id}_{idx}()" style="padding: 10px 25px; background-color: #3498db; color: white; border: none; border-radius: 5px; font-weight: bold; cursor:pointer;">Trả lời</button>
                <p id="scramble-msg-{sys_id}-{idx}" style="margin-top: 15px; font-weight: bold; min-height: 24px;"></p>
              </div>
              <div id="scramble-result-{sys_id}-{idx}" style="display: none;">
                <h3 style="color: #27ae60;">🎉 Hoàn thành!</h3>
                <button onclick="startScramble_{sys_id}_{idx}()" style="padding: 10px 20px; background-color: #e67e22; color: white; border: none; border-radius: 5px; cursor:pointer;">🔄 Chơi lại</button>
              </div>
            </div>
            <script>
              const wb_{sys_id}_{idx} = {json_wb}; let up_{sys_id}_{idx}=[], curr_{sys_id}_{idx}=null, s_{sys_id}_{idx}=0, q_{sys_id}_{idx}=1;
              
              document.getElementById("scramble-guess-{sys_id}-{idx}").addEventListener("keydown", function(e) {{
                  if (e.key === "Enter") {{ e.preventDefault(); e.stopPropagation(); checkScramble_{sys_id}_{idx}(); }}
              }});

              function shuf_{sys_id}_{idx}(w) {{ let a=w.split(''); for(let i=a.length-1;i>0;i--) {{let j=Math.floor(Math.random()*(i+1)); [a[i],a[j]]=[a[j],a[i]];}} return a.join(''); }}
              function startScramble_{sys_id}_{idx}() {{ up_{sys_id}_{idx}=[...wb_{sys_id}_{idx}]; s_{sys_id}_{idx}=0; q_{sys_id}_{idx}=1; document.getElementById("scramble-score-{sys_id}-{idx}").innerText=s_{sys_id}_{idx}; document.getElementById("scramble-play-{sys_id}-{idx}").style.display="block"; document.getElementById("scramble-result-{sys_id}-{idx}").style.display="none"; nextScramble_{sys_id}_{idx}(); }}
              
              function nextScramble_{sys_id}_{idx}() {{
                if(up_{sys_id}_{idx}.length===0){{ return; }}
                document.getElementById("scramble-count-{sys_id}-{idx}").innerText=q_{sys_id}_{idx}+"/"+wb_{sys_id}_{idx}.length;
                let r=Math.floor(Math.random()*up_{sys_id}_{idx}.length); curr_{sys_id}_{idx}=up_{sys_id}_{idx}[r]; up_{sys_id}_{idx}.splice(r,1);
                document.getElementById("scramble-text-{sys_id}-{idx}").innerText=shuf_{sys_id}_{idx}(curr_{sys_id}_{idx}.word);
                document.getElementById("scramble-hint-{sys_id}-{idx}").innerText="Gợi ý: "+curr_{sys_id}_{idx}.hint;
                let inp = document.getElementById("scramble-guess-{sys_id}-{idx}"); inp.value=""; inp.disabled=false; inp.focus(); document.getElementById("scramble-msg-{sys_id}-{idx}").innerText="";
              }}

              function checkScramble_{sys_id}_{idx}() {{
                let inp = document.getElementById("scramble-guess-{sys_id}-{idx}");
                let v = inp.value.toUpperCase().trim(); let m = document.getElementById("scramble-msg-{sys_id}-{idx}");
                if(!v) return;
                inp.disabled = true;
                if(v === curr_{sys_id}_{idx}.word){{ s_{sys_id}_{idx}+=10; document.getElementById("scramble-score-{sys_id}-{idx}").innerText=s_{sys_id}_{idx}; m.innerText="Chính xác! +10đ"; m.style.color="green"; }}
                else {{ m.innerText="Sai! Đáp án: "+curr_{sys_id}_{idx}.word; m.style.color="red"; }}
                q_{sys_id}_{idx}++; 
                setTimeout(() => {{
                    if (up_{sys_id}_{idx}.length === 0) {{
                        document.getElementById("scramble-play-{sys_id}-{idx}").style.display="none"; document.getElementById("scramble-result-{sys_id}-{idx}").style.display="block";
                        let nTop = document.getElementById('quiz-next-btn-top-{sys_id}');
                        if (nTop && nTop.style.display !== 'none') {{ window['moveQuizSlide_{sys_id}'](1); }}
                    }} else {{ nextScramble_{sys_id}_{idx}(); }}
                }}, 1500);
              }}
              setTimeout(startScramble_{sys_id}_{idx}, 500);
            </script>"""

        elif q_type == "Game: Tìm Từ Vựng":
            words_list = q.get('g_ws_words', [])
            grid_size = q.get('g_ws_grid', 15)
            json_words = json.dumps(words_list, ensure_ascii=False)
            input_html = f"""
            <div class="game-section" style="margin-top:10px; background-color: #fdfdfd; border-radius: 12px; box-shadow: rgba(0,0,0,0.08) 0px 4px 15px; max-width: 600px; margin-left:auto; margin-right:auto; padding: 20px; text-align: center;">
              <h3 style="color: #d35400; margin-top:0;">Tìm Từ Vựng ({len(words_list)} Từ)</h3>
              <div id="ws-list-{sys_id}-{idx}" style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-bottom: 15px;"></div>
              <div id="ws-grid-{sys_id}-{idx}" style="background-color: #7f8c8d; border-radius: 5px; display: grid; gap: 2px; padding: 2px; user-select: none;"></div>
              <button onclick="initWS_{sys_id}_{idx}()" style="margin-top:15px; background-color: #34495e; border-radius: 5px; border: none; color: white; cursor: pointer; font-weight: bold; padding: 8px 15px;">🔄 Trộn bảng</button>
            </div>
            <script>
              const wsW_{sys_id}_{idx}={json_words}; const wsG_{sys_id}_{idx}={grid_size}; let wGrid_{sys_id}_{idx}=[], wsSel_{sys_id}_{idx}=[], wsIsSel_{sys_id}_{idx}=false, wsFnd_{sys_id}_{idx}=0;
              function initWS_{sys_id}_{idx}(){{
                wGrid_{sys_id}_{idx}=Array(wsG_{sys_id}_{idx}).fill(null).map(()=>Array(wsG_{sys_id}_{idx}).fill('')); wsFnd_{sys_id}_{idx} = 0;
                wsW_{sys_id}_{idx}.forEach(w=>{{ let p=false, a=0; while(!p && a<500){{ let d=Math.random()<0.5?'H':'V', r=Math.floor(Math.random()*wsG_{sys_id}_{idx}), c=Math.floor(Math.random()*wsG_{sys_id}_{idx}); if(d==='H'&&c+w.length<=wsG_{sys_id}_{idx}){{ let ok=true; for(let i=0;i<w.length;i++) if(wGrid_{sys_id}_{idx}[r][c+i]!==''&&wGrid_{sys_id}_{idx}[r][c+i]!==w[i])ok=false; if(ok){{for(let i=0;i<w.length;i++)wGrid_{sys_id}_{idx}[r][c+i]=w[i]; p=true;}} }} else if(d==='V'&&r+w.length<=wsG_{sys_id}_{idx}){{ let ok=true; for(let i=0;i<w.length;i++) if(wGrid_{sys_id}_{idx}[r+i][c]!==''&&wGrid_{sys_id}_{idx}[r+i][c]!==w[i])ok=false; if(ok){{for(let i=0;i<w.length;i++)wGrid_{sys_id}_{idx}[r+i][c]=w[i]; p=true;}} }} a++; }} }});
                const ab="ABCDEFGHIJKLMNOPQRSTUVWXYZ"; for(let r=0;r<wsG_{sys_id}_{idx};r++)for(let c=0;c<wsG_{sys_id}_{idx};c++)if(wGrid_{sys_id}_{idx}[r][c]==='')wGrid_{sys_id}_{idx}[r][c]=ab[Math.floor(Math.random()*ab.length)];
                const cont=document.getElementById('ws-grid-{sys_id}-{idx}'), list=document.getElementById('ws-list-{sys_id}-{idx}'); cont.innerHTML=''; list.innerHTML=''; cont.style.gridTemplateColumns=`repeat(${{wsG_{sys_id}_{idx}}}, 1fr)`;
                wsW_{sys_id}_{idx}.forEach(w=>{{ let s=document.createElement('span'); s.className='ws-item'; s.id='wsi-{sys_id}-{idx}-'+w; s.innerText=w; list.appendChild(s); }});
                for(let r=0;r<wsG_{sys_id}_{idx};r++)for(let c=0;c<wsG_{sys_id}_{idx};c++){{ let d=document.createElement('div'); d.className='ws-cell'; d.innerText=wGrid_{sys_id}_{idx}[r][c]; d.onmousedown=()=>{{wsIsSel_{sys_id}_{idx}=true;wsSel_{sys_id}_{idx}=[d];d.classList.add('sel');}}; d.onmouseenter=()=>{{if(wsIsSel_{sys_id}_{idx}&&!wsSel_{sys_id}_{idx}.includes(d)){{wsSel_{sys_id}_{idx}.push(d);d.classList.add('sel');}}}}; cont.appendChild(d); }}
              }}
              window.addEventListener('mouseup',()=>{{ 
                  if(!wsIsSel_{sys_id}_{idx}) return; 
                  wsIsSel_{sys_id}_{idx}=false; 
                  let s=wsSel_{sys_id}_{idx}.map(c=>c.innerText).join(''), rev=s.split('').reverse().join(''); 
                  if(wsW_{sys_id}_{idx}.includes(s)||wsW_{sys_id}_{idx}.includes(rev)){{ 
                      let m=wsW_{sys_id}_{idx}.includes(s)?s:rev; let el=document.getElementById('wsi-{sys_id}-{idx}-'+m); 
                      if(!el.classList.contains('fnd')){{
                          el.classList.add('fnd'); wsFnd_{sys_id}_{idx}++;
                          wsSel_{sys_id}_{idx}.forEach(c=>{{c.classList.remove('sel');c.classList.add('fnd');}});
                          if(wsFnd_{sys_id}_{idx} === wsW_{sys_id}_{idx}.length) {{ setTimeout(() => {{ alert("🎉 Bạn đã tìm thấy tất cả các từ!"); let nTop = document.getElementById('quiz-next-btn-top-{sys_id}'); if (nTop && nTop.style.display !== 'none') window['moveQuizSlide_{sys_id}'](1); }}, 1500); }}
                      }}else wsSel_{sys_id}_{idx}.forEach(c=>c.classList.remove('sel')); 
                  }}else wsSel_{sys_id}_{idx}.forEach(c=>{{if(!c.classList.contains('fnd'))c.classList.remove('sel');}}); wsSel_{sys_id}_{idx}=[]; 
              }});
              setTimeout(initWS_{sys_id}_{idx}, 500);
            </script>"""

        elif q_type == "Game: Ô Chữ":
            timer_val = q.get('cross_timer', '0')
            json_data = json.dumps(q.get('cross_layout', []), ensure_ascii=False)
            timer_script = f"let totalSeconds_{sys_id}_{idx} = {timer_val};" if timer_val and timer_val.isdigit() else f"let totalSeconds_{sys_id}_{idx} = null;"

            input_html = f"""
            <div class="game-section" style="margin-top:10px; background:#EBEBEB; padding:15px; border-radius:8px;">
                <div class="cw-main-wrapper" id="cw-fullscreen-area-{sys_id}-{idx}" style="position:relative; width:100%; min-height:500px; display:flex; justify-content:center; align-items:center; overflow:auto;">
                    <div class="cw-board-container" id="cw-board-container-{sys_id}-{idx}" style="transition:transform 0.2s ease; padding:20px;"></div>
                    <div class="cw-controls-bottom" style="position:absolute; bottom:15px; left:15px;">
                        <div class="cw-timer-box" id="cw-timer-box-{sys_id}-{idx}" style="background:#fff; border:3px solid #82A944; padding:5px 12px; border-radius:20px; font-weight:900;"><span id="cw-timer-{sys_id}-{idx}">00:00</span></div>
                    </div>
                </div>
                <div class="cw-clues-container" style="display:flex; flex-wrap:wrap; gap:20px; margin-top:20px;">
                    <div class="cw-clue-column" style="flex:1; min-width:200px;">
                        <h4 style="border-bottom:2px solid #BDE773; padding-bottom:5px;">Hàng Ngang</h4>
                        <ul id="cw-clues-across-{sys_id}-{idx}" style="list-style:none; padding:0;"></ul>
                    </div>
                    <div class="cw-clue-column" style="flex:1; min-width:200px;">
                        <h4 style="border-bottom:2px solid #BDE773; padding-bottom:5px;">Hàng Dọc</h4>
                        <ul id="cw-clues-down-{sys_id}-{idx}" style="list-style:none; padding:0;"></ul>
                    </div>
                </div>
            </div>
            <style>
                .cw-cell {{ width:35px; height:35px; margin:1px; position:relative; }}
                .cw-input {{ width:100%; height:100%; border:1px solid #000; border-radius:4px; font-size:16px; text-align:center; text-transform:uppercase; font-weight:bold; padding:0; outline:none; }}
                .cw-input:focus {{ background-color:#A0D84F !important; }}
                .cw-input.active-word {{ background-color:#BDE773 !important; }}
                .cw-input.cw-wrong {{ background-color:#ffcdd2 !important; color:#d32f2f !important; border-color:#d32f2f !important; }}
                .cw-number {{ position:absolute; top:2px; left:3px; font-size:10px; font-weight:bold; color:#333; z-index:2; pointer-events:none;}}
                .active-clue {{ color:#82A944; font-weight:bold; }}
                .cw-clue-column li {{ cursor:pointer; margin-bottom:8px; font-size:14px; line-height:1.4; }}
            </style>
            <script>
            (function(){{
                const crosswordData = {json_data};
                {timer_script}
                let gridMap = {{}}; let activeDir = 'across'; let currentWordId = null; let timerInt;
                let minX = 99, maxX = 0, minY = 99, maxY = 0;
                crosswordData.forEach(item => {{
                    let cx = item.x, cy = item.y;
                    for (let i = 0; i < item.word.length; i++) {{
                        minX = Math.min(minX, cx); maxX = Math.max(maxX, cx);
                        minY = Math.min(minY, cy); maxY = Math.max(maxY, cy);
                        let key = cx + ',' + cy;
                        if (!gridMap[key]) gridMap[key] = {{ char: item.word[i], numbers: [], acrossId: null, downId: null }};
                        if (i === 0 && !gridMap[key].numbers.includes(item.id)) gridMap[key].numbers.push(item.id);
                        if (item.dir === 'across') gridMap[key].acrossId = item.id; else gridMap[key].downId = item.id;
                        item.dir === 'across' ? cx++ : cy++;
                    }}
                }});
                
                const board = document.getElementById('cw-board-container-{sys_id}-{idx}');
                let bHTML = '';
                for (let y = minY; y <= maxY; y++) {{
                    bHTML += '<div style="display:flex; justify-content:center;">';
                    for (let x = minX; x <= maxX; x++) {{
                        let key = x + ',' + y;
                        if (gridMap[key]) {{
                            let d = gridMap[key];
                            let nHTML = d.numbers.length > 0 ? `<span class="cw-number">${{d.numbers[0]}}</span>` : '';
                            bHTML += `<div class="cw-cell">${{nHTML}}<input type="text" class="cw-input" maxlength="1" data-x="${{x}}" data-y="${{y}}" data-across="${{d.acrossId || ''}}" data-down="${{d.downId || ''}}" onfocus="window.cwFocus_{sys_id}_{idx}(this)" oninput="window.cwInput_{sys_id}_{idx}(this, event)" onkeydown="window.cwKey_{sys_id}_{idx}(this, event)"></div>`;
                        }} else {{
                            bHTML += `<div class="cw-cell" style="background:transparent;"></div>`;
                        }}
                    }}
                    bHTML += '</div>';
                }}
                board.innerHTML = bHTML;
                
                const acList = document.getElementById('cw-clues-across-{sys_id}-{idx}');
                const dnList = document.getElementById('cw-clues-down-{sys_id}-{idx}');
                crosswordData.forEach(item => {{
                    let li = `<li id="clue-${{item.dir}}-${{item.id}}-{sys_id}-{idx}" onclick="window.cwFocusWord_{sys_id}_{idx}(${{item.id}}, '${{item.dir}}')"><strong>${{item.id}}.</strong> ${{item.clue}}</li>`;
                    if (item.dir === 'across') acList.innerHTML += li; else dnList.innerHTML += li;
                }});
                
                window.cwFocus_{sys_id}_{idx} = function(input) {{
                    let acId = input.getAttribute('data-across'), dnId = input.getAttribute('data-down');
                    if (acId && dnId) {{ activeDir = (currentWordId === acId) ? 'down' : 'across'; }}
                    else if (acId) activeDir = 'across'; else if (dnId) activeDir = 'down';
                    currentWordId = (activeDir === 'across') ? acId : dnId;
                    
                    document.getElementById('cw-fullscreen-area-{sys_id}-{idx}').querySelectorAll('.cw-input').forEach(e => e.classList.remove('active-word'));
                    document.getElementById('cw-clues-across-{sys_id}-{idx}').querySelectorAll('li').forEach(e => e.classList.remove('active-clue'));
                    document.getElementById('cw-clues-down-{sys_id}-{idx}').querySelectorAll('li').forEach(e => e.classList.remove('active-clue'));
                    
                    let query = activeDir === 'across' ? `[data-across="${{currentWordId}}"]` : `[data-down="${{currentWordId}}"]`;
                    document.getElementById('cw-board-container-{sys_id}-{idx}').querySelectorAll(query).forEach(e => e.classList.add('active-word'));
                    let clueEl = document.getElementById(`clue-${{activeDir}}-${{currentWordId}}-{sys_id}-{idx}`);
                    if(clueEl) clueEl.classList.add('active-clue');
                }};
                
                window.cwFocusWord_{sys_id}_{idx} = function(id, dir) {{
                    activeDir = dir;
                    let inputs = document.getElementById('cw-board-container-{sys_id}-{idx}').querySelectorAll(dir === 'across' ? `[data-across="${{id}}"]` : `[data-down="${{id}}"]`);
                    if(inputs.length > 0) inputs[0].focus();
                }};
                
                window.cwInput_{sys_id}_{idx} = function(input, e) {{
                    let x = input.getAttribute('data-x'), y = input.getAttribute('data-y');
                    let exp = gridMap[`${{x}},${{y}}`].char;
                    let val = input.value.toUpperCase(); 
                    input.value = val;
                    
                    let isCorrect = false;
                    if(val) {{ 
                        if(val !== exp) {{ input.classList.add('cw-wrong'); }} 
                        else {{ input.classList.remove('cw-wrong'); isCorrect = true; }}
                    }} else {{ input.classList.remove('cw-wrong'); }}
                    
                    // Chuyển ô thông minh: Chỉ nhảy khi ĐÚNG
                    if(val.length === 1 && isCorrect) {{ 
                        let n = window.cwGetNext_{sys_id}_{idx}(input, 1); 
                        if(n) {{ n.focus(); }} 
                        else {{ setTimeout(() => window.cwFocusNextClue_{sys_id}_{idx}(), 200); }}
                    }}
                    window.cwCheck_{sys_id}_{idx}();
                }};
                
                window.cwKey_{sys_id}_{idx} = function(input, e) {{
                    if(e.key === 'Backspace' && input.value === '') {{ let p = window.cwGetNext_{sys_id}_{idx}(input, -1); if(p) {{ p.focus(); p.value=''; p.classList.remove('cw-wrong'); }} }}
                    else if(['ArrowRight','ArrowDown'].includes(e.key)) {{ let n = window.cwGetNext_{sys_id}_{idx}(input, 1); if(n) n.focus(); }}
                    else if(['ArrowLeft','ArrowUp'].includes(e.key)) {{ let p = window.cwGetNext_{sys_id}_{idx}(input, -1); if(p) p.focus(); }}
                }};
                
                window.cwGetNext_{sys_id}_{idx} = function(curr, step) {{
                    let x = parseInt(curr.getAttribute('data-x')), y = parseInt(curr.getAttribute('data-y'));
                    let nx = activeDir === 'across' ? x+step : x; let ny = activeDir === 'down' ? y+step : y;
                    return document.getElementById('cw-board-container-{sys_id}-{idx}').querySelector(`input[data-x="${{nx}}"][data-y="${{ny}}"]`);
                }};
                
                window.cwFocusNextClue_{sys_id}_{idx} = function() {{
                    let allInputs = document.getElementById('cw-board-container-{sys_id}-{idx}').querySelectorAll('.cw-input');
                    let allCorrect = true;
                    for(let inp of allInputs) {{
                        let exp = gridMap[`${{inp.getAttribute('data-x')}},${{inp.getAttribute('data-y')}}`].char;
                        if(inp.value.toUpperCase() !== exp) {{ allCorrect = false; break; }}
                    }}
                    if(allCorrect) return; // Đã xong toàn bộ

                    let acClues = Array.from(document.getElementById('cw-clues-across-{sys_id}-{idx}').querySelectorAll('li'));
                    let dnClues = Array.from(document.getElementById('cw-clues-down-{sys_id}-{idx}').querySelectorAll('li'));
                    let allClues = acClues.concat(dnClues); // Ưu tiên ngang trước

                    for(let li of allClues) {{
                        let parts = li.id.split('-');
                        let dir = parts[1]; 
                        let wid = parts[2]; 
                        let inputs = document.getElementById('cw-board-container-{sys_id}-{idx}').querySelectorAll(`[data-${{dir}}="${{wid}}"]`);
                        
                        let isWordDone = true;
                        let firstEmpty = null;
                        for(let inp of inputs) {{
                            let exp = gridMap[`${{inp.getAttribute('data-x')}},${{inp.getAttribute('data-y')}}`].char;
                            if(inp.value.toUpperCase() !== exp) {{
                                isWordDone = false;
                                if(!firstEmpty) firstEmpty = inp;
                            }}
                        }}
                        if(!isWordDone && firstEmpty) {{
                            window.cwFocusWord_{sys_id}_{idx}(wid, dir);
                            firstEmpty.focus();
                            return;
                        }}
                    }}
                }};

                window.cwCheck_{sys_id}_{idx} = function() {{
                    let isWin = true; let inputs = document.getElementById('cw-board-container-{sys_id}-{idx}').querySelectorAll('.cw-input');
                    for(let i=0; i<inputs.length; i++) {{
                        let inp = inputs[i]; let exp = gridMap[`${{inp.getAttribute('data-x')}},${{inp.getAttribute('data-y')}}`].char;
                        if(inp.value.toUpperCase() !== exp) {{ isWin = false; break; }}
                    }}
                    // Win -> Auto Advance
                    if(isWin && inputs.length > 0) {{ 
                        if(timerInt) clearInterval(timerInt); 
                        setTimeout(()=>{{ 
                            alert("🎉 Hoàn thành ô chữ chính xác!"); 
                            inputs.forEach(i=>i.disabled=true); 
                            let nTop = document.getElementById('quiz-next-btn-top-{sys_id}');
                            if (nTop && nTop.style.display !== 'none') window['moveQuizSlide_{sys_id}'](1);
                        }}, 1500); 
                    }}
                }};
                
                if(totalSeconds_{sys_id}_{idx} !== null) {{
                    function upTimer() {{
                        let m = Math.floor(totalSeconds_{sys_id}_{idx}/60).toString().padStart(2,'0');
                        let s = (totalSeconds_{sys_id}_{idx}%60).toString().padStart(2,'0');
                        document.getElementById('cw-timer-{sys_id}-{idx}').innerText = m+':'+s;
                    }}
                    upTimer();
                    timerInt = setInterval(()=>{{
                        if(totalSeconds_{sys_id}_{idx} <= 0) {{ clearInterval(timerInt); alert("Hết giờ!"); document.getElementById('cw-board-container-{sys_id}-{idx}').querySelectorAll('.cw-input').forEach(i=>i.disabled=true); return; }}
                        totalSeconds_{sys_id}_{idx}--; upTimer();
                    }}, 1000);
                }} else {{ document.getElementById('cw-timer-box-{sys_id}-{idx}').style.display='none'; }}
            }})();
            </script>
            """

        elif q_type == "Game: Bức Tranh Bí Ẩn":
            bg_url = optimize_url(q.get('hidden_bg', ''))
            imgs = q.get('hidden_imgs', [])
            num_tiles = len(imgs)
            if num_tiles <= 6: cols, rows = 3, 2
            elif num_tiles <= 8: cols, rows = 4, 2
            elif num_tiles <= 9: cols, rows = 3, 3
            elif num_tiles <= 12: cols, rows = 4, 3
            elif num_tiles <= 15: cols, rows = 5, 3
            elif num_tiles <= 16: cols, rows = 4, 4
            else: cols, rows = 5, 4

            tiles_html = ""
            for j, img in enumerate(imgs):
                img_url = get_direct_img_link(img, "w400")
                tiles_html += f"""
                <div class="hp-tile-{sys_id}-{idx}" style="background:transparent; perspective:1000px; cursor:pointer; transition:opacity 0.5s ease;">
                    <div class="hp-inner-{sys_id}-{idx}" style="position:relative; width:100%; height:100%; text-align:center; transition:transform 0.6s; transform-style:preserve-3d;">
                        <div class="hp-front" style="position:absolute; width:100%; height:100%; backface-visibility:hidden; display:flex; justify-content:center; align-items:center; background:#2196F3; color:white; font-size:2rem; font-weight:bold; border-radius:4px; box-shadow:0 4px 8px rgba(0,0,0,0.2);">{j+1}</div>
                        <div class="hp-back" style="position:absolute; width:100%; height:100%; backface-visibility:hidden; display:flex; flex-direction:column; justify-content:center; align-items:center; background:#fff; transform:rotateY(180deg); padding:5px; border-radius:4px; box-sizing:border-box;">
                            <img src="{img_url}" style="max-width:100%; max-height:70%; object-fit:contain; margin-bottom:5px;">
                            <div style="display:flex; gap:5px;">
                                <button class="hp-correct-{sys_id}-{idx}" style="padding:4px 6px; background:#4CAF50; color:white; border:none; border-radius:3px; font-size:11px; cursor:pointer;">✔ Đúng</button>
                                <button class="hp-wrong-{sys_id}-{idx}" style="padding:4px 6px; background:#f44336; color:white; border:none; border-radius:3px; font-size:11px; cursor:pointer;">✘ Đóng</button>
                            </div>
                        </div>
                    </div>
                </div>"""

            bg_url_final = get_direct_img_link(bg_url, "w1000")
            input_html = f"""
            <div class="game-section hp-game-{sys_id}-{idx}" id="hp-wrapper-{sys_id}-{idx}" style="margin-top:10px; max-width:800px; margin:0 auto;">
                <div style="display:grid; grid-template-columns:repeat({cols},1fr); grid-template-rows:repeat({rows},1fr); gap:4px; aspect-ratio:4/3; background-image:url('{bg_url_final}'); background-size:100% 100%; background-position:center; border:5px solid #333; border-radius:8px; overflow:hidden;">
                    {tiles_html}
                </div>
            </div>
            <style>
                .hp-tile-{sys_id}-{idx}.flipped .hp-inner-{sys_id}-{idx} {{ transform: rotateY(180deg); }}
            </style>
            <script>
            (function(){{
                const wrapper = document.getElementById('hp-wrapper-{sys_id}-{idx}');
                wrapper.querySelectorAll('.hp-front').forEach(f => {{ f.addEventListener('click', function() {{ this.closest('.hp-tile-{sys_id}-{idx}').classList.add('flipped'); }}); }});
                wrapper.querySelectorAll('.hp-correct-{sys_id}-{idx}').forEach(b => {{ b.addEventListener('click', function(e) {{ e.stopPropagation(); let t = this.closest('.hp-tile-{sys_id}-{idx}'); t.style.opacity='0'; t.style.pointerEvents='none'; }}); }});
                wrapper.querySelectorAll('.hp-wrong-{sys_id}-{idx}').forEach(b => {{ b.addEventListener('click', function(e) {{ e.stopPropagation(); this.closest('.hp-tile-{sys_id}-{idx}').classList.remove('flipped'); }}); }});
            }})();
            </script>
            """

        elif q_type == "Game: Lật Thẻ Nhớ":
            timer_val = q.get('memory_timer', '60')
            pairs = q.get('memory_pairs', [])
            vocab_list = []
            for j, p in enumerate(pairs):
                img_url = get_direct_img_link(p["image"], "w400")
                vocab_list.append(f'{{ id: {j+1}, word: "{p["word"]}", image: "{img_url}" }}')
            vocab_string = ",\n".join(vocab_list)

            input_html = f"""
            <div class="game-section" style="margin-top:10px; text-align:center; max-width:600px; margin:0 auto; background:#f8f9fa; padding:20px; border-radius:10px; box-shadow:0 4px 8px rgba(0,0,0,0.1);">
                <div style="display:flex; justify-content:center; align-items:center; margin-bottom:15px;">
                    <div id="mem-timer-{sys_id}-{idx}" style="font-size:20px; font-weight:bold; color:#e74c3c; background:#fadbd8; padding:5px 15px; border-radius:8px; border:2px solid #e74c3c;">Thời gian: {timer_val}s</div>
                </div>
                <div id="mem-board-{sys_id}-{idx}" style="display:grid; grid-template-columns:repeat(4,1fr); gap:10px;"></div>
                <button onclick="window.initMem_{sys_id}_{idx}()" style="margin-top:20px; padding:10px 20px; background:#3498db; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">Chơi Lại</button>
            </div>
            <style>
                .mem-card-{sys_id}-{idx} {{ aspect-ratio:1/1; background-color:#2c3e50; border-radius:8px; display:flex; align-items:center; justify-content:center; cursor:pointer; position:relative; transform-style:preserve-3d; transition:transform 0.4s ease; box-shadow:0 2px 4px rgba(0,0,0,0.2); }}
                .mem-card-{sys_id}-{idx}.flip, .mem-card-{sys_id}-{idx}.matched {{ transform:rotateY(180deg); cursor:default; }}
                .mem-card-{sys_id}-{idx}.matched .mem-front {{ border-color:#27ae60; background:#e8f8f5; }}
                .mem-front, .mem-back {{ position:absolute; width:100%; height:100%; backface-visibility:hidden; display:flex; align-items:center; justify-content:center; border-radius:8px; }}
                .mem-front {{ background:#fff; transform:rotateY(180deg); font-size:16px; font-weight:bold; color:#333; border:2px solid #bdc3c7; padding:5px; box-sizing:border-box; word-break:break-word; text-align:center; }}
                .mem-back {{ background-color:#3498db; background-image:repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,.1) 10px, rgba(255,255,255,.1) 20px); }}
            </style>
            <script>
            (function(){{
                const vocab = [{vocab_string}];
                let hasFlipped = false, lock = false, first, second, matches = 0;
                let timeLeft = {timer_val}, timerInt;
                const targetMatches = vocab.length;
                
                window.initMem_{sys_id}_{idx} = function() {{
                    const board = document.getElementById('mem-board-{sys_id}-{idx}');
                    board.innerHTML = ''; matches = 0;
                    [hasFlipped, lock, first, second] = [false, false, null, null];
                    clearInterval(timerInt); timeLeft = {timer_val};
                    document.getElementById('mem-timer-{sys_id}-{idx}').innerText = `Thời gian: ${{timeLeft}}s`;
                    
                    timerInt = setInterval(() => {{
                        timeLeft--; document.getElementById('mem-timer-{sys_id}-{idx}').innerText = `Thời gian: ${{timeLeft}}s`;
                        if(timeLeft <= 0) {{ clearInterval(timerInt); lock=true; setTimeout(()=>alert("Hết giờ!"), 300); }}
                    }}, 1000);
                    
                    let cards = [];
                    vocab.forEach(item => {{
                        cards.push({{id: item.id, type: 'img', c: item.image}});
                        cards.push({{id: item.id, type: 'txt', c: item.word}});
                    }});
                    cards.sort(() => 0.5 - Math.random());
                    
                    cards.forEach(item => {{
                        let div = document.createElement('div');
                        div.className = `mem-card-{sys_id}-{idx}`;
                        div.dataset.id = item.id; div.dataset.type = item.type; div.dataset.content = item.c;
                        let isLink = item.c.includes("http") || item.c.startsWith("data:image");
                        let front = item.type === 'img' ? (isLink ? `<img src="${{item.c}}" style="max-width:90%; max-height:90%; object-fit:contain; border-radius:5px;">` : item.c) : item.c;
                        div.innerHTML = `<div class="mem-front">${{front}}</div><div class="mem-back"></div>`;
                        div.addEventListener('click', flipCard);
                        board.appendChild(div);
                    }});
                }};
                
                function flipCard() {{
                    if(lock || this === first) return;
                    this.classList.add('flip');
                    if(this.dataset.type === 'txt') {{
                        let b64 = btoa(unescape(encodeURIComponent(this.dataset.content)));
                        window['speakTTSBase64_{sys_id}'](b64);
                    }}
                    if(!hasFlipped) {{ hasFlipped = true; first = this; return; }}
                    second = this;
                    let isMatch = first.dataset.id === second.dataset.id && first.dataset.type !== second.dataset.type;
                    isMatch ? disableCards() : unflipCards();
                }}
                
                function disableCards() {{
                    first.removeEventListener('click', flipCard); second.removeEventListener('click', flipCard);
                    first.classList.add('matched'); second.classList.add('matched');
                    matches++;
                    if(matches === targetMatches) {{ 
                        clearInterval(timerInt); 
                        setTimeout(()=>{{
                            alert(`Hoàn thành! Bạn dư ${{timeLeft}}s`);
                            let nTop = document.getElementById('quiz-next-btn-top-{sys_id}');
                            if (nTop && nTop.style.display !== 'none') window['moveQuizSlide_{sys_id}'](1);
                        }}, 1500); 
                    }}
                    [hasFlipped, lock, first, second] = [false, false, null, null];
                }}
                
                function unflipCards() {{
                    lock = true;
                    setTimeout(() => {{
                        first.classList.remove('flip'); second.classList.remove('flip');
                        [hasFlipped, lock, first, second] = [false, false, null, null];
                    }}, 1000);
                }}
                
                setTimeout(window.initMem_{sys_id}_{idx}, 500);
            }})();
            </script>
            """

        # Xử lý Ẩn Text Câu hỏi nếu dùng TTS và Cấp số thứ tự câu
        header_content = ""
        # Điều kiện MỚI: Bỏ qua Điền từ V3 để không in q_text_html lên header
        if q_text_html and q_type not in ["Điền từ (V3)", "Nối câu", "Game: Sắp Xếp Từ", "Game: Tìm Từ Vựng", "Game: Ô Chữ", "Game: Bức Tranh Bí Ẩn", "Game: Lật Thẻ Nhớ"]:
            if q.get('q_tts', False):
                tts_text = strip_html(q.get('q_raw', ''))
                b64_tts = base64.b64encode(tts_text.encode('utf-8')).decode('utf-8')
                header_content = f'<div class="card-header hover-yellow">Câu {idx}: <button type="button" class="audio-icon-btn" onclick="speakTTSBase64_{sys_id}(\'{b64_tts}\')" title="Nghe câu hỏi">🔊</button></div>'
            else:
                header_content = f'<div class="card-header hover-yellow">Câu {idx}:<br>{q_text_html}</div>'
        else:
            header_content = f'<div class="card-header hover-yellow">Câu {idx}</div>'

        display_style = 'display: block;' if i == 0 else 'display: none;'
        quiz_html_parts.append(f'<div class="quiz-card quiz-master-slide" id="card-q{idx}_{sys_id}" style="{display_style}"><div class="sticky-header">{topic_html}{header_content}</div><div class="quiz-body-scrollable">{img_html}{input_html}<div class="explanation-box" id="exp-q{idx}_{sys_id}">💡 <b>Kết quả / Giải thích:</b><br>{explanation}</div></div></div>')

    quiz_html = "".join(quiz_html_parts)
    js_grading = "\n".join(js_grading_parts)
    js_init = "".join(js_init_parts)

    quiz_nav_style = "display: inline-flex; align-items: center; background: #f8f9fa; padding: 4px 10px; border-radius: 6px; border: 1px solid #dadce0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"
    display_next = "inline-block" if len(valid_quizzes) > 1 else "none"
    display_submit = "inline-block" if len(valid_quizzes) == 1 else "none"
    
    global_timer_html = ""
    if global_timer_secs > 0:
        global_timer_html = f'<div id="quiz-global-timer-box-{sys_id}" style="margin-left:10px; background:#ffebee; color:#c62828; padding:4px 10px; border-radius:6px; font-weight:bold; border:1px solid #ef9a9a; display:inline-flex; align-items:center;">⏳ <span id="quiz-global-timer-{sys_id}" style="margin-left:5px;">00:00</span></div>'

    quiz_nav_top = f'<div style="{quiz_nav_style}"><button type="button" class="nav-control-btn" onclick="moveQuizSlide_{sys_id}(-1)" id="quiz-prev-btn-top-{sys_id}" disabled>&#10094; Câu trước</button><span class="fc-counter" id="quiz-counter-top-{sys_id}">Câu 1 / {len(valid_quizzes)}</span><button type="button" class="nav-control-btn" onclick="moveQuizSlide_{sys_id}(1)" id="quiz-next-btn-top-{sys_id}" style="display: {display_next};">Câu tiếp &#10095;</button><button type="button" class="submit-all-btn" id="quiz-submit-btn-top-{sys_id}" onclick="submitQuiz_{sys_id}()" style="display: {display_submit}; margin-left: 5px;">NỘP BÀI</button>{global_timer_html}</div>' if valid_quizzes else ""

    has_lecture = len(lec_html_parts) > 0
    has_quiz = len(valid_quizzes) > 0

    tab_buttons = []
    if has_lecture: tab_buttons.append(f'<button class="tab-btn active" onclick="openTab_{sys_id}(event, \'tab-lecture\')">📚 Thư mục bài giảng</button>')
    if has_quiz: tab_buttons.append(f'<button class="tab-btn {"active" if not has_lecture else ""}" onclick="openTab_{sys_id}(event, \'tab-quiz\')">📝 Bài tập</button>')
    
    tab_buttons_html = f'<div class="tab-buttons" style="border-bottom: none; margin-bottom: 0;">{"".join(tab_buttons)}</div>' if len(tab_buttons) > 1 else ""

    header_wrapper_html = ""
    if len(tab_buttons) > 1:
        header_wrapper_html = f"""<div class="system-header-wrapper" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #dadce0; margin-bottom: 25px; flex-wrap: wrap; gap: 10px;">{tab_buttons_html}<div id="quiz-global-nav-{sys_id}" style="display: {'block' if has_quiz and not has_lecture else 'none'};">{quiz_nav_top}</div></div>"""
    else:
        header_wrapper_html = f"""<div class="system-header-wrapper" style="display: flex; justify-content: flex-end; align-items: center; border-bottom: 2px solid #dadce0; padding-bottom: 10px; margin-bottom: 25px;"><div id="quiz-global-nav-{sys_id}" style="display: block;">{quiz_nav_top}</div></div>""" if has_quiz else ""

    lecture_block_html = f'<div id="tab-lecture_{sys_id}" class="tab-content" style="display: {"block" if has_lecture else "none"};">{"".join(lec_html_parts)}</div>' if has_lecture else ""
    quiz_block_html = f'<div id="tab-quiz_{sys_id}" class="tab-content" style="display: {"block" if has_quiz and not has_lecture else "none"};"><div class="quiz-master-container"><div id="quiz-slider-container-{sys_id}" class="slider-content-wrapper">{quiz_html}</div></div><div class="score-board" id="final-score-board-{sys_id}" style="display: none; margin-top: 20px;">🏆 Điểm số tự động của bạn: <strong id="total-score-text-{sys_id}">0 / {max_score}</strong></div></div>' if has_quiz else ""

    cover_opt = get_direct_img_link(st.session_state.config.get('cover',''), "w1000")
    cover_html_block = f'<div style="display:none!important; opacity:0; width:0; height:0; overflow:hidden;"><img src="{cover_opt}" loading="lazy" alt="Cover Image"></div>\n' if cover_opt else ""

    final_code = f"""
<div class="system-container" id="bj-system-{sys_id}">
{cover_html_block}
<h2 class="system-title">E With Bich Jane<span><!--more--></span></h2>
{header_wrapper_html}
{lecture_block_html}
{quiz_block_html}
</div>

<style>
.system-container, .tab-content, .lecture-section, .slider-container-main, .quiz-master-container {{ overflow: visible !important; }}
.system-container {{ font-family: -apple-system, sans-serif; max-width: 720px; margin: 0 auto; padding: 20px 10px; }}
.system-title {{ display: none; }} 
.tab-buttons {{ display: flex; gap: 10px; margin-bottom: 25px; }}
.tab-btn {{ background: none; border: none; padding: 12px 20px; font-size: 16px; font-weight: 600; color: #5f6368; cursor: pointer; transition: 0.3s; border-bottom: 3px solid transparent; margin-bottom: -2px; }}
.tab-btn:hover {{ color: #1a73e8; background: #f8f9fa; border-radius: 8px 8px 0 0; }}
.tab-btn.active {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; }}
.tab-content {{ display: none; animation: fadeIn 0.4s; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.lecture-section {{ margin-bottom: 30px; }}
.section-title {{ font-size: 18px; color: #202124; border-left: 4px solid #34a853; padding-left: 10px; }}

.hover-yellow {{ transition: color 0.2s; }}
.hover-yellow:hover, .hover-yellow:hover * {{ color: #f1c40f !important; }}

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

.quiz-card {{ background: #ffffff; border: 1px solid #dadce0; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); box-sizing: border-box; animation: fadeIn 0.3s ease; width: 100%; }}
.quiz-topic-badge {{ display: inline-block; background: #e8f0fe; color: #1a73e8; padding: 6px 14px; border-radius: 20px; font-size: 13.5px; font-weight: bold; margin-bottom: 12px; border: 1px solid #d2e3fc; }}
.sticky-header {{ position: -webkit-sticky; position: sticky; top: 0px; background: #ffffff; z-index: 90; padding: 10px 0 5px 0; margin-top: -10px; border-bottom: 2px dashed #e4e3e1; margin-bottom: 10px; }}
.card-header {{ font-size: 16.5px; font-weight: 600; color: #202124; line-height: 1.5; display: flex; align-items: center; }}

.carousel-container {{ position: relative; width: 100%; background: transparent; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; outline: none; margin-bottom: 10px; }}
.quiz-img {{ max-height: 350px; width: 100%; height: auto; object-fit: contain; }} 
.nav-img-btn {{ position: absolute; top: 50%; transform: translateY(-50%); background: rgba(0, 0, 0, 0.4); color: white; border: none; padding: 12px 15px; cursor: pointer; font-size: 16px; border-radius: 50%; z-index: 2; }}
.nav-img-btn:hover {{ background: rgba(0, 0, 0, 0.8); }}
.prev-btn {{ left: 10px; }} .next-btn {{ right: 10px; }}
.slide-counter {{ position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); background: rgba(0, 0, 0, 0.6); color: white; padding: 4px 12px; border-radius: 20px; font-size: 11.5px; font-weight: bold; z-index: 2; }}

.card-options {{ display: flex; flex-direction: column; gap: 8px; }}
.opt-label {{ display: block; padding: 10px; border: 1px solid #dadce0; border-radius: 8px; cursor: pointer; font-size: 15px; transition: 0.15s; box-sizing: border-box; }}
.opt-label:hover {{ background: #f8f9fa; }}
.opt-label.correct {{ background: #e6f4ea; border-color: #137333; color: #137333; font-weight: bold; }}
.opt-label.incorrect {{ background: #fce8e6; border-color: #c5221f; color: #c5221f; }}

.essay-container {{ display: flex; flex-direction: column; gap: 8px; width: 100%; }}
.blank-input {{ border: none; border-bottom: 2px solid #95a5a6; background: #f1f3f4; border-radius: 4px 4px 0 0; text-align: center; font-weight: bold; color: #2980b9; outline: none; transition: all 0.3s ease; padding: 4px 8px; margin: 0 4px; box-sizing: border-box; box-shadow: inset 0 -1px 0 rgba(0,0,0,0.1); }}
.blank-input:focus {{ border-bottom: 2px solid #1a73e8; background-color: #e8f0fe; }}
.input-correct {{ border-bottom: 2px solid #27ae60 !important; background: #e6f4ea !important; color: #137333 !important; font-weight: bold; }}
.input-incorrect {{ border-bottom: 2px solid #e74c3c !important; background: #fce8e6 !important; color: #c5221f !important; }}

.match-item {{ padding: 8px; border: 1px solid #dadce0; border-radius: 6px; margin-bottom: 5px; background: #f8f9fa; display: flex; align-items: center; font-size: 15px; box-sizing: border-box; }}
.match-select {{ padding: 4px 8px; border-radius: 6px; border: 1px solid #dadce0; font-size: 14px; outline: none; cursor: pointer; }}

.status-icon {{ font-weight: bold; font-size: 15px; }}
.status-icon.text-correct {{ color: #137333; }}
.status-icon.text-incorrect {{ color: #c5221f; }}
.submit-all-btn {{ padding: 6px 12px; font-size: 14px; font-weight: bold; background: #34a853; color: white; border: none; border-radius: 6px; cursor: pointer; transition: 0.3s; margin: 0 2px; }}
.submit-all-btn:hover {{ background: #2d9248; box-shadow: 0 4px 10px rgba(52, 168, 83, 0.3); }}
.explanation-box {{ display: none; margin-top: 10px; padding: 15px; background: #e8f0fe; color: #1967d2; border-radius: 8px; font-size: 14.5px; border-left: 5px solid #1a73e8; line-height: 1.5; }}
.score-board {{ margin: 0 auto; padding: 15px 20px; background: #fff3e0; border: 1px solid #ffcc80; border-radius: 8px; color: #e65100; font-size: 18px; box-sizing: border-box; text-align: center; }}

/* Giao diện lưới cho Game Tìm từ */
.ws-cell {{ background:white; display:flex; align-items:center; justify-content:center; aspect-ratio:1/1; font-weight:bold; cursor:pointer; font-size: clamp(12px, 3.5vw, 18px); color: #2c3e50; transition: background-color 0.1s; }} 
.ws-cell.sel {{ background:#f39c12; color:white; }} 
.ws-cell.fnd {{ background:#e67e22; color:white; }} 
.ws-item {{ padding: 4px 10px; background: #ecf0f1; border-radius: 15px; font-size: 13px; font-weight: bold; color: #7f8c8d; transition: all 0.3s; }} 
.ws-item.fnd {{ text-decoration: line-through; background: #2ecc71; color: white; }}
</style>

<script>
(function() {{
    var sysId = '{sys_id}';
    var container = document.getElementById('bj-system-' + sysId);
    if (!container) return;

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
        window.currentSystemAudio.play().catch(function(e) {{ console.error("Lỗi audio:", e); alert("Không thể phát âm thanh!"); }});
    }};
    
    // Nâng cấp: Mã hóa Base64 cho TTS và chọn giọng Nữ chuẩn Tiếng Anh
    let voicesLoaded_{sys_id} = false;
    if ('speechSynthesis' in window) {{
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = function() {{ voicesLoaded_{sys_id} = true; }};
    }}
    
    function getBestEnglishFemaleVoice_{sys_id}() {{
        let voices = window.speechSynthesis.getVoices();
        let preferred = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Female') || v.name.includes('Zira') || v.name.includes('Samantha') || v.name.includes('Victoria') || v.name.includes('Google US English')));
        if (preferred) return preferred;
        let fallback = voices.find(v => v.lang === 'en-US' || v.lang === 'en-GB');
        return fallback || voices[0];
    }}

    window['speakTTSBase64_' + sysId] = function(b64text) {{
        try {{
            let text = decodeURIComponent(escape(atob(b64text)));
            window['speakTTS_' + sysId](text);
        }} catch(e) {{
            alert("⚠️ LỖI ÂM THANH:\\nTrình duyệt bạn đang xem bị giới hạn tính năng đọc tiếng Anh.\\n\\n👉 CÁCH SỬA: Hãy nhấn vào biểu tượng 3 DẤU CHẤM ở góc trên cùng bên phải màn hình, chọn 'Mở bằng trình duyệt' (hoặc Mở bằng Chrome / Safari) để nghe được nhé!");
        }}
    }};

    window['speakTTS_' + sysId] = function(textToSpeak) {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            
            // Xử lý chunking (Cắt theo dấu câu) để tạo quãng nghỉ và giảm tốc độ
            var lowerText = textToSpeak.toLowerCase();
            var chunks = lowerText.split(/([.,;:?!]+)/g);
            let voice = getBestEnglishFemaleVoice_{sys_id}();
            
            let speakChunk = function(i) {{
                if (i >= chunks.length) return;
                let chunkText = chunks[i].trim();
                
                if (!chunkText) {{
                    speakChunk(i + 1);
                    return;
                }}
                
                // Nếu chunk là dấu câu -> tạo quãng nghỉ setTimeout
                if (/^[.,;:?!]+$/.test(chunkText)) {{
                    let delay = (chunkText.includes('.') || chunkText.includes('?') || chunkText.includes('!')) ? 600 : 300;
                    setTimeout(function() {{ speakChunk(i + 1); }}, delay);
                    return;
                }}
                
                var msg = new SpeechSynthesisUtterance(chunkText);
                msg.lang = 'en-US';
                if(voice) msg.voice = voice;
                msg.rate = 0.75; // Giảm tốc độ đọc
                
                msg.onend = function() {{ speakChunk(i + 1); }};
                msg.onerror = function() {{ 
                    alert("⚠️ LỖI ÂM THANH:\\nTrình duyệt bạn đang xem bị giới hạn tính năng đọc tiếng Anh.\\n\\n👉 CÁCH SỬA: Hãy nhấn vào biểu tượng 3 DẤU CHẤM ở góc trên cùng bên phải màn hình, chọn 'Mở bằng trình duyệt' (hoặc Mở bằng Chrome / Safari) để nghe được nhé!");
                    speakChunk(i + 1); 
                }};
                window.speechSynthesis.speak(msg);
            }};
            
            speakChunk(0);
        }} else {{
            alert("⚠️ LỖI ÂM THANH:\\nTrình duyệt bạn đang xem bị giới hạn tính năng đọc tiếng Anh.\\n\\n👉 CÁCH SỬA: Hãy nhấn vào biểu tượng 3 DẤU CHẤM ở góc trên cùng bên phải màn hình, chọn 'Mở bằng trình duyệt' (hoặc Mở bằng Chrome / Safari) để nghe được nhé!");
        }}
    }};

    // Logic Countdown Timer Toàn Bài
    if ({global_timer_secs} > 0) {{
        let globalTime_{sys_id} = {global_timer_secs};
        let globalTimerInt_{sys_id};
        
        function updateGlobalTimer_{sys_id}() {{
            let timerEl = document.getElementById('quiz-global-timer-{sys_id}');
            if(!timerEl) return;
            let m = Math.floor(globalTime_{sys_id} / 60).toString().padStart(2, '0');
            let s = (globalTime_{sys_id} % 60).toString().padStart(2, '0');
            timerEl.innerText = m + ":" + s;
        }}
        
        function startGlobalTimer_{sys_id}() {{
            updateGlobalTimer_{sys_id}();
            globalTimerInt_{sys_id} = setInterval(() => {{
                globalTime_{sys_id}--;
                if(globalTime_{sys_id} <= 0) {{
                    clearInterval(globalTimerInt_{sys_id});
                    document.getElementById('quiz-global-timer-{sys_id}').innerText = "00:00";
                    alert("⏳ Đã hết thời gian làm bài!");
                    window['submitQuiz_' + sysId]();
                }} else {{
                    updateGlobalTimer_{sys_id}();
                }}
            }}, 1000);
        }}
        setTimeout(startGlobalTimer_{sys_id}, 500);
    }}

    // JS CHO BÀI GIẢNG 
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

    // JS CHO BÀI TẬP VÀ GAME
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
        if (event.key === 'Enter') {{
            if (activeElement && (activeElement.classList.contains('quiz-enter-trigger') || activeElement.classList.contains('game-enter-trigger'))) {{
                event.preventDefault();
                var currentSlide = activeElement.closest('.quiz-master-slide');
                if (currentSlide) {{
                    var allInputs = Array.from(currentSlide.querySelectorAll('.quiz-enter-trigger, .game-enter-trigger'));
                    var idx = allInputs.indexOf(activeElement);
                    if (idx > -1 && idx < allInputs.length - 1) {{
                        allInputs[idx + 1].focus();
                    }} else {{
                        var nTop = container.querySelector('#quiz-next-btn-top-' + sysId);
                        if (nTop && nTop.style.display !== 'none') {{
                            window['moveQuizSlide_' + sysId](1);
                            setTimeout(function() {{
                                var newSlide = container.querySelector('.quiz-master-slide[style*="display: block"]');
                                if (newSlide) {{
                                    var firstInput = newSlide.querySelector('.quiz-enter-trigger, .game-enter-trigger');
                                    if (firstInput) firstInput.focus();
                                }}
                            }}, 100);
                        }}
                    }}
                }}
            }}
        }}

        var isTyping = activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA' || activeElement.tagName === 'SELECT');
        if (!isTyping) {{
            if (event.key === 'ArrowLeft') {{
                var quizTab = container.querySelector('#tab-quiz_' + sysId);
                var lecTab = container.querySelector('#tab-lecture_' + sysId);
                if (quizTab && quizTab.style.display !== 'none') {{
                    var pTop = container.querySelector('#quiz-prev-btn-top-' + sysId);
                    if (pTop && !pTop.disabled) window['moveQuizSlide_' + sysId](-1);
                    event.preventDefault();
                }} else if (lecTab && lecTab.style.display !== 'none') {{
                    if (window['moveFcSlide_' + sysId]) window['moveFcSlide_' + sysId](-1);
                    if (window['moveGrSlide_' + sysId]) window['moveGrSlide_' + sysId](-1);
                    event.preventDefault();
                }}
            }} else if (event.key === 'ArrowRight') {{
                var quizTab = container.querySelector('#tab-quiz_' + sysId);
                var lecTab = container.querySelector('#tab-lecture_' + sysId);
                if (quizTab && quizTab.style.display !== 'none') {{
                    var nTop = container.querySelector('#quiz-next-btn-top-' + sysId);
                    if (nTop && nTop.style.display !== 'none') window['moveQuizSlide_' + sysId](1);
                    event.preventDefault();
                }} else if (lecTab && lecTab.style.display !== 'none') {{
                    if (window['moveFcSlide_' + sysId]) window['moveFcSlide_' + sysId](1);
                    if (window['moveGrSlide_' + sysId]) window['moveGrSlide_' + sysId](1);
                    event.preventDefault();
                }}
            }}
        }}
    }});
}})();
</script>
"""
    return final_code

# =========================================================================
# GIAO DIỆN STREAMLIT CHÍNH
# =========================================================================
def main():
    st.set_page_config(page_title="Super App - V3 Ultimate Quiz & Game", layout="wide")
    
    # 1. Khởi tạo State (Thay thế cho CoreManager)
    init_session()
    
    # 2. Sidebar Navigation
    st.sidebar.title("MENU CHÍNH")
    page = st.sidebar.radio("Điều hướng", ["⚙️ Cấu Hình Chung", "📚 Bài Giảng", "📝 Bài Tập & Trò Chơi"], 
                            index=["Config", "Lecture", "Quiz"].index(st.session_state.current_page) if st.session_state.current_page in ["Config", "Lecture", "Quiz"] else 0)
    
    # Map label to internal page name
    if page == "⚙️ Cấu Hình Chung": st.session_state.current_page = "Config"
    elif page == "📚 Bài Giảng": st.session_state.current_page = "Lecture"
    elif page == "📝 Bài Tập & Trò Chơi": st.session_state.current_page = "Quiz"
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**ĐIỀU KHIỂN XUẤT MÃ**")
    
    if st.sidebar.button("🔄 LÀM MỚI TẤT CẢ", use_container_width=True, type="secondary"):
        st.session_state.lecture_data = []
        st.session_state.quiz_data = []
        save_data()
        st.rerun()
        
    if st.sidebar.button("🚀 XUẤT MÃ GỘP BÀI", use_container_width=True, type="primary"):
        code = generate_code_block()
        st.session_state.generated_code = code
        st.session_state.show_code = True
        st.rerun()

    # Xử lý hiển thị Code sau khi xuất
    if st.session_state.get('show_code', False) and 'generated_code' in st.session_state:
        st.success("Tạo mã thành công! Bạn có thể Copy ở khung dưới hoặc tải về.")
        st.download_button("💾 TẢI FILE CODE (.txt)", data=st.session_state.generated_code, file_name="blog_code.txt", mime="text/plain", use_container_width=True)
        with st.expander("MÃ CODE ĐÃ TẠO (Bấm Copy ở góc phải)", expanded=True):
            st.code(st.session_state.generated_code, language='html')
        if st.button("Đóng mã code"):
            st.session_state.show_code = False
            st.rerun()

    st.sidebar.markdown("---")
    
    # 3. Render Pages
    if st.session_state.current_page == "Config":
        st.header("⚙️ CẤU HÌNH BÀI VIẾT (Áp dụng chung)")
        cover = st.text_input("Ảnh Cover (Làm Thumbnail Blogspot):", value=st.session_state.config.get('cover',''), placeholder="Dán Link ảnh Cover trực tiếp vào đây...")
        timer = st.text_input("Thời gian làm toàn bộ Bài Tập (Phút):", value=st.session_state.config.get('timer',''), placeholder="Ví dụ: 15 (Để trống = Không giới hạn)")
        
        if cover != st.session_state.config.get('cover','') or timer != st.session_state.config.get('timer',''):
            st.session_state.config['cover'] = cover
            st.session_state.config['timer'] = timer
            save_data()

    elif st.session_state.current_page == "Lecture":
        st.header("📚 Quản lý Bài Giảng")
        
        # Nếu đang ở chế độ chỉnh sửa/thêm mới
        if st.session_state.edit_idx is not None and st.session_state.edit_idx >= -1:
            is_new = (st.session_state.edit_idx == -1)
            idx = st.session_state.edit_idx
            
            # Khởi tạo temp data nếu chưa có
            if 'temp_lec' not in st.session_state:
                if is_new:
                    st.session_state.temp_lec = {
                        "type": "🎬 Video Bài Học", "title": "", "link": "",
                        "fc_rows": [{"w": "", "m": "", "a_tts": False, "i": ""}],
                        "gr_rows": [{"t": "", "a_tts": False, "i": "", "d_html": "", "d_state": "", "d_raw": ""}]
                    }
                else:
                    import copy
                    st.session_state.temp_lec = copy.deepcopy(st.session_state.lecture_data[idx])
                    if not st.session_state.temp_lec.get("fc_rows"): st.session_state.temp_lec["fc_rows"] = [{"w": "", "m": "", "a_tts": False, "i": ""}]
                    if not st.session_state.temp_lec.get("gr_rows"): st.session_state.temp_lec["gr_rows"] = [{"t": "", "a_tts": False, "i": "", "d_html": "", "d_state": "", "d_raw": ""}]

            st.subheader(f"{'Thêm mới' if is_new else 'Sửa'} Bài Giảng")
            t_data = st.session_state.temp_lec
            
            t_data["type"] = st.selectbox("Loại nội dung:", ["🎬 Video Bài Học", "📇 Danh sách Flashcard", "📖 Ngữ Pháp", "🎧 Audio Độc Lập"], 
                                          index=["🎬 Video Bài Học", "📇 Danh sách Flashcard", "📖 Ngữ Pháp", "🎧 Audio Độc Lập"].index(t_data["type"]))
            t_data["title"] = st.text_input("Tiêu đề hiển thị:", value=t_data["title"])
            
            if t_data["type"] in ["🎬 Video Bài Học", "🎧 Audio Độc Lập"]:
                t_data["link"] = st.text_input("Dán Link Video G-Drive hoặc Link Audio (.mp3):", value=t_data["link"])
                
            elif t_data["type"] == "📇 Danh sách Flashcard":
                st.markdown("#### Từ vựng Flashcard")
                for r_idx, r in enumerate(t_data["fc_rows"]):
                    cols = st.columns([3, 3, 2, 3, 1])
                    r["w"] = cols[0].text_input(f"Từ vựng {r_idx+1}", value=r["w"], key=f"fc_w_{r_idx}")
                    r["m"] = cols[1].text_input(f"Nghĩa {r_idx+1}", value=r["m"], key=f"fc_m_{r_idx}")
                    r["a_tts"] = cols[2].checkbox("Đọc Audio (TTS)", value=r["a_tts"], key=f"fc_tts_{r_idx}")
                    r["i"] = cols[3].text_input(f"Link Ảnh {r_idx+1}", value=r["i"], key=f"fc_i_{r_idx}")
                    if cols[4].button("❌", key=f"fc_del_{r_idx}"):
                        t_data["fc_rows"].pop(r_idx)
                        st.rerun()
                if st.button("➕ Thêm Từ Vựng"):
                    t_data["fc_rows"].append({"w": "", "m": "", "a_tts": False, "i": ""})
                    st.rerun()
                    
            elif t_data["type"] == "📖 Ngữ Pháp":
                st.markdown("#### Cấu trúc Ngữ pháp")
                for r_idx, r in enumerate(t_data["gr_rows"]):
                    st.markdown(f"**Mục {r_idx+1}**")
                    cols = st.columns([4, 2, 4, 1])
                    r["t"] = cols[0].text_input("Tên cấu trúc", value=r["t"], key=f"gr_t_{r_idx}")
                    r["a_tts"] = cols[1].checkbox("Đọc Audio (TTS)", value=r["a_tts"], key=f"gr_tts_{r_idx}")
                    r["i"] = cols[2].text_input("Link Ảnh", value=r["i"], key=f"gr_i_{r_idx}")
                    if cols[3].button("❌", key=f"gr_del_{r_idx}"):
                        t_data["gr_rows"].pop(r_idx)
                        st.rerun()
                    
                    # HTML Editor Simplified via text_area
                    st.caption("Nhập nội dung HTML (hoặc text thường). Bạn có thể dùng <b>chữ đậm</b>, <i>chữ nghiêng</i>...")
                    r["d_raw"] = st.text_area("Nội dung", value=r.get("d_raw", ""), height=150, key=f"gr_d_{r_idx}")
                    r["d_html"] = r["d_raw"].replace('\n', '<br>')
                    
                if st.button("➕ Thêm Cấu Trúc"):
                    t_data["gr_rows"].append({"t": "", "a_tts": False, "i": "", "d_html": "", "d_state": "", "d_raw": ""})
                    st.rerun()

            col_btn1, col_btn2 = st.columns([1, 5])
            if col_btn1.button("✔ LƯU LẠI", type="primary"):
                if is_new: st.session_state.lecture_data.append(t_data)
                else: st.session_state.lecture_data[idx] = t_data
                save_data()
                del st.session_state.temp_lec
                navigate("Lecture", None)
            if col_btn2.button("❌ Hủy"):
                del st.session_state.temp_lec
                navigate("Lecture", None)
                
        else: # Hiển thị danh sách
            col1, col2 = st.columns([1, 1])
            if col1.button("➕ THÊM BÀI GIẢNG MỚI", type="primary"):
                navigate("Lecture", -1)
                
            if len(st.session_state.lecture_data) > 0:
                to_delete = []
                for i, data in enumerate(st.session_state.lecture_data):
                    title = data.get('title') or data.get('type')
                    with st.container():
                        c1, c2, c3, c4 = st.columns([1, 6, 1, 1])
                        if c1.checkbox("Chọn", key=f"lec_chk_{i}"): to_delete.append(i)
                        c2.markdown(f"**Mục {i+1}: {title[:70]}**")
                        if c3.button("✏️ Sửa", key=f"lec_edit_{i}"): navigate("Lecture", i)
                        if c4.button("📑 Nhân bản", key=f"lec_clone_{i}"):
                            st.session_state.lecture_data.insert(i + 1, data.copy())
                            save_data()
                            st.rerun()
                
                if to_delete:
                    if st.button("🗑 XÓA CÁC MỤC ĐÃ CHỌN", type="primary"):
                        for i in sorted(to_delete, reverse=True):
                            del st.session_state.lecture_data[i]
                        save_data()
                        st.rerun()
            else:
                st.info("Chưa có bài giảng nào. Hãy bấm 'Thêm Bài Giảng' để bắt đầu.")

    elif st.session_state.current_page == "Quiz":
        st.header("📝 Quản lý Bài Tập & Trò Chơi")
        
        if st.session_state.edit_idx is not None and st.session_state.edit_idx >= -1:
            is_new = (st.session_state.edit_idx == -1)
            idx = st.session_state.edit_idx
            
            if 'temp_quiz' not in st.session_state:
                if is_new:
                    st.session_state.temp_quiz = {
                        "topic": "", "q_type": "Trắc nghiệm", "q_raw": "", "q_html": "", "q_tts": False,
                        "mcq": {"a":"", "b":"", "c":"", "d":"", "correct":"A"},
                        "mcq_tts": {"A":False, "B":False, "C":False, "D":False},
                        "matches": [{"l":"", "r":"", "l_tts":False, "r_tts":False}],
                        "v3_raw_text": "", "v3_tts": False, "v3_image": "",
                        "g_scramble_raw": "", "g_ws_grid": 15, "g_ws_raw": "",
                        "cross_timer": "", "cross_rows": [{"w":"", "c":""}],
                        "hidden_bg": "", "hidden_imgs": [""],
                        "memory_timer": "60", "memory_pairs": [{"w":"", "img":""}],
                        "exp_raw": ""
                    }
                else:
                    import copy
                    st.session_state.temp_quiz = copy.deepcopy(st.session_state.quiz_data[idx])
                    # Ensure all keys exist for older saves
                    q = st.session_state.temp_quiz
                    if 'mcq_tts' not in q: q['mcq_tts'] = {"A":False, "B":False, "C":False, "D":False}
                    if 'matches' not in q or not q['matches']: q['matches'] = [{"l":"", "r":"", "l_tts":False, "r_tts":False}]
                    if 'cross_rows' not in q or not q['cross_rows']: q['cross_rows'] = [{"w":"", "c":""}]
                    if 'hidden_imgs' not in q or not q['hidden_imgs']: q['hidden_imgs'] = [""]
                    if 'memory_pairs' not in q or not q['memory_pairs']: q['memory_pairs'] = [{"w":"", "img":""}]

            t_data = st.session_state.temp_quiz
            
            t_data["q_type"] = st.selectbox("Loại câu hỏi / Trò chơi:", 
                                            ["Trắc nghiệm", "Điền từ (V3)", "Nối câu", "Game: Sắp Xếp Từ", "Game: Tìm Từ Vựng", "Game: Ô Chữ", "Game: Bức Tranh Bí Ẩn", "Game: Lật Thẻ Nhớ"],
                                            index=["Trắc nghiệm", "Điền từ (V3)", "Nối câu", "Game: Sắp Xếp Từ", "Game: Tìm Từ Vựng", "Game: Ô Chữ", "Game: Bức Tranh Bí Ẩn", "Game: Lật Thẻ Nhớ"].index(t_data.get("q_type", "Trắc nghiệm")))
            t_data["topic"] = st.text_input("Chủ đề chung (Tùy chọn):", value=t_data.get("topic", ""))

            # Layout 2 cột
            col_l, col_r = st.columns([1, 1])
            
            with col_l:
                if t_data["q_type"] not in ["Nối câu", "Điền từ (V3)", "Game: Sắp Xếp Từ", "Game: Tìm Từ Vựng", "Game: Ô Chữ", "Game: Bức Tranh Bí Ẩn", "Game: Lật Thẻ Nhớ"]:
                    st.markdown("**Câu hỏi:**")
                    t_data["q_tts"] = st.checkbox("Chuyển thành Audio (Ẩn text)", value=t_data.get("q_tts", False))
                    t_data["q_raw"] = st.text_area("Nội dung câu hỏi (Hỗ trợ HTML):", value=t_data.get("q_raw", ""), height=150)
                    t_data["q_html"] = t_data["q_raw"].replace('\n', '<br>')
            
            with col_r:
                if t_data["q_type"] == "Trắc nghiệm":
                    st.caption("* Hỗ trợ dán Link Ảnh (G-Drive) và Text cùng lúc")
                    mcq = t_data.get("mcq", {})
                    mcq_tts = t_data.get("mcq_tts", {})
                    
                    for opt in ['A', 'B', 'C', 'D']:
                        c1, c2 = st.columns([4, 1])
                        mcq[opt.lower()] = c1.text_input(f"Đáp án {opt}", value=mcq.get(opt.lower(), ""))
                        mcq_tts[opt] = c2.checkbox(f"Đọc Audio", value=mcq_tts.get(opt, False), key=f"mcq_tts_{opt}")
                    
                    t_data["mcq"] = mcq
                    t_data["mcq_tts"] = mcq_tts
                    t_data["mcq"]["correct"] = st.selectbox("Đáp án ĐÚNG:", ["A", "B", "C", "D"], index=["A", "B", "C", "D"].index(mcq.get("correct", "A")))
                    
                elif t_data["q_type"] == "Nối câu":
                    st.caption("* Cả 2 vế đều hỗ trợ Ảnh, Text, Checkbox 'Đọc'")
                    for r_idx, r in enumerate(t_data["matches"]):
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 3, 1, 1])
                        r["l"] = c1.text_input(f"Vế trái {r_idx+1}", value=r.get("l", ""), key=f"m_l_{r_idx}")
                        r["l_tts"] = c2.checkbox("Đọc", value=r.get("l_tts", False), key=f"m_l_tts_{r_idx}")
                        r["r"] = c3.text_input(f"Vế phải {r_idx+1}", value=r.get("r", ""), key=f"m_r_{r_idx}")
                        r["r_tts"] = c4.checkbox("Đọc", value=r.get("r_tts", False), key=f"m_r_tts_{r_idx}")
                        if c5.button("❌", key=f"m_del_{r_idx}"):
                            t_data["matches"].pop(r_idx)
                            st.rerun()
                    if st.button("➕ Thêm Cặp Nối"):
                        t_data["matches"].append({"l":"", "r":"", "l_tts":False, "r_tts":False})
                        st.rerun()
                        
                elif t_data["q_type"] == "Điền từ (V3)":
                    c1, c2 = st.columns(2)
                    t_data["v3_tts"] = c1.checkbox("Đọc Audio (Toàn bộ)", value=t_data.get("v3_tts", False))
                    t_data["v3_image"] = c2.text_input("Link Ảnh (G-Drive):", value=t_data.get("v3_image", ""))
                    st.caption("* Nhập nội dung, đặt từ cần điền trong ngoặc vuông kép. Ví dụ: The first month is [[January, Jan]]")
                    t_data["v3_raw_text"] = st.text_area("Nội dung:", value=t_data.get("v3_raw_text", ""), height=200)

                elif t_data["q_type"] == "Game: Sắp Xếp Từ":
                    st.caption("Cú pháp: TỪ_VỰNG | Gợi ý (Mỗi từ 1 dòng)")
                    t_data["g_scramble_raw"] = st.text_area("Dữ liệu:", value=t_data.get("g_scramble_raw", ""), height=200)
                    
                elif t_data["q_type"] == "Game: Tìm Từ Vựng":
                    t_data["g_ws_grid"] = st.number_input("Kích thước lưới:", value=int(t_data.get("g_ws_grid", 15)))
                    st.caption("Danh sách từ (Mỗi từ 1 dòng)")
                    t_data["g_ws_raw"] = st.text_area("Từ vựng:", value=t_data.get("g_ws_raw", ""), height=200)
                    
                elif t_data["q_type"] == "Game: Ô Chữ":
                    t_data["cross_timer"] = st.text_input("Thời gian (Giây, rỗng = ko tính):", value=t_data.get("cross_timer", ""))
                    for r_idx, r in enumerate(t_data["cross_rows"]):
                        c1, c2, c3 = st.columns([3, 5, 1])
                        r["w"] = c1.text_input(f"Từ (Ko dấu cách)", value=r.get("w", ""), key=f"cw_w_{r_idx}")
                        r["c"] = c2.text_input(f"Gợi ý {r_idx+1}", value=r.get("c", ""), key=f"cw_c_{r_idx}")
                        if c3.button("❌", key=f"cw_del_{r_idx}"):
                            t_data["cross_rows"].pop(r_idx)
                            st.rerun()
                    if st.button("➕ Thêm Từ Khóa"):
                        t_data["cross_rows"].append({"w":"", "c":""})
                        st.rerun()
                        
                elif t_data["q_type"] == "Game: Bức Tranh Bí Ẩn":
                    t_data["hidden_bg"] = st.text_input("Link Ảnh Nền (Bức tranh giấu):", value=t_data.get("hidden_bg", ""))
                    for r_idx, r in enumerate(t_data["hidden_imgs"]):
                        c1, c2 = st.columns([8, 1])
                        t_data["hidden_imgs"][r_idx] = c1.text_input(f"Ảnh ô cắt {r_idx+1}", value=r, key=f"hp_i_{r_idx}")
                        if c2.button("❌", key=f"hp_del_{r_idx}"):
                            t_data["hidden_imgs"].pop(r_idx)
                            st.rerun()
                    if st.button("➕ Thêm Ô Cắt"):
                        t_data["hidden_imgs"].append("")
                        st.rerun()
                        
                elif t_data["q_type"] == "Game: Lật Thẻ Nhớ":
                    t_data["memory_timer"] = st.text_input("Thời gian (Giây):", value=t_data.get("memory_timer", "60"))
                    for r_idx, r in enumerate(t_data["memory_pairs"]):
                        c1, c2, c3 = st.columns([4, 4, 1])
                        r["w"] = c1.text_input(f"Từ vựng {r_idx+1}", value=r.get("w", ""), key=f"mem_w_{r_idx}")
                        r["img"] = c2.text_input(f"Link Ảnh {r_idx+1}", value=r.get("img", ""), key=f"mem_i_{r_idx}")
                        if c3.button("❌", key=f"mem_del_{r_idx}"):
                            t_data["memory_pairs"].pop(r_idx)
                            st.rerun()
                    if st.button("➕ Thêm Cặp"):
                        t_data["memory_pairs"].append({"w":"", "img":""})
                        st.rerun()
                        
                st.markdown("---")
                st.markdown("**Giải thích / Đáp án mẫu:**")
                t_data["exp_raw"] = st.text_area("Nội dung giải thích (Hỗ trợ HTML):", value=t_data.get("exp_raw", ""))
                t_data["exp_html"] = t_data["exp_raw"].replace('\n', '<br>')
            
            # Action Buttons
            col_btn1, col_btn2 = st.columns([2, 5])
            if col_btn1.button("✔ LƯU BÀI TẬP", type="primary"):
                # Processing logic before saving
                if t_data["q_type"] == "Điền từ (V3)":
                    text = t_data.get("v3_raw_text", "")
                    blanks = re.findall(r'\[\[(.*?)\]\]', text)
                    correct_answers = []
                    for b in blanks:
                        correct_answers.append([v.strip() for v in b.split(',')])
                    
                    def repl(m):
                        idx = len(repl.counter)
                        repl.counter.append(1)
                        return f"[[BLANK_{idx}]]"
                    repl.counter = []
                    
                    q_html = re.sub(r'\[\[.*?\]\]', repl, text)
                    t_data["v3_html_content"] = q_html.replace('\n', '<br>\n')
                    t_data["v3_answers"] = correct_answers
                
                elif t_data["q_type"] == "Game: Sắp Xếp Từ":
                    raw = t_data.get("g_scramble_raw", "")
                    wb = [{"word": line.split('|', 1)[0].strip().upper(), "hint": line.split('|', 1)[1].strip()} for line in raw.split('\n') if '|' in line]
                    t_data["g_scramble_wb"] = wb
                
                elif t_data["q_type"] == "Game: Tìm Từ Vựng":
                    raw = t_data.get("g_ws_raw", "")
                    t_data["g_ws_words"] = [w.strip().upper() for w in raw.split('\n') if w.strip()]
                
                elif t_data["q_type"] == "Game: Ô Chữ":
                    words = []
                    for r in t_data.get("cross_rows", []):
                        w = r.get("w", "").strip().upper().replace(" ", "")
                        c = r.get("c", "").strip()
                        if w and c: words.append({"word": w, "clue": c})
                    if len(words) < 4:
                        st.error("Cần tối thiểu 4 từ vựng!")
                        st.stop()
                    iso = check_connectivity(words)
                    if iso:
                        st.error(f"Các từ sau bị cô lập: {', '.join(iso)}")
                        st.stop()
                    layout, msg = generate_crossword_layout(words)
                    if not layout:
                        st.error(msg)
                        st.stop()
                    t_data["cross_layout"] = layout
                
                elif t_data["q_type"] == "Game: Bức Tranh Bí Ẩn":
                    if not t_data.get("hidden_bg", "").strip():
                        st.error("Vui lòng nhập link ảnh nền!")
                        st.stop()
                    imgs = [r.strip() for r in t_data.get("hidden_imgs", []) if r.strip()]
                    if len(imgs) < 6:
                        st.error("Cần tối thiểu 6 ô ảnh cắt!")
                        st.stop()
                    t_data["hidden_imgs"] = imgs
                
                elif t_data["q_type"] == "Game: Lật Thẻ Nhớ":
                    pairs = []
                    for r in t_data.get("memory_pairs", []):
                        if r.get("w", "").strip() or r.get("img", "").strip():
                            pairs.append({"word": r.get("w", "").strip(), "image": r.get("img", "").strip()})
                    if len(pairs) < 4:
                        st.error("Cần tối thiểu 4 cặp từ-ảnh!")
                        st.stop()
                    t_data["memory_pairs"] = pairs

                if is_new: st.session_state.quiz_data.append(t_data)
                else: st.session_state.quiz_data[idx] = t_data
                
                save_data()
                del st.session_state.temp_quiz
                navigate("Quiz", None)
                
            if col_btn2.button("❌ Hủy"):
                del st.session_state.temp_quiz
                navigate("Quiz", None)
                
        else: # List view
            col1, col2 = st.columns([1, 1])
            if col1.button("➕ THÊM BÀI TẬP / TRÒ CHƠI", type="primary"):
                navigate("Quiz", -1)
                
            if len(st.session_state.quiz_data) > 0:
                to_delete = []
                for i, data in enumerate(st.session_state.quiz_data):
                    title = data.get('topic') or data.get('q_raw', '')[:50]
                    if not title: title = "Câu hỏi " + data.get('q_type', '')
                    with st.container():
                        c1, c2, c3, c4 = st.columns([1, 6, 1, 1])
                        if c1.checkbox("Chọn", key=f"quiz_chk_{i}"): to_delete.append(i)
                        c2.markdown(f"**Mục {i+1}: {title}**")
                        if c3.button("✏️ Sửa", key=f"quiz_edit_{i}"): navigate("Quiz", i)
                        if c4.button("📑 Nhân bản", key=f"quiz_clone_{i}"):
                            st.session_state.quiz_data.insert(i + 1, data.copy())
                            save_data()
                            st.rerun()
                
                if to_delete:
                    if st.button("🗑 XÓA CÁC MỤC ĐÃ CHỌN", type="primary", key="del_quiz"):
                        for i in sorted(to_delete, reverse=True):
                            del st.session_state.quiz_data[i]
                        save_data()
                        st.rerun()
            else:
                st.info("Chưa có bài tập nào.")

if __name__ == "__main__":
    main()