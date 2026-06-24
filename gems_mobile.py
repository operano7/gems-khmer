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
st.title("🎧 크메르어 학습기")

# 💡 [크메르어 전용 커스텀 폰트, 프리로딩 및 전역 CSS 강제 주입]
st.markdown("""
<style>
/* 1. 얇은 폰트를 배제하고 '굵은 글씨(700)' 버전의 Noto Sans Khmer 폰트만 단독 임포트 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Khmer:wght@700&display=swap');

/* 2. 💡 [화면 잘림 버그 해결] 스트림릿 레이아웃을 파괴하던 과도한 CSS를 제거하고, 
      표(Canvas)가 참조하는 가장 안전한 루트 폰트 변수만 정밀하게 덮어씁니다. */
:root {
    --font: 'Noto Sans Khmer', sans-serif;
}

body, .stApp {
    font-family: 'Noto Sans Khmer', sans-serif;
}

/* 선택된 텍스트 영역 커스텀 */
.khmer-custom-font {
    font-family: 'Noto Sans Khmer', sans-serif !important;
    font-size: 20pt !important;
    font-weight: 700 !important;
}

/* 속도 조절 라디오 버튼 가로 간격(gap) 넓히기 */
div[role="radiogroup"] {
    gap: 3rem !important; 
}

/* 체크박스 텍스트(Edge 남성/여성) 강제 한 줄 표시 (줄바꿈 방지) */
div[data-testid="stCheckbox"] p {
    white-space: nowrap !important;
}
</style>

<!-- 3. 💡 폰트 프리로딩(Preloading) 핵: 표가 그려지기 전 브라우저가 굵은 폰트를 즉시 다운받도록 투명/숨김 텍스트 배치 -->
<div style="font-family: 'Noto Sans Khmer'; font-weight: 700; position: absolute; width: 0; height: 0; overflow: hidden;">
    Preload Noto Sans Khmer Bold
</div>
""", unsafe_allow_html=True)

# 💡 [TTS 선택 UI: 간격을 최대한 좁힌 다중 선택 가로형 체크박스]
st.markdown("🗣️ **음성 종류를 설정하세요:**")
# 컬럼 비율 조정: 두 번째 열의 폭을 줄여 'Edge 여성' 문구가 앞쪽으로 당겨지도록 조정했습니다. (1.5 -> 1.2)
col_v1, col_v2, col_v3, _ = st.columns([0.8, 1.2, 1.2, 2.8])

with col_v1:
    use_google = st.checkbox("Google (여성)", value=True)
with col_v2:
    use_edge_m = st.checkbox("Edge 남성 (Piseth Neural)")
with col_v3:
    use_edge_f = st.checkbox("Edge 여성 (Sreymom Neural)")

voice_options = []
if use_google: voice_options.append("Google (여성)")
if use_edge_m: voice_options.append("Edge 남성 (Piseth Neural)")
if use_edge_f: voice_options.append("Edge 여성 (Sreymom Neural)")

if not voice_options:
    st.warning("⚠️ 재생할 목소리를 최소 1개 이상 체크해 주세요.")

# 여백을 제거한 커스텀 구분선
st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# 💡 [속도 조절 UI: TTS 선택과 디자인을 통일한 가로형 라디오 버튼]
st.markdown("🐢 **음성 재생 속도를 설정하세요:**")
speed_choice = st.radio(
    "속도 선택",
    options=["아주 느리게 (0.6x)", "조금 느리게 (0.8x)", "보통 속도 (1.0x)"],
    index=2, # 기본값: 보통 속도
    horizontal=True,
    label_visibility="collapsed"
)

# 선택된 속도에 따른 엔진 파라미터 매핑
if speed_choice == "아주 느리게 (0.6x)":
    final_edge_rate_str = "-40%"
    final_gtts_slow = True
elif speed_choice == "조금 느리게 (0.8x)":
    final_edge_rate_str = "-20%"
    final_gtts_slow = False
else:
    final_edge_rate_str = "+0%"
    final_gtts_slow = False

final_speed_level_desc = speed_choice

# Google TTS 제한 안내 메시지
if use_google and final_speed_level_desc == "조금 느리게 (0.8x)":
    st.caption("💡 [알림] Google TTS는 기술적 제약으로 '조금 느리게(0.8x)'를 지원하지 않아 이 단계에서는 보통 속도(1.0x)로 재생됩니다.")
elif use_google and final_speed_level_desc == "아주 느리게 (0.6x)":
    st.caption("💡 [알림] Google TTS는 기술적 제약으로 '아주 느리게(0.6x)'를 지원하지 않아 이 단계에서는 0.5배속(slow 모드)으로 재생됩니다.")

# 여백을 제거한 커스텀 구분선
st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# 엑셀 파일 탐색
EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

if not EXCEL_FILE:
    st.error("❌ 엑셀 파일이 없습니다.")
    st.stop()

