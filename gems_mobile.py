import streamlit as st
import pandas as pd
import os
import asyncio
import edge_tts
import base64
import streamlit.components.v1 as components

# 1. 화면 설정
st.set_page_config(page_title="크메르어 학습기", page_icon="🎧", layout="wide")
st.header("🎧 크메르어 학습기")

# 상태 관리 초기화
if "current_play_idx" not in st.session_state: st.session_state.current_play_idx = 0
if "is_continuous" not in st.session_state: st.session_state.is_continuous = False

# 데이터 로드
@st.cache_data
def load_data():
    EXCEL_FILE = None
    for ext in ['.xlsm', '.xlsx']:
        if os.path.exists(f"캄보디아어 공부{ext}"):
            EXCEL_FILE = f"캄보디아어 공부{ext}"
            break
    if not EXCEL_FILE: return None
    df = pd.read_excel(EXCEL_FILE, header=None, engine='openpyxl').iloc[1:].dropna(how='all')
    required_cols = ['번호', '원문', '발음', '한국어', '영어']
    df = df.iloc[:, :len(required_cols)]
    df.columns = required_cols
    return df.reset_index(drop=True)

df = load_data()
if df is None: st.error("파일 없음"); st.stop()

# 오디오 생성 엔진 (캐시 적용)
@st.cache_data(show_spinner=False)
def get_audio_bytes(text):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    communicate = edge_tts.Communicate(text, "km-KH-PisethNeural")
    audio_data = b""
    loop.run_until_complete(asyncio.gather(*[
        asyncio.create_task(communicate.stream())
    ]))
    # 간소화된 생성 로직 (환경별 최적화)
    return loop.run_until_complete(edge_tts.Communicate(text, "km-KH-PisethNeural").save(None))

# 💡 개선된 통합 플레이어
def render_player(text, is_continuous):
    # 실제 오디오 생성
    audio_bytes = asyncio.run(edge_tts.Communicate(text, "km-KH-PisethNeural").save(None))
    b64 = base64.b64encode(audio_bytes).decode()
    
    html = f"""
    <audio id="audio" src="data:audio/mp3;base64,{b64}" autoplay></audio>
    <script>
        var audio = document.getElementById("audio");
        audio.onended = function() {{
            if({str(is_continuous).lower()}) {{
                window.parent.document.querySelector('[data-testid="stButton"] button').click();
            }}
        }};
    </script>
    """
    components.html(html, height=0)

# 표 선택 및 재생 관리
selection = st.dataframe(df, use_container_width=True, on_select="rerun", selection_mode="single-row", key="table")
if selection.selection.rows:
    st.session_state.current_play_idx = selection.selection.rows[0]

if st.button("연속 재생 전환"):
    st.session_state.is_continuous = not st.session_state.is_continuous
    st.rerun()

# 자동 순차 재생 로직
if st.session_state.current_play_idx < len(df):
    text = df.iloc[st.session_state.current_play_idx]['원문']
    st.write(f"현재: {text}")
    render_player(text, st.session_state.is_continuous)
    
    # 자동 넘김용 버튼 (CSS로 숨김 처리 예정)
    if st.button("▶️ 다음 항목으로"):
        st.session_state.current_play_idx = (st.session_state.current_play_idx + 1) % len(df)
        st.rerun()
