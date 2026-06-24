import streamlit as st
import pandas as pd
import io
import os
import asyncio
import edge_tts
import base64
import streamlit.components.v1 as components
import time

# 1. 화면 설정
st.set_page_config(page_title="크메르어 학습기", page_icon="🎧", layout="wide")

# 💡 [크기 조정] st.title() 보다 한 단계 글씨가 작은 st.header()로 변경하여 상단 제목 크기를 약간 줄였습니다.
st.header("🎧 크메르어 학습기")

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

/* 선택된 텍스트 영역 커스텀: 💡 폰트 크기 15pt -> 20pt 로 재변경 */
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

# 💡 [상태 관리] 연속 재생을 위한 Session State 초기화
if "is_continuous_playing" not in st.session_state:
    st.session_state.is_continuous_playing = False
if "current_play_idx" not in st.session_state:
    st.session_state.current_play_idx = 0

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

# 💡 [공간 최적화] 단어장 시트 선택과 검색어 입력을 한 줄(2개의 컬럼)에 나란히 배치했습니다.
col_sheet_select, col_search_input = st.columns(2)

with col_sheet_select:
    selected_sheet = st.selectbox("📂 학습할 단어장 시트:", sheet_names)

with col_search_input:
    search_query = st.text_input("🔍 검색어 입력:", "")

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

# HTML/JS 커스텀 순차 재생 플레이어 (단일/연속 통합용)
def play_sequential_audio(audio_bytes_list, is_continuous=False):
    if not audio_bytes_list:
        return

    b64_audios = []
    for ab in audio_bytes_list:
        b64 = base64.b64encode(ab).decode()
        b64_audios.append(f"data:audio/mp3;base64,{b64}")

    js_array = str(b64_audios).replace("'", '"')
    
    # 💡 [기능 추가] 연속 재생 모드일 경우 버튼 텍스트와 색상을 변경
    btn_text = "🔊 연속 재생중" if is_continuous else "🔊 재생중"
    btn_color = "#084298" if is_continuous else "#0f5132" # 연속재생은 짙은 파란색
    
    # 💡 [위치 겹침 완벽 해결] 스트림릿 표의 우측 상단 UI 아이콘을 피하기 위해 margin-right를 130px로 확대했습니다.
    html_code = f"""
    <div id="playerBox" style="display: flex; justify-content: flex-end; align-items: center; width: 100%; cursor: pointer; user-select: none;">
        <audio id="sequentialPlayer" autoplay style="display: none;"></audio>
        
        <!-- 오른쪽: 스트림릿 UI 겹침 방지를 위해 마진 부여. 버튼 하나만 남기기 위해 여백 조정 -->
        <div id="playBtn" style="font-family: 'Noto Sans Khmer', sans-serif; font-size: 14px; font-weight: bold; color: white; background-color: #198754; padding: 8px 16px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); transition: all 0.2s; white-space: nowrap; margin-right: 130px; margin-bottom: 5px;">
            ▶️ 재생
        </div>
    </div>
    <script>
        var audios = {js_array};
        var currentIdx = 0;
        var player = document.getElementById("sequentialPlayer");
        var box = document.getElementById("playerBox");
        var playBtn = document.getElementById("playBtn");
        var isContinuous = {'true' if is_continuous else 'false'};

        function updateStatus() {{
            playBtn.innerText = "{btn_text}";
            playBtn.style.backgroundColor = "{btn_color}"; 
        }}

        // 터치 시 강제로 재생 (스마트폰 보안 차단 해제용)
        box.onclick = function() {{
            player.play();
        }};

        if(audios.length > 0) {{
            player.src = audios[0];
            updateStatus();
            
            var playPromise = player.play();
            if (playPromise !== undefined) {{
                playPromise.catch(function(error) {{
                    playBtn.innerText = "⏸️ 터치하여 재생 시작";
                    playBtn.style.backgroundColor = "#dc3545"; // 빨간색 (모바일 차단 알림)
                }});
            }}

            player.onended = function() {{
                currentIdx++;
                if(currentIdx < audios.length) {{
                    player.src = audios[currentIdx];
                    updateStatus();
                    player.play();
                }} else {{
                    if (isContinuous) {{
                        // 연속 재생일 때는 완료 메시지 없이 백그라운드 파이썬으로 처리를 넘김
                        playBtn.innerText = "⏳ 다음 단어 준비중...";
                        playBtn.style.backgroundColor = "#6c757d";
                        // 스트림릿과 통신하기 위해 임시 버튼 클릭 흉내 (실제로는 python loop가 처리)
                    }} else {{
                        playBtn.innerText = "▶️ 재생"; 
                        playBtn.style.backgroundColor = "#0d6efd"; // 파란색 (완료)
                    }}
                }}
            }};
        }}
    </script>
    """
    
    # 컴포넌트 높이를 버튼 크기에 딱 맞추어 낭비되는 세로 여백을 원천 차단
    components.html(html_code, height=45)

