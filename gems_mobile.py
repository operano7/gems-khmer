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

# CSS 주입 (폰트 및 레이아웃)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Khmer:wght@700&display=swap');
:root { --font: 'Noto Sans Khmer', sans-serif; }
body, .stApp { font-family: 'Noto Sans Khmer', sans-serif; }
.khmer-custom-font { font-family: 'Noto Sans Khmer', sans-serif !important; font-size: 20pt !important; font-weight: 700 !important; }
div[role="radiogroup"] { gap: 3rem !important; }
div[data-testid="stCheckbox"] p { white-space: nowrap !important; }
</style>
""", unsafe_allow_html=True)

# 상태 관리
if "is_continuous_playing" not in st.session_state: st.session_state.is_continuous_playing = False
if "current_play_idx" not in st.session_state: st.session_state.current_play_idx = 0
if "last_clicked_row" not in st.session_state: st.session_state.last_clicked_row = None

# 데이터 로드
EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

@st.cache_data
def load_data(filepath):
    df = pd.read_excel(filepath, header=None, engine='openpyxl')
    # 기본 전처리 생략 (이전 버전 유지)
    return df

if EXCEL_FILE:
    df_raw = load_data(EXCEL_FILE)
    # 데이터 처리 로직 (이전 버전 유지)
    processed_df = df_raw.copy() # 실제 처리 로직 적용
else:
    st.error("파일 없음")
    st.stop()

# 💡 개선된 재생 로직: 즉시 정지 기능 포함
def play_sequential_audio(audio_bytes_list, is_continuous=False):
    if not audio_bytes_list: return
    b64_audios = [f"data:audio/mp3;base64,{base64.b64encode(ab).decode()}" for ab in audio_bytes_list]
    js_array = str(b64_audios).replace("'", '"')
    
    html_code = f"""
    <audio id="player" style="display:none;"></audio>
    <button id="btn" style="background:#0d6efd; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold;">▶️ 재생</button>
    <script>
        var player = document.getElementById("player");
        var btn = document.getElementById("btn");
        var audios = {js_array};
        var idx = 0;
        
        function stopPlayer() {{
            player.pause();
            player.src = "";
            btn.innerText = "▶️ 재생";
            btn.style.backgroundColor = "#0d6efd";
        }}

        btn.onclick = function() {{
            if (player.paused && player.src) {{ player.play(); }}
            else {{ stopPlayer(); }}
        }};

        player.onended = function() {{
            idx++;
            if(idx < audios.length) {{ player.src = audios[idx]; player.play(); }}
            else {{
                if({'true' if is_continuous else 'false'}) {{
                    var buttons = window.parent.document.querySelectorAll('button');
                    for(var i=0; i<buttons.length; i++) {{
                        if(buttons[i].innerText.trim() === 'AUTO_NEXT_BTN_XYZ') {{ buttons[i].click(); }}
                    }}
                }} else {{ stopPlayer(); }}
            }}
        }};
        
        // 초기화
        player.src = audios[0];
        player.play();
        btn.innerText = "🔊 재생중";
        btn.style.backgroundColor = "#198754";
    </script>
    """
    components.html(html_code, height=60)

# 메인 UI
st.write("표 선택 및 재생 테스트")
# ... 이전 버전의 표 및 상태 동기화 로직 적용 ...

# 자동 넘김 처리
if st.button("AUTO_NEXT_BTN_XYZ", key="auto_next"):
    st.session_state.current_play_idx += 1
    st.rerun()
