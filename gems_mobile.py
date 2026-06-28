import streamlit as st
import pandas as pd
import io
import os
import asyncio
import edge_tts
import base64
import streamlit.components.v1 as components
import time
import re

# 1. 화면 설정
st.set_page_config(page_title="크메르어 학습기", page_icon="🎧", layout="wide")

st.header("🎧 크메르어 학습기")

# 앱 UI 커스텀 CSS 주입
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Khmer:wght@700&display=swap');

:root {
    --font: 'Noto Sans Khmer', sans-serif;
}

body, .stApp {
    font-family: 'Noto Sans Khmer', sans-serif;
}

.khmer-custom-font {
    font-family: 'Noto Sans Khmer', sans-serif !important;
    font-size: 20pt !important;
    font-weight: 700 !important;
}

div[role="radiogroup"] {
    gap: 3rem !important; 
}

div[data-testid="stCheckbox"] p {
    white-space: nowrap !important;
}

/* 📊 표 스타일 제어: 휜색 테두리 눈에 띄게 추가 및 글자 크기 조정 */
div[data-testid="stDataFrame"] {
    border: 1.5px solid #ffffff !important;
    border-radius: 0.25rem;
}

div[data-testid="stDataFrame"] data-grid-canvas {
    font-size: 10pt !important;
}
</style>
<div style="font-family: 'Noto Sans Khmer'; font-weight: 700; position: absolute; width: 0; height: 0; overflow: hidden;">
    Preload Noto Sans Khmer Bold