if processed_df is not None:
    # 검색어 입력과 시트 선택은 상단에 이미 배치되었으므로 필터링 로직만 수행합니다.
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
    st.markdown("<hr style='margin-top: 0px; margin-bottom: 10px;'>", unsafe_allow_html=True)
    
    # 💡 [레이아웃 혁신] 안내 문구와 우측 재생/연속 버튼을 한 줄에 배치
    col_caption, col_btn_cont, col_btn_play = st.columns([0.65, 0.15, 0.2])
    
    with col_caption:
        # 버튼과 수평(높이)이 맞도록 padding-top을 살짝 추가
        st.markdown(f"<div style='padding-top: 8px; font-size: 14px; color: gray;'>총 {len(filtered_df)}개의 항목 (아래 표에서 원하는 행을 터치하세요)</div>", unsafe_allow_html=True)
        
    # 플레이어가 삽입될 빈 공간 (이제 사용 안 함, Python st.audio 스트리밍으로 대체)
    # player_placeholder = col_player.empty()

    # 무력화되는 Pandas Styler를 삭제하고, 깔끔하게 원본 DataFrame을 렌더링합니다.
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

    # 💡 [연속 재생 로직 컨트롤]
    # 사용자가 표에서 새 항목을 터치하면 연속재생 모드 중지 및 해당 인덱스로 초기화
    if selected_rows:
        if st.session_state.current_play_idx != selected_rows[0]:
            st.session_state.is_continuous_playing = False
            st.session_state.current_play_idx = selected_rows[0]
            
    # 아무것도 선택되지 않았을 때는 0번 인덱스 대기
    elif not st.session_state.is_continuous_playing:
        st.session_state.current_play_idx = 0

    # 현재 처리할 데이터 인덱스 확보
    target_idx = st.session_state.current_play_idx
    
    audio_datas = [] # 💡 안전장치: 에러 방지를 위한 변수 초기화

    # 선택된 행이 있거나, 연속 재생 중일 때 상단 컨테이너에 단어 정보를 출력
    if selected_rows or st.session_state.is_continuous_playing:
        # 데이터 유효성 검사
        if target_idx < len(filtered_df):
            selected_num = filtered_df.iloc[target_idx]['번호']
            selected_word = filtered_df.iloc[target_idx]['캄보디아어']
            selected_pron = filtered_df.iloc[target_idx]['발음']
            selected_kor = filtered_df.iloc[target_idx]['한국어']
            selected_eng = filtered_df.iloc[target_idx]['영어']
            
            with player_container:
                # 💡 [버튼 배치] '연속' 버튼과 '단일 재생' 컨트롤 영역을 상단 컨테이너 우측에 배치
                c1, c2, c3 = st.columns([0.65, 0.15, 0.2])
                with c2:
                    if st.button("⏹️ 중지" if st.session_state.is_continuous_playing else "🔁 연속", use_container_width=True):
                        st.session_state.is_continuous_playing = not st.session_state.is_continuous_playing
                        st.rerun()
                
                with c3:
                    # 단일 재생 버튼 트리거용 빈 공간 (실제 UI는 custom HTML이 그림)
                    btn_placeholder = st.empty()
            
                num_str = f"[{selected_num}] " if selected_num else ""
                pron_str = f"{selected_pron} " if selected_pron else ""
                
                # 💡 [여백 100% 완벽 제어] 아래의 숫자를 6px, 10px, 24px 등 원하시는 대로 수정하시면 즉시 확실하게 반응합니다!
                box_padding = "6px 14px"
                
                # 💡 한글/영문 해석에도 15pt 폰트 사이즈를 일괄 적용했습니다.
                kor_html = f"<span style='color: #20c997; font-size: 15pt; font-weight: bold;'>{selected_kor}</span>" if selected_kor else ""
                eng_html = f"<span style='color: #fd7e14; font-size: 15pt; font-weight: bold;'>{selected_eng}</span>" if selected_eng else ""
                colored_mean = " ".join(filter(None, [kor_html, eng_html]))

                # 💡 [마크다운 들여쓰기 버그 완벽 해결]
                html_combined_display = f"""<div style="display: flex; flex-direction: column; gap: 6px; margin-bottom: 0px;">
        <!-- 1. 크메르어 원문 박스 -->
        <div style="padding: {box_padding}; border-radius: 0.5rem; background-color: #d1e7dd; border: 1px solid #badbcc;">
            <span class="khmer-custom-font" style="color: #0f5132;">{num_str}{selected_word}</span>
        </div>
        <!-- 2. 발음 및 해석 박스 (기존 st.info 완전 대체, 💡아이콘 제거 완료) -->
        <div style="padding: {box_padding}; border-radius: 0.5rem; background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); font-size: 14px; color: inherit; display: flex; align-items: flex-start; gap: 8px;">
            <div style="line-height: 1.5; padding-top: 1px;">
                <span style="color: #3b82f6; font-size: 15pt; font-weight: bold;">{pron_str}</span> {colored_mean}
            </div>
        </div>
    </div>"""
                
                st.markdown(html_combined_display, unsafe_allow_html=True)

                if voice_options:
                    # 연속 재생 중일 때는 spinner를 조용하게 띄우거나 생략
                    if not st.session_state.is_continuous_playing:
                        with st.spinner(f"🎵 음성 준비 중..."):
                            audio_datas, error_msgs = generate_multiple_audios(selected_word, voice_options, final_edge_rate_str, final_gtts_slow)
                    else:
                        audio_datas, error_msgs = generate_multiple_audios(selected_word, voice_options, final_edge_rate_str, final_gtts_slow)

                    for err in error_msgs:
                        st.error(err)

            # 💡 [핵심] 오디오 재생 제어
            if audio_datas:
                # 단일 모드일 경우 기존의 커스텀 HTML 플레이어를 버튼 위치에 그림
                if not st.session_state.is_continuous_playing:
                    with btn_placeholder:
                        play_sequential_audio(audio_datas, is_continuous=False)
                
                # 연속 모드일 경우, 스트림릿 내장 st.audio(autoplay=True)를 순차적으로 백그라운드 렌더링
                elif st.session_state.is_continuous_playing:
                    with btn_placeholder:
                        st.markdown("<div style='text-align: right; padding-right: 130px; font-weight: bold; color: #084298;'>🔁 연속 재생중...</div>", unsafe_allow_html=True)
                        
                    # 연속 생성된 오디오들을 순서대로 플레이
                    for ad in audio_datas:
                        # 화면에는 안 보이게 1픽셀짜리 audio 태그 렌더링 (꼼수)
                        b64 = base64.b64encode(ad).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}"></audio>', unsafe_allow_html=True)
                        
                        # 다음 오디오가 겹쳐서 나오지 않도록 재생 길이만큼 파이썬 스레드 대기
                        # 임시로 오디오 길이를 예측(단어 길이 비례)하여 딜레이 부여. 
                        # 완벽한 딜레이를 위해선 librosa 등이 필요하나 클라우드 환경 제약 상 보수적 시간 부여
                        estimated_length = max(1.5, len(selected_word) * 0.15) 
                        time.sleep(estimated_length)
                    
                    # 현재 오디오 리스트 플레이가 끝나면, 다음 인덱스로 이동 후 자동 리런
                    if target_idx + 1 < len(filtered_df):
                        st.session_state.current_play_idx += 1
                        time.sleep(0.5) # 단어 사이 짧은 휴식
                        st.rerun()
                    else:
                        st.success("🎉 단어장의 끝에 도달했습니다!")
                        st.session_state.is_continuous_playing = False
        else:
            st.session_state.is_continuous_playing = False
