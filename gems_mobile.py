import streamlit as st
import pandas as pd
import io
import os
import asyncio
import edge_tts
import base64
import streamlit.components.v1 as components

# 1. 화면 설정
st.set_page_config(page_title="크메르어 학습기", page_icon="🎧", layout="wide")

st.header("🎧 크메르어 학습기")

# CSS 주입
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Khmer:wght@700&display=swap');
:root { --font: 'Noto Sans Khmer', sans-serif; }
body, .stApp { font-family: 'Noto Sans Khmer', sans-serif; }
.khmer-custom-font { font-family: 'Noto Sans Khmer', sans-serif !important; font-size: 20pt !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# 💡 [핵심] 상태 관리 최적화
if "current_play_idx" not in st.session_state: st.session_state.current_play_idx = 0
if "is_continuous" not in st.session_state: st.session_state.is_continuous = False

# 데이터 로드
EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

@st.cache_data
def load_data(filepath):
    return pd.read_excel(filepath, header=None, engine='openpyxl')

if EXCEL_FILE:
    processed_df = load_data(EXCEL_FILE)
    # 데이터가 로드되면 간단히 번호/원문/발음/해석 구조로 가정
    df = processed_df.iloc[1:].dropna(how='all')
    df.columns = ['번호', '원문', '발음', '한국어', '영어']
    df = df.reset_index(drop=True)
else:
    st.error("파일 없음")
    st.stop()

# 💡 [개선된 플레이어] 자바스크립트가 완전히 상태를 장악하도록 수정
def play_sequential_audio(audio_bytes, is_continuous):
    b64 = base64.b64encode(audio_bytes).decode()
    html_code = f"""
    <audio id="player" src="data:audio/mp3;base64,{b64}" autoplay></audio>
    <button id="btn" style="background:#198754; color:white; padding:10px 20px; border:none; border-radius:5px;">🔊 재생중</button>
    <script>
        var player = document.getElementById("player");
        player.onended = function() {{
            if({str(is_continuous).lower()}) {{
                var btn = window.parent.document.querySelector('button[kind="secondary"]');
                // 자동 넘김 트리거 (streamlit 버튼)
                var buttons = window.parent.document.querySelectorAll('button');
                for(var i=0; i<buttons.length; i++) {{
                    if(buttons[i].innerText.includes('AUTO_NEXT')) {{ buttons[i].click(); }}
                }}
            }}
        }};
    </script>
    """
    components.html(html_code, height=60)

# 💡 [표 선택 로직]
selection = st.dataframe(df, use_container_width=True, on_select="rerun", selection_mode="single-row", key="table")
if selection.selection.rows:
    st.session_state.current_play_idx = selection.selection.rows[0]

# 재생 제어 UI
col1, col2 = st.columns(2)
if col1.button("연속 재생 시작/정지"):
    st.session_state.is_continuous = not st.session_state.is_continuous
    st.rerun()

# 실제 재생
if st.session_state.current_play_idx < len(df):
    text = df.iloc[st.session_state.current_play_idx]['원문']
    # 오디오 생성 로직 생략 (생성 후 bytes 변수에 담김)
    # play_sequential_audio(audio_bytes, st.session_state.is_continuous)

# 자동 넘김용 숨김 버튼
if st.button("AUTO_NEXT", key="next"):
    st.session_state.current_play_idx += 1
    st.rerun()
