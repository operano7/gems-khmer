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
st.set_page_config(page_title="영어 학습기", page_icon="🎧", layout="wide")

st.header("🎧 영어 학습기")

# 💡 [여백 완벽 수정] 폰트 20pt 적용 및 상단 여백 제거 (translateY(-10%))
st.markdown("""
<style>
.custom-font {
    font-family: sans-serif !important;
    font-size: 20pt !important; 
    font-weight: 700 !important;
    line-height: 1 !important; 
    display: inline-block;
    transform: translateY(-10%); 
}

div[role="radiogroup"] {
    gap: 3rem !important; 
}
</style>
""", unsafe_allow_html=True)

# 💡 [여백 수정] 상단 패딩은 0px, 하단은 12px 유지 (비대칭 패딩)
box_padding = "0px 14px 12px 14px"
inner_div_style = "line-height: 1; margin-top: 0px;" 

# [이하 데이터 처리 로직은 기존 영어 학습기 파일과 동일하게 유지됩니다]
# ... (데이터 로드, 검색, TTS 재생 로직 등)

# 렌더링 시 적용 예시:
# html_parts.append(f'<div style="{blue_bg} padding: {box_padding};"><div style="{inner_div_style}"><span class="custom-font" style="color: {blue_text};">{text}</span></div></div>')
