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

# ====== 新增：自動分行排版函式 ======
def format_display_text(text):
    """
    將答案中的條列式項目 (如 1、 2.) 自動分行，以利閱讀。
    使用正規表示式尋找「數字+、」或「數字+.」，並在前面強制換行。
    """
    # \s* 代表可能存在的空白，\d+ 代表數字，[、.] 代表頓號或小數點
    formatted = re.sub(r'\s*(\d+[、.])', r'\n\n\1', text)
    return formatted.strip()
# ====================================

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

    # ==========================================
    # 左側邊欄：測驗設定
    # ==========================================
    with st.sidebar:
        st.header("⚙️ 測驗設定")
        selected_bank = st.selectbox("📚 選擇班隊 (題庫)", list(bank_mapping.keys()))
        selected_file = bank_mapping[selected_bank]
        all_questions = load_questions_from_file(selected_file)
        
        st.caption(f"當前題庫共有： {len(all_questions)} 題")
        st.divider()
        
        st.subheader("選擇範圍")
        col1, col2 = st.columns(2)
        max_q = len(all_questions) if all_questions else 1
        with col1:
            start_id = st.number_input("起 (題號)", min_value=1, max_value=max_q, value=1)
        with col2:
            end_id = st.number_input("迄 (題號)", min_value=1, max_value=max_q, value=max_q)

        st.divider()

        st.subheader("選擇模式")
        is_shuffle = st.checkbox("🎲 亂序排列", value=False)
        display_mode = st.radio("顯示模式：", ["逐題顯示", "全部顯示", "字卡模式"], index=0)

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

    # ==========================================
    # 主畫面區塊
    # ==========================================
    if st.session_state.current_bank_name:
        st.title(f"🎯 {st.session_state.current_bank_name}")
    else:
        st.title("🎯 兵科題庫 測驗系統")

    if not st.session_state.test_questions:
        st.info("👈 請在左側設定後開始測驗。")
        return

    total_q = len(st.session_state.test_questions)

    # ------------------------------------------
    # 模式 A：全部顯示
    # ------------------------------------------
    if display_mode == "全部顯示":
        st.subheader(f"📝 全部顯示模式 (共 {total_q} 題)")
        
        for idx, q in enumerate(st.session_state.test_questions, 1):
            with st.container(border=True):
                st.markdown(f"**第 {idx} 題** (原題號: {q['id']})")
                st.write(f"💡 **{q['question']}**")
                
                input_key = f"input_{st.session_state.current_bank_name}_{q['id']}"
                saved_val = st.session_state.all_inputs.get(input_key, "")
                
                with st.form(key=f"form_{q['id']}", clear_on_submit=False):
                    user_val = st.text_area("您的答案：", value=saved_val, height=80)
                    submit_q = st.form_submit_button("📤 送出答案")
                    
                    if submit_q:
                        st.session_state.all_inputs[input_key] = user_val
                        if not user_val.strip():
                            st.warning("請輸入內容後再送出。")
                        else:
                            is_correct, msg = check_answer(user_val, q['answer'])
                            if is_correct:
                                st.success(f"✅ {msg}")
                            else:
                                st.error("❌ 答錯了！")
                                # 這裡套用排版函式
                                st.info(f"📌 **標準答案：**\n\n{format_display_text(q['answer'])}")
                
                if not submit_q:
                    with st.expander("👁️ 快速查看標準答案"):
                        # 這裡套用排版函式
                        st.write(format_display_text(q['answer']))

    # ------------------------------------------
    # 模式 B：逐題顯示
    # ------------------------------------------
    elif display_mode == "逐題顯示":
        if st.session_state.current_idx >= total_q:
            st.balloons()
            st.success("🏆 測驗結束！")
            st.metric(label="最終成績", value=f"{st.session_state.score} / {total_q} 題")
            if st.button("🔄 重新測驗"):
                st.session_state.current_idx = 0
                st.session_state.score = 0
                st.session_state.feedback = ""
                st.session_state.has_answered = False
                st.rerun()
            return

        current_q = st.session_state.test_questions[st.session_state.current_idx]
        st.progress(st.session_state.current_idx / total_q, text=f"進度：{st.session_state.current_idx + 1} / {total_q}")
        
        with st.container(border=True):
            st.subheader(f"💡 題目：{current_q['question']}")
            st.caption(f"原題號：{current_q['id']}")
            
            if st.session_state.feedback:
                if "✅" in st.session_state.feedback: st.success(st.session_state.feedback)
                else: st.error(st.session_state.feedback)

            if not st.session_state.has_answered:
                with st.form(key='one_by_one_form', clear_on_submit=False):
                    user_ans = st.text_area("📝 輸入答案：", height=100)
                    if st.form_submit_button("📤 送出答案"):
                        if not user_ans.strip():
                            st.warning("請先輸入答案再送出喔！")
                        else:
                            is_correct, msg = check_answer(user_ans, current_q['answer'])
                            if is_correct:
                                st.session_state.score += 1
                                st.session_state.feedback = f"✅ **答對了！** {msg}"
                            else:
                                # 這裡套用排版函式
                                st.session_state.feedback = f"❌ **答錯了！**\n\n📌 **標準答案：**\n\n{format_display_text(current_q['answer'])}"
                            
                            st.session_state.has_answered = True
                            st.rerun()
            else:
                if st.button("⏭️ 前往下一題", type="primary", use_container_width=True):
                    st.session_state.current_idx += 1
                    st.session_state.has_answered = False
                    st.session_state.feedback = ""
                    st.rerun()

            with st.expander("🫣 想不起來？點我偷看答案 (不計分)"):
                # 這裡套用排版函式
                st.info(format_display_text(current_q['answer']))
                if st.button("⏭️ 直接跳下一題"):
                    # 這裡套用排版函式
                    st.session_state.feedback = f"⏭️ **已跳過該題。**\n\n📌 **標準答案：**\n\n{format_display_text(current_q['answer'])}"
                    st.session_state.current_idx += 1
                    st.session_state.has_answered = False
                    st.rerun()

    # ------------------------------------------
    # 模式 C：字卡模式
    # ------------------------------------------
    elif display_mode == "字卡模式":
        st.subheader("📇 隨機字卡")
        if st.session_state.flashcard_q is None:
            st.session_state.flashcard_q = random.choice(st.session_state.test_questions)
            st.session_state.flashcard_flipped = False

        with st.container(border=True):
            st.markdown(f"### 🤔 {st.session_state.flashcard_q['question']}")
            st.divider()
            if st.session_state.flashcard_flipped:
                # 這裡套用排版函式
                st.success(f"**標準答案：**\n\n{format_display_text(st.session_state.flashcard_q['answer'])}")
            else:
                st.write("\n\n*(默念答案後點擊翻開)*\n\n")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 翻開字卡", use_container_width=True) and not st.session_state.flashcard_flipped:
                st.session_state.flashcard_flipped = True
                st.rerun()
        with col2:
            if st.button("⏭️ 抽下一題", use_container_width=True, type="primary"):
                st.session_state.flashcard_q = random.choice(st.session_state.test_questions)
                st.session_state.flashcard_flipped = False
                st.rerun()

if __name__ == "__main__":
    main()