</div>
""", unsafe_allow_html=True)

# 상태 관리
if "is_continuous_playing" not in st.session_state:
    st.session_state.is_continuous_playing = False
if "current_play_idx" not in st.session_state:
    st.session_state.current_play_idx = 0
if "last_clicked_row" not in st.session_state:
    st.session_state.last_clicked_row = None

# 읽어줄 언어 복수 선택 및 교차 재생 순서/대기시간 UI
st.markdown("📖 **읽어줄 언어를 선택하세요 (복수 선택 가능):**")
col_l1, col_l2, _ = st.columns([1.2, 1.2, 3.6])

with col_l1:
    read_khm = st.checkbox("크메르어", value=True)
with col_l2:
    read_kor = st.checkbox("한국어")
    
read_langs = []

if read_khm and read_kor:
    st.markdown("<div style='margin-top: 5px; margin-bottom: 5px;'>🔄 <b>두 언어 재생 순서를 선택하세요:</b></div>", unsafe_allow_html=True)
    order_choice = st.radio(
        "재생 순서",
        options=["1. 크메르어 먼저 재생", "2. 한국어 먼저 재생"],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )
    if order_choice == "1. 크메르어 먼저 재생":
        read_langs = ["크메르어", "한국어"]
    else:
        read_langs = ["한국어", "크메르어"]
        
    st.markdown("<div style='margin-top: 5px; margin-bottom: 5px;'>⏳ <b>언어 간 대기 시간을 선택하세요:</b></div>", unsafe_allow_html=True)
    lang_delay_choice = st.radio(
        "언어 간 대기 시간",
        options=["1초", "3초", "5초", "10초"],
        index=1,
        horizontal=True,
        label_visibility="collapsed"
    )
    if lang_delay_choice == "1초": lang_delay_ms = 1000
    elif lang_delay_choice == "3초": lang_delay_ms = 3000
    elif lang_delay_choice == "5초": lang_delay_ms = 5000
    elif lang_delay_choice == "10초": lang_delay_ms = 10000
    else: lang_delay_ms = 1000
else:
    lang_delay_ms = 0
    if read_khm: read_langs.append("크메르어")
    if read_kor: read_langs.append("한국어")

if not read_langs:
    st.warning("⚠️ 읽어줄 언어를 최소 1개 이상 체크해 주세요.")

st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# TTS 선택 UI
st.markdown("🗣️ **음성 종류를 선택하세요:**")
col_v1, col_v2, col_v3, _ = st.columns([1.2, 1.2, 1.2, 2.4])

with col_v1:
    use_edge_m = st.checkbox("MS Edge (남성)")
with col_v2:
    use_edge_f = st.checkbox("MS Edge (여성)")
with col_v3:
    use_google = st.checkbox("Google (여성)", value=True)

voice_options = []
if use_edge_m: voice_options.append("MS Edge (남성)")
if use_edge_f: voice_options.append("MS Edge (여성)")
if use_google: voice_options.append("Google (여성)")

if not voice_options:
    st.warning("⚠️ 재생할 목소리를 최소 1개 이상 체크해 주세요.")

st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# 속도 조절 UI
speed_choice = st.radio(
    "속도 선택",
    options=["아주 느리게 (0.6x)", "조금 느리게 (0.8x)", "보통 속도 (1.0x)"],
    index=2,
    horizontal=True,
    label_visibility="collapsed"
)

if speed_choice == "아주 느리게 (0.6x)":
    final_edge_rate_str = "-40%"
    final_gtts_slow = True
elif speed_choice == "조금 느리게 (0.8x)":
    final_edge_rate_str = "-20%"
    final_gtts_slow = False
else:
    final_edge_rate_str = "+0%"
    final_gtts_slow = False

st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# 연속 재생 대기 시간 선택 UI
st.markdown("⏱️ **연속 재생 대기 시간을 선택하세요:**")
delay_choice = st.radio(
    "대기 시간 선택",
    options=["1초", "3초", "5초"],
    index=0,
    horizontal=True,
    label_visibility="collapsed"
)

if delay_choice == "1초":
    delay_ms = 1000
elif delay_choice == "3초":
    delay_ms = 3000
else:
    delay_ms = 5000

st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# 엑셀 파일 자동 탐색
EXCEL_FILE = None
for name in ["캄보디아어 공부"]: 
    for ext in ['.xlsx', '.xlsm']:
        if os.path.exists(f"{name}{ext}"):
            EXCEL_FILE = f"{name}{ext}"
            break
    if EXCEL_FILE: break

if not EXCEL_FILE:
    st.error("❌ 학습할 엑셀 파일('캄보디아어 공부.xlsm' 또는 .xlsx)이 없습니다.")
    st.stop()

# 크메르어 마스터 패턴 로딩 
PATTERN_FILE = None
for name in ["캄보디아어패턴_선별", "크메르어패턴_선별", "핵심_회화패턴"]:
    for ext in ['.xlsx', '.csv']:
        if os.path.exists(f"{name}{ext}"):
            PATTERN_FILE = f"{name}{ext}"
            break
    if PATTERN_FILE: break

@st.cache_data
def load_master_patterns(filepath, last_modified):
    try:
        if filepath.endswith('.csv'):
            df_pat = pd.read_csv(filepath, header=None)
        else:
            df_pat = pd.read_excel(filepath, header=None, engine='openpyxl')
            
        pattern_col_idx = None
        type_col_idx = None
        pattern_row_idx = None
        
        for r in range(min(10, len(df_pat))):
            row_found = False
            for c in range(len(df_pat.columns)):
                val = str(df_pat.iloc[r, c]).strip().lower()
                if val in ['pattern', '패턴']:
                    pattern_col_idx = c
                    row_found = True
                elif '구분' in val or '시작' in val:
                    type_col_idx = c
            if row_found:
                pattern_row_idx = r
                break
                
        if pattern_col_idx is None:
            pattern_col_idx = 1
            pattern_row_idx = 0
            
        unique_patterns = {}
        for i in range(pattern_row_idx + 1, len(df_pat)):
            p = str(df_pat.iloc[i, pattern_col_idx])
            if p.lower() in ['nan', 'none', '']: continue
            
            p_clean = re.sub(r"[^\w\s']", ' ', p.lower()).strip()
            if not p_clean: continue
            
            p_type = "시작"
            if type_col_idx is not None:
                t_val = str(df_pat.iloc[i, type_col_idx])
                if '중간' in t_val:
                    p_type = "중간"
            else:
                p_type = "중간"
                
            if p_clean in unique_patterns:
                if unique_patterns[p_clean] == "시작" and p_type == "중간":
                    unique_patterns[p_clean] = "중간"
            else:
                unique_patterns[p_clean] = p_type
                
        sorted_keys = sorted(unique_patterns.keys(), key=lambda x: len(x.split()), reverse=True)
        return {k: unique_patterns[k] for k in sorted_keys}
    except Exception as e:
        st.error(f"❌ 패턴 마스터 파일 로드 중 오류: {e}")
        return {}

if PATTERN_FILE:
    pattern_mtime = os.path.getmtime(PATTERN_FILE)
    MASTER_PATTERNS = load_master_patterns(PATTERN_FILE, pattern_mtime)
else:
    st.info("💡 팁: '캄보디아어패턴_선별.xlsx' 파일을 업로드하시면 패턴 강조 기능이 활성화됩니다.")
    MASTER_PATTERNS = {}

@st.cache_data
def load_all_data(filepath, last_modified):
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    
    excel_data = io.BytesIO(file_bytes)
    xl = pd.ExcelFile(excel_data, engine='openpyxl')
    sheet_names = xl.sheet_names
    
    sheets_dict = {}
    for sheet in sheet_names:
        sheets_dict[sheet] = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=0, engine='openpyxl')
        
    return sheet_names, sheets_dict

try:
    file_modified_time = os.path.getmtime(EXCEL_FILE)
    sheet_names, all_sheets = load_all_data(EXCEL_FILE, file_modified_time)
except Exception as e:
    st.error(f"❌ 데이터 로드 중 오류: {e}")
    st.stop()

col_sheet_select, col_search_input = st.columns(2)

with col_sheet_select:
    selected_sheet = st.selectbox("📂 학습할 단어장 시트:", sheet_names)

with col_search_input:
    search_query = st.text_input("🔍 검색어 입력:", "")

def process_sheet_data(df):
    if '크메르어' not in df.columns and '캄보디아어' not in df.columns:
        for i in range(min(5, len(df))):
            row_vals = df.iloc[i].astype(str).str.strip().tolist()
            if '크메르어' in row_vals or '캄보디아어' in row_vals:
                df.columns = row_vals
                df = df.iloc[i+1:].reset_index(drop=True)
                break
                
    df.columns = [str(c).strip() for c in df.columns]

    def clean_text(text):
        t = str(text).strip()
        if t.lower() in ['nan', 'none', 'nat', '']: return ""
        if t.endswith('.0'): return t[:-2]
        return t
        
    for c in df.columns:
        df[c] = df[c].apply(clean_text)
    
    khmer_col = '크메르어' if '크메르어' in df.columns else '캄보디아어' if '캄보디아어' in df.columns else None
    
    if khmer_col:
        df = df[df[khmer_col] != '']
    return df

processed_df = process_sheet_data(all_sheets[selected_sheet])

# 동적 타겟 컬럼명 추출 (크메르어 or 캄보디아어)
KHMER_TARGET_COL = '크메르어' if '크메르어' in processed_df.columns else '캄보디아어' if '캄보디아어' in processed_df.columns else None

# 크메르어 문장 내 마스터 패턴 하이라이트 적용 엔진
@st.cache_data(show_spinner=False)
def apply_fixed_patterns(df, target_col, frequent_patterns=None):
    if not target_col or target_col not in df.columns:
        return df
        
    if not frequent_patterns:
        df = df.copy()
        df[target_col + '_display'] = df[target_col]
        return df
        
    highlight_color = "#d97706" 
    
    def highlight_text(text):
        if not text or not str(text).strip(): return text
        text_str = str(text)
        clean_text = re.sub(r"[^\w\s']", ' ', text_str.lower()).strip()
        padded_clean = f" {clean_text} "
        
        matched_spans = []
        
        for pat, pat_type in frequent_patterns.items():
            if f" {pat} " in padded_clean:
                pat_words = pat.split()
                pat_len = len(pat_words)
                
                boundary_start = r"(?<![\w'])"
                boundary_end = r"(?![\w'])"
                regex_parts = [boundary_start + re.escape(w) + boundary_
