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

# 앱 UI 커스텀 CSS 주입
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Khmer:wght@700&display=swap');

:root {
    --font: 'Noto Sans Khmer', sans-serif;
}

.khmer-custom-font {
    font-family: 'Noto Sans Khmer', sans-serif !important;
    font-size: 20pt !important;
    font-weight: 700 !important;
    line-height: normal !important;
    color: #1E3A8A;
}

.korean-font {
    font-size: 16pt !important;
    font-weight: 500 !important;
    color: #333333;
}

div[role="radiogroup"] {
    gap: 3rem !important; 
}
</style>
""", unsafe_allow_html=True)

st.header("🎧 크메르어 학습기")

# 2. 학습 데이터 셋업 (임시 데이터베이스)
@st.cache_data
def load_data():
    data = {
        "id": [1, 2, 3],
        "khmer": ["សួស្តី", "អរគុណ", "សូមទោស"],
        "korean": ["안녕하세요", "감사합니다", "죄송합니다"]
    }
    return pd.DataFrame(data)

df = load_data()

# 3. 재생 모드 선택 UI
play_mode = st.radio("재생 모드 선택", ["일반 재생", "연속 재생"], horizontal=True)
st.markdown("---")

# 4. 일반 재생 모드 로직
if play_mode == "일반 재생":
    st.subheader("📖 일반 재생 모드")
    
    # 문장 선택 및 대기 시간 설정 UI
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        selected_korean = st.selectbox("학습할 문장을 선택하세요:", df["korean"].tolist())
    with col_sel2:
        wait_time = st.slider("언어 간 대기 시간(초)", min_value=1, max_value=5, value=2)
    
    # 선택한 문장의 매칭 데이터 추출
    selected_row = df[df["korean"] == selected_korean].iloc[0]
    
    st.write("") # 여백용
    col_lang1, col_lang2 = st.columns(2)
    
    # 5. 크메르어 우선 출력
    with col_lang1:
        st.caption("🇰🇭 크메르어")
        st.markdown(f'<div class="khmer-custom-font">{selected_row["khmer"]}</div>', unsafe_allow_html=True)
        
    # 6. 한국어 지연 출력 (Placeholder 및 time.sleep 활용)
    with col_lang2:
        st.caption("🇰🇷 한국어")
        korean_placeholder = st.empty()
        
        # 설정한 대기 시간만큼 지연 후 한국어 렌더링
        with st.spinner(f"{wait_time}초 후 뜻이 공개됩니다..."):
            time.sleep(wait_time)
            
        korean_placeholder.markdown(f'<div class="korean-font">{selected_row["korean"]}</div>', unsafe_allow_html=True)

# 7. 연속 재생 모드 로직 (추후 구현 영역)
elif play_mode == "연속 재생":
    st.subheader("▶️ 연속 재생 모드")
    st.info("이곳에 연속 재생 로직이 들어갑니다.")
