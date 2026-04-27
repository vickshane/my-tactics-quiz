import streamlit as st
import random
import re
import os
import difflib

# --- 1. 核心邏輯函式 ---
def load_questions_from_file(filename):
    questions_data = []
    if not os.path.exists(filename):
        return questions_data
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('|')
            if len(parts) >= 3:
                try:
                    q_id = int(parts[0])
                    questions_data.append({
                        "id": q_id,
                        "question": parts[1],
                        "answer": parts[2]
                    })
                except ValueError:
                    continue
    return questions_data

def normalize_text(text):
    text = re.sub(r'\d+[、.]\s*', '', text)
    text = re.sub(r'[^\w]', '', text)
    return text

def check_answer(user_input, correct_answer):
    norm_user = normalize_text(user_input)
    norm_ans = normalize_text(correct_answer)
    
    if norm_ans in norm_user:
        return True, "完全正確！"
        
    similarity = difflib.SequenceMatcher(None, norm_ans, norm_user).ratio()
    if similarity >= 0.8:
        return True, f"算你對！(相似度 {similarity:.0%}，有少許錯漏字)"
        
    return False, ""

# ====== 自動分行排版函式 ======
def format_display_text(text):
    formatted = re.sub(r'\s*(\d+[、.])', r'\n\n\1', text)
    return formatted.strip()

# --- 2. 網頁介面與狀態管理 ---
def main():
    st.set_page_config(page_title="戰術題庫 測驗系統", page_icon="🎯", layout="wide")
    
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and f != 'requirements.txt']
    if not txt_files:
        st.error("⚠️ 找不到任何 `.txt` 題庫檔案。")
        return

    bank_mapping = {os.path.splitext(f)[0]: f for f in txt_files}

    if 'test_questions' not in st.session_state:
        st.session_state.test_questions = []
        st.session_state.current_idx = 0
        st.session_state.score = 0
        st.session_state.feedback = ""
        st.session_state.flashcard_q = None
        st.session_state.flashcard_flipped = False
        st.session_state.all_inputs = {}
        st.session_state.current_bank_name = ""
        st.session_state.has_answered = False 

    # ====== 埋設最上方的隱形錨點 ======
    st.markdown("<div id='nav-settings'></div>", unsafe_allow_html=True)
    # =================================

    # 顯示大標題
    if st.session_state.current_bank_name:
        st.title(f"🎯 {st.session_state.current_bank_name}")
    else:
        st.title("🎯 兵科題庫 測驗系統")

    # ==========================================
    # 上方設定面板
    # ==========================================
    with st.container(border=True):
        st.subheader("⚙️ 測驗與音樂設定面板")
        
        col_music, col_quiz = st.columns([1, 2])
        
        with col_music:
            st.markdown("##### 🎵 測驗電台")
            mp3_files = [f for f in os.listdir('.') if f.endswith('.mp3')]
            
            if mp3_files:
                selected_song = st.selectbox("選擇歌曲：", mp3_files)
                st.audio(selected_song, format="audio/mp3", loop=True)
            else:
                st.caption("找不到任何 MP3 音樂檔案")
                
        with col_quiz:
            st.markdown("##### 📚 題庫與模式設定")
            
            selected_bank = st.selectbox("選擇班隊 (題庫)：", list(bank_mapping.keys()), label_visibility="collapsed")
            selected_file = bank_mapping[selected_bank]
            all_questions = load_questions_from_file(selected_file)
            
            col_q1, col_q2, col_q3 = st.columns([1, 1, 1])
            max_q = len(all_questions) if all_questions else 1
            with col_q1:
                start_id = st.number_input("起 (題號)", min_value=1, max_value=max_q, value=1)
            with col_q2:
                end_id = st.number_input("迄 (題號)", min_value=1, max_value=max_q, value=max_q)
            with col_q3:
                st.write("")
                st.write("")
                is_shuffle = st.checkbox("🎲 亂序排列", value=False)

            col_m1, col_m2 = st.columns([3, 2])
            with col_m1:
                display_mode = st.radio("顯示模式：", ["逐題顯示", "全部顯示", "字卡模式"], index=0, horizontal=True)
            with col_m2:
                if st.button("🚀 載入 / 重置題目", use_container_width=True, type="primary"):
                    filtered = [q for q in all_questions if start_id <= q['id'] <= end_id]
                    if filtered:
                        if is_shuffle: random.shuffle(filtered)
                        st.session_state.test_questions = filtered
                        st.session_state.current_bank_name = selected_bank
                        st.session_state.current_idx = 0
                        st.session_state.score = 0
                        st.session_state.feedback = ""
                        st.session_state.all_inputs = {}
                        st.session_state.has_answered = False 
                    else:
                        st.warning("該範圍內無題目！")
                    st.rerun()

    st.divider()

    # ==========================================
    # 🛗 左側電梯導覽 (快速樓梯)
    # 放在設定面板之後讀取，才能抓到最新的 display_mode 和題目
    # ==========================================
    with st.sidebar:
        st.header("🛗 快速導覽 (樓梯)")
        st.info("💡 點擊下方連結即可快速跳轉！")
        
        # 固定提供回到最上方的按鈕
        st.markdown("### 🔝
