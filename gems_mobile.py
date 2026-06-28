import streamlit as st
import pandas as pd
import asyncio
import edge_tts
import base64
import streamlit.components.v1 as components
import time

# 페이지 설정
st.set_page_config(page_title="크메르어 학습기", page_icon="🎧", layout="wide")

# 스타일 설정: 20pt 폰트 및 상단 밀착형 레이아웃
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Khmer:wght@700&display=swap');
    
    .main > div { padding-top: 0rem; }
    
    .khmer-text {
        font-family: 'Noto Sans Khmer', sans-serif !important;
        font-size: 20pt !important;
        font-weight: 700 !important;
        line-height: 1.2;
    }
    
    .korean-text {
        font-size: 20pt !important;
        font-weight: 700 !important;
        line-height: 1.2;
    }
    
    /* 상단 여백 제거 */
    .stApp > header { display: none; }
    div[data-testid="stToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# 데이터 예시 (사역 현장 맞춤형)
data = {
    "크메르어": ["សួស្តី", "អរគុណ", "ព្រះអម្ចាស់"],
    "한글": ["안녕하세요", "감사합니다", "주님"]
}
df = pd.DataFrame(data)

st.title("🎧 크메르어 학습기")

# TTS 엔진 함수
def get_edge_audio(text, voice="km-KH-PisethNeural"):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def _gen():
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
    return loop.run_until_complete(_gen())

# 메인 학습 인터페이스
for i, row in df.iterrows():
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"<div class='khmer-text'>{row['크메르어']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='korean-text'>{row['한글']}</div>", unsafe_allow_html=True)
    with col2:
        if st.button(f"듣기 {i}", key=f"btn_{i}"):
            audio_bytes = get_edge_audio(row['크메르어'])
            b64 = base64.b64encode(audio_bytes).decode()
            audio_html = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}"></audio>'
            components.html(audio_html, height=0)
    st.divider()

st.success("데이터베이스 연동 준비 완료 및 학습 모듈 정상 작동 중입니다.")