# 메모리 격리 파일 로드
@st.cache_data
def load_all_data(filepath):
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    
    excel_data = io.BytesIO(file_bytes)
    xl = pd.ExcelFile(excel_data, engine='openpyxl')
    sheet_names = xl.sheet_names
    
    sheets_dict = {}
    for sheet in sheet_names:
        sheets_dict[sheet] = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=None, engine='openpyxl')
        
    return sheet_names, sheets_dict

try:
    sheet_names, all_sheets = load_all_data(EXCEL_FILE)
except Exception as e:
    st.error(f"❌ 데이터 로드 중 오류: {e}")
    st.stop()

selected_sheet = st.selectbox("📂 학습할 단어장 시트:", sheet_names)

def process_sheet_data(df_raw):
    start_row = 0
    for i in range(min(15, len(df_raw))):
        val = str(df_raw.iloc[i, 0]).strip()
        if val.isdigit() or val == '번호' or 'no' in val.lower():
            start_row = i if val.isdigit() else i + 1
            break
            
    df = df_raw.iloc[start_row:].reset_index(drop=True)
    num_cols = df.shape[1]
    
    # 💡 [핵심] 2번째 열(크메르어 다음 열)이 URL 열인지 동적 탐지
    is_url_col = False
    if num_cols > 2:
        # 2번 열 전체 데이터 중 'http', 'www', 'youtu' 등의 링크가 포함되어 있는지 검사
        col2_text = df_raw.iloc[:, 2].astype(str).str.lower()
        if col2_text.str.contains('http|www\.|youtu', na=False).any():
            is_url_col = True
            
    # URL 열 유무에 따라 발음, 한국어, 영어 데이터가 있는 열(Column) 인덱스를 동적으로 조정
    idx_pron = 3 if is_url_col else 2
    idx_kor = 4 if is_url_col else 3
    idx_eng = 5 if is_url_col else 4
    
    df['번호'] = df.iloc[:, 0].astype(str) if num_cols > 0 else ""
    df['원문'] = df.iloc[:, 1].astype(str) if num_cols > 1 else ""
    df['발음'] = df.iloc[:, idx_pron].astype(str) if num_cols > idx_pron else ""
    df['한국어'] = df.iloc[:, idx_kor].astype(str) if num_cols > idx_kor else ""
    df['영어'] = df.iloc[:, idx_eng].astype(str) if num_cols > idx_eng else ""
    
    def clean_text(text):
        t = str(text).strip()
        if t.lower() in ['nan', 'none', 'nat', '']: return ""
        if t.endswith('.0'): return t[:-2]
        return t
        
    for c in ['번호', '원문', '발음', '한국어', '영어']:
        df[c] = df[c].apply(clean_text)
    
    df = df[df['원문'] != '']

    def combine_meanings(row):
        parts = []
        if row['한국어']: parts.append(row['한국어'])
        if row['영어']: parts.append(row['영어'])
        return " / ".join(parts) if parts else ""
        
    df['해석'] = df.apply(combine_meanings, axis=1)

    # 한글과 영문을 분리하여 출력하기 위해 컬럼에 각각 추가 유지
    sub_df = df[['번호', '원문', '발음', '해석', '한국어', '영어']]
    sub_df.columns = ['번호', '캄보디아어', '발음', '해석', '한국어', '영어']
    return sub_df

processed_df = process_sheet_data(all_sheets[selected_sheet])

# Edge TTS 비동기 처리 엔진
def get_edge_audio_sync(text, voice_model, rate_str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _generate():
        communicate = edge_tts.Communicate(text, voice_model, rate=rate_str)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
        
    result = loop.run_until_complete(_generate())
    loop.close()
    return result

# 다중 오디오 동시 생성 캐시 엔진
@st.cache_data(show_spinner=False)
def generate_multiple_audios(khmer_text, selected_options, edge_rate, gtts_slow):
    audio_results = []
    error_messages = []
    
    for opt in selected_options:
        if "Edge" in opt:
            try:
                voice_model = "km-KH-PisethNeural" if "남성" in opt else "km-KH-SreymomNeural"
                audio_content = get_edge_audio_sync(khmer_text, voice_model, edge_rate)
                audio_results.append(audio_content)
            except Exception as e:
                error_messages.append(f"Edge TTS ({opt}) 에러: {str(e)}")
        else:
            try:
                from gtts import gTTS
                tts = gTTS(text=khmer_text, lang='km', slow=gtts_slow)
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                audio_results.append(fp.getvalue())
            except Exception as e:
                error_messages.append(f"Google TTS 에러: {str(e)}")
                
    return audio_results, error_messages

# HTML/JS 커스텀 순차 재생 플레이어
def play_sequential_audio(audio_bytes_list, speed_desc):
    if not audio_bytes_list:
        return

    b64_audios = []
    for ab in audio_bytes_list:
        b64 = base64.b64encode(ab).decode()
        b64_audios.append(f"data:audio/mp3;base64,{b64}")

    js_array = str(b64_audios).replace("'", '"')

    # 💡 [SyntaxError 완벽 해결] 파이썬의 f-string (f""") 기능을 해제하고, .replace()를 사용해 안전하게 변수를 주입했습니다.
    html_code = """
    <div style="background-color: #f0f2f6; padding: 5px 10px; border-radius: 8px;">
        <audio id="sequentialPlayer" controls autoplay style="width: 100%; height: 35px; outline: none;"></audio>
        <div id="statusText" style="text-align: center; font-family: sans-serif; font-size: 13px; color: #d9534f; font-weight: bold;"></div>
    </div>
    <script>
        var audios = __JS_ARRAY__;
        var currentIdx = 0;
        var player = document.getElementById("sequentialPlayer");
        var status = document.getElementById("statusText");

        function updateStatus() {
            status.innerText = "";
        }

        if(audios.length > 0) {
            player.src = audios[0];
            updateStatus();
            
            var playPromise = player.play();
            if (playPromise !== undefined) {
                playPromise.catch(function(error) {
                    status.style.marginTop = "5px";
                    status.innerText = "⏸️ 스마트폰 보안 차단: 위 재생(▶) 버튼을 수동으로 눌러주세요.";
                });
            }

            player.onended = function() {
                currentIdx++;
                if(currentIdx < audios.length) {
                    player.src = audios[currentIdx];
                    updateStatus();
                    player.play();
                } else {
                    status.innerText = "";
                }
            };
        }
    </script>
    """.replace("__JS_ARRAY__", js_array)
    
    components.html(html_code, height=60)

if processed_df is not None:
    search_query = st.text_input("🔍 검색어 입력:", "")
    
    if search_query:
        filtered_df = processed_df[
            processed_df['번호'].str.contains(search_query, na=False) |
            processed_df['캄보디아어'].str.contains(search_query, na=False) | 
            processed_df['발음'].str.contains(search_query, na=False) |
            processed_df['해석'].str.contains(search_query, na=False)
        ].reset_index(drop=True)
    else:
        filtered_df = processed_df.reset_index(drop=True)

    # 💡 [핵심 UI 개선] 플레이어와 단어 정보가 표 아래로 밀리지 않도록 상단 고정 컨테이너 생성
    player_container = st.container()
    
    # 여백을 제거한 커스텀 구분선
    st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)
    st.caption(f"총 {len(filtered_df)}개의 항목 (아래 표에서 원하는 행을 터치하세요)")

    # 💡 무력화되는 Pandas Styler를 삭제하고, 깔끔하게 원본 DataFrame을 렌더링합니다.
    display_df = filtered_df.drop(columns=['한국어', '영어'])
    
    selection = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    selected_rows = []
    if hasattr(selection, "selection"):
        selected_rows = selection.selection.rows
    elif isinstance(selection, dict):
        selected_rows = selection.get("selection", {}).get("rows", [])

    # 선택 결과가 있으면 최상단 player_container에 UI를 출력합니다.
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_num = filtered_df.iloc[selected_idx]['번호']
        selected_word = filtered_df.iloc[selected_idx]['캄보디아어']
        selected_pron = filtered_df.iloc[selected_idx]['발음']
        selected_kor = filtered_df.iloc[selected_idx]['한국어']
        selected_eng = filtered_df.iloc[selected_idx]['영어']
        
        with player_container:
            num_str = f"[{selected_num}] " if selected_num else ""
            
            # 선택된 영역의 폰트 속성 적용 HTML
            st.markdown(f"""
            <div style="padding: 1rem; border-radius: 0.5rem; background-color: #d1e7dd; border: 1px solid #badbcc; margin-bottom: 1rem;">
                <span class="khmer-custom-font" style="color: #0f5132;">{num_str}{selected_word}</span>
            </div>
            """, unsafe_allow_html=True)

            # 한글/영문 색상 분리
            colored_mean_parts = []
            if selected_kor: colored_mean_parts.append(f":green[{selected_kor}]")
            if selected_eng: colored_mean_parts.append(f":orange[{selected_eng}]")
            
            colored_mean = " ".join(colored_mean_parts)
            pron_str = f"{selected_pron} " if selected_pron else ""
            st.info(f"💡 {pron_str}{colored_mean}")

            if voice_options:
                with st.spinner(f"🎵 선택하신 {len(voice_options)}개의 고품질 음성(배속: {final_speed_level_desc})을 동시 준비 중입니다..."):
                    audio_datas, error_msgs = generate_multiple_audios(selected_word, voice_options, final_edge_rate_str, final_gtts_slow)
                
                for err in error_msgs:
                    st.error(err)
                
                if audio_datas:
                    play_sequential_audio(audio_datas, final_speed_level_desc)
