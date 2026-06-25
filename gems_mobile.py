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

# 💡 [상태 관리] 연속 재생 및 행 선택 초기화
if "is_continuous_playing" not in st.session_state:
    st.session_state.is_continuous_playing = False
if "current_play_idx" not in st.session_state:
    st.session_state.current_play_idx = 0
if "last_clicked_row" not in st.session_state:
    st.session_state.last_clicked_row = None # 터치 강제 롤백 방지용 상태 추가

# 💡 [TTS 선택 UI: 간격을 최대한 좁힌 다중 선택 가로형 체크박스]
st.markdown("🗣️ **음성 종류를 설정하세요:**")
# 컬럼 비율 조정: 두 번째 열의 폭을 줄여 'Edge 여성' 문구가 앞쪽으로 당겨지도록 조정했습니다.
col_v1, col_v2, col_v3, _ = st.columns([1.0, 1.2, 1.2, 2.6])

with col_v1:
    use_google = st.checkbox("Google (여성)", value=True)
with col_v2:
    use_edge_m = st.checkbox("MS Edge (남성)")
with col_v3:
    use_edge_f = st.checkbox("MS Edge (여성)")

voice_options = []
if use_google: voice_options.append("Google (여성)")
if use_edge_m: voice_options.append("MS Edge (남성)")
if use_edge_f: voice_options.append("MS Edge (여성)")

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

# 💡 [캐시 최적화] 엑셀 파일의 '마지막 수정 시간'을 추적하여, 
# 시트 순서 변경 등 파일이 덮어씌워질 때마다 즉시 새로운 데이터를 메모리에 반영합니다.
@st.cache_data
def load_all_data(filepath, last_modified):
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
    # 엑셀 파일의 실제 수정 시간(타임스탬프)을 가져와 캐시 함수에 전달합니다.
    file_modified_time = os.path.getmtime(EXCEL_FILE)
    sheet_names, all_sheets = load_all_data(EXCEL_FILE, file_modified_time)
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
    
    is_url_col = False
    if num_cols > 2:
        col2_text = df_raw.iloc[:, 2].astype(str).str.lower()
        if col2_text.str.contains('http|www\.|youtu', na=False).any():
            is_url_col = True
            
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

# 💡 [모바일 완벽 호환 버튼 통합 시스템] 연속 재생 버튼과 일반 재생 버튼을 하나로 묶었습니다.
def play_sequential_audio(audio_bytes_list, is_continuous=False):
    b64_audios = []
    if audio_bytes_list:
        for ab in audio_bytes_list:
            b64 = base64.b64encode(ab).decode()
            b64_audios.append(f"data:audio/mp3;base64,{b64}")

    js_array = str(b64_audios).replace("'", '"')
    
    # 상태별 텍스트 및 컬러 정의
    btn_text = "🔊 연속 재생중" if is_continuous else "🔊 재생중"
    btn_color = "#198754"
    
    cont_text = "⏹️ 중지" if is_continuous else "⏭️ 연속"
    cont_color = "#dc3545" if is_continuous else "#212529"
    
    # 💡 [디자인 완벽 일치] 두 버튼이 절대 떨어지지 않고 모바일에서도 밀리지 않게 Flexbox로 고정결합 (gap: 8px)
    html_code = f"""
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
        }}
        #btnContainer {{
            display: flex;
            gap: 8px; /* 버튼 사이의 간격을 좁게 고정 */
            justify-content: flex-start; /* 좌측으로 바짝 밀착 */
            align-items: center;
            width: 100%;
        }}
        .custom-btn {{
            font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 16px;
            color: #ffffff;
            padding: 0 14px;
            height: 38.4px; /* 스트림릿 네이티브 버튼과 동일한 높이 */
            display: inline-flex;
            justify-content: center;
            align-items: center;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: filter 0.2s ease, transform 0.1s;
            box-sizing: border-box;
            user-select: none;
            line-height: 1;
            white-space: nowrap; /* 💡 스마트폰에서 글씨가 아래로 밀리는 현상 완벽 방지 */
            border: 1px solid transparent;
        }}
        .custom-btn:hover {{
            filter: brightness(0.85); 
        }}
        .custom-btn:active {{
            transform: scale(0.98);
        }}
        #contBtn {{
            background-color: {cont_color};
            border-color: {cont_color};
        }}
        #playBtn {{
            background-color: {btn_color};
            border-color: {btn_color};
        }}
    </style>

    <div id="btnContainer">
        <audio id="sequentialPlayer" autoplay style="display: none;"></audio>
        <div id="contBtn" class="custom-btn">{cont_text}</div>
        <div id="playBtn" class="custom-btn">{btn_text}</div>
    </div>
    
    <script>
        var audios = {js_array};
        var currentIdx = 0;
        var player = document.getElementById("sequentialPlayer");
        var playBtn = document.getElementById("playBtn");
        var contBtn = document.getElementById("contBtn");
        var isContinuous = {'true' if is_continuous else 'false'};

        // 💡 연속 재생 스위치를 숨겨진 파이썬 버튼과 연동
        contBtn.onclick = function() {{
            var buttons = window.parent.document.querySelectorAll('button');
            for(var i=0; i<buttons.length; i++) {{
                if(buttons[i].innerText.trim() === 'TOGGLE_CONT_BTN_XYZ') {{
                    buttons[i].click();
                    break;
                }}
            }}
        }};

        function updateStatus() {{
            playBtn.innerText = "{btn_text}";
            playBtn.style.backgroundColor = "{btn_color}"; 
            playBtn.style.borderColor = "{btn_color}"; 
        }}

        // 오디오가 있을 때만 재생 로직 활성화
        if(audios.length > 0) {{
            playBtn.onclick = function() {{
                if (player.paused) player.play();
            }};

            player.src = audios[0];
            updateStatus();
            
            var playPromise = player.play();
            if (playPromise !== undefined) {{
                playPromise.catch(function(error) {{
                    playBtn.innerText = "⏸️ 터치하여 시작";
                    playBtn.style.backgroundColor = "#dc3545"; 
                    playBtn.style.borderColor = "#dc3545";
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
                        playBtn.innerText = "⏳ 다음 단어...";
                        playBtn.style.backgroundColor = "#6c757d";
                        playBtn.style.borderColor = "#6c757d";
                        
                        var buttons = window.parent.document.querySelectorAll('button');
                        for(var i=0; i<buttons.length; i++) {{
                            if(buttons[i].innerText.trim() === 'AUTO_NEXT_BTN_XYZ') {{
                                buttons[i].click();
                                break;
                            }}
                        }}
                    }} else {{
                        playBtn.innerText = "▶️ 재생"; 
                        playBtn.style.backgroundColor = "#0d6efd"; 
                        playBtn.style.borderColor = "#0d6efd";
                    }}
                }}
            }};
        }} else {{
            // 오디오가 없는 경우 예외 처리
            playBtn.innerText = "⚠️ 음성 없음";
            playBtn.style.backgroundColor = "#6c757d";
            playBtn.style.borderColor = "#6c757d";
            playBtn.style.cursor = "not-allowed";
        }}
    </script>
    """
    
    components.html(html_code, height=40)

if processed_df is not None:
    if search_query:
        filtered_df = processed_df[
            processed_df['번호'].str.contains(search_query, na=False) |
            processed_df['캄보디아어'].str.contains(search_query, na=False) | 
            processed_df['발음'].str.contains(search_query, na=False) |
            processed_df['해석'].str.contains(search_query, na=False)
        ].reset_index(drop=True)
    else:
        filtered_df = processed_df.reset_index(drop=True)

    # 💡 [표 선택 값 선행 동기화]
    if "word_table" in st.session_state:
        sel = st.session_state.word_table
        sel_rows = []
        if hasattr(sel, "selection"):
            sel_rows = sel.selection.rows
        elif isinstance(sel, dict):
            sel_rows = sel.get("selection", {}).get("rows", [])
            
        if sel_rows:
            current_selection = sel_rows[0]
            if current_selection != st.session_state.last_clicked_row:
                st.session_state.last_clicked_row = current_selection
                st.session_state.is_continuous_playing = False
                st.session_state.current_play_idx = current_selection
        elif not st.session_state.is_continuous_playing:
            st.session_state.current_play_idx = 0
            st.session_state.last_clicked_row = None

    target_idx = st.session_state.current_play_idx

    # =================================================================================
    # 💡 [구조 혁신: Layout Shift 원천 차단 (표 튐 버그 완벽 해결)]
    # 이전 방식은 표를 먼저 그리고 빈공간을 예약한 뒤, 나중에 버튼을 쑤셔 넣는 방식이었습니다.
    # 이제는 모든 내부 데이터 처리(오디오 생성)를 백그라운드에서 먼저 끝마친 후, 
    # 눈에 보이는 UI를 "단어 박스 ➡️ 버튼 ➡️ 하단 표"의 정순서로 차곡차곡 위에서부터 아래로 한 번에 찍어냅니다.
    # =================================================================================
    
    audio_datas = []
    
    # 1. 렌더링 전 오디오 데이터 및 단어 정보 사전 준비 (블로킹)
    if st.session_state.is_continuous_playing or (0 <= target_idx < len(filtered_df)):
        if target_idx < len(filtered_df):
            selected_num = filtered_df.iloc[target_idx]['번호']
            selected_word = filtered_df.iloc[target_idx]['캄보디아어']
            selected_pron = filtered_df.iloc[target_idx]['발음']
            selected_kor = filtered_df.iloc[target_idx]['한국어']
            selected_eng = filtered_df.iloc[target_idx]['영어']

            if voice_options:
                audio_datas, error_msgs = generate_multiple_audios(selected_word, voice_options, final_edge_rate_str, final_gtts_slow)
                for err in error_msgs:
                    st.error(err)

            # 2. 가장 최상단: 단어 정보 박스 출력 (순차적 렌더링 시작)
            num_str = f"[{selected_num}] " if selected_num else ""
            pron_str = f"{selected_pron} " if selected_pron else ""
            box_padding = "6px 14px"
            kor_html = f"<span style='color: #20c997; font-size: 15pt; font-weight: bold;'>{selected_kor}</span>" if selected_kor else ""
            eng_html = f"<span style='color: #fd7e14; font-size: 15pt; font-weight: bold;'>{selected_eng}</span>" if selected_eng else ""
            colored_mean = " ".join(filter(None, [kor_html, eng_html]))

            html_combined_display = f"""<div style="display: flex; flex-direction: column; gap: 6px; margin-bottom: 0px;">
                <div style="padding: {box_padding}; border-radius: 0.5rem; background-color: #d1e7dd; border: 1px solid #badbcc;">
                    <span class="khmer-custom-font" style="color: #0f5132;">{num_str}{selected_word}</span>
                </div>
                <div style="padding: {box_padding}; border-radius: 0.5rem; background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); font-size: 14px; color: inherit; display: flex; align-items: flex-start; gap: 8px;">
                    <div style="line-height: 1.5; padding-top: 1px;">
                        <span style="color: #3b82f6; font-size: 15pt; font-weight: bold;">{pron_str}</span> {colored_mean}
                    </div>
                </div>
            </div>"""
            st.markdown(html_combined_display, unsafe_allow_html=True)

            # 3. 중간 영역: 구분선, 캡션, 그리고 오디오 버튼 출력
            st.markdown("<hr style='margin-top: 10px; margin-bottom: 10px;'>", unsafe_allow_html=True)
            col_caption, col_buttons = st.columns([0.65, 0.35])
            
            with col_caption:
                st.markdown(f"<div style='padding-top: 8px; font-size: 14px; color: gray;'>총 {len(filtered_df)}개의 항목 (아래 표에서 원하는 행을 터치하세요)</div>", unsafe_allow_html=True)
                
            with col_buttons:
                # 중간에 비는 공간 없이 순서대로 바로 렌더링됩니다.
                play_sequential_audio(audio_datas, is_continuous=st.session_state.is_continuous_playing)
    else:
        # 단어장 끝 도달 시 기본 UI 렌더링
        st.session_state.is_continuous_playing = False
        st.markdown("<hr style='margin-top: 10px; margin-bottom: 10px;'>", unsafe_allow_html=True)
        st.markdown(f"<div style='padding-top: 8px; font-size: 14px; color: gray;'>총 {len(filtered_df)}개의 항목 (아래 표에서 원하는 행을 터치하세요)</div>", unsafe_allow_html=True)

    # 4. 가장 하단: 데이터프레임(표) 출력
    # 위에 있는 버튼과 텍스트 박스들이 자리를 모두 잡은 뒤, 마지막에 표를 그리기 때문에 화면이 절대 튀지 않습니다!
    display_df = filtered_df.drop(columns=['한국어', '영어']).copy()
    
    def highlight_playing_row(row):
        if row.name == target_idx:
            return ['background-color: rgba(25, 135, 84, 0.25);'] * len(row)
        return [''] * len(row)

    styled_df = display_df.style.apply(highlight_playing_row, axis=1)

    selection = st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="word_table"
    )

# 💡 [보이지 않는 자동 스위치 로직]
if st.button("AUTO_NEXT_BTN_XYZ", key="auto_next"):
    if st.session_state.current_play_idx + 1 < len(filtered_df):
        st.session_state.current_play_idx += 1
        st.rerun()
    else:
        st.success("🎉 단어장의 끝에 도달했습니다!")
        st.session_state.is_continuous_playing = False
        st.rerun()

# 💡 [보이지 않는 연속 재생 토글 스위치 (HTML에서 눌러줌)]
if st.button("TOGGLE_CONT_BTN_XYZ", key="toggle_cont"):
    st.session_state.is_continuous_playing = not st.session_state.is_continuous_playing
    st.rerun()

components.html("""
<script>
var buttons = window.parent.document.querySelectorAll('button');
buttons.forEach(function(btn) {
    if(btn.innerText.trim() === 'AUTO_NEXT_BTN_XYZ' || btn.innerText.trim() === 'TOGGLE_CONT_BTN_XYZ') {
        btn.style.display = 'none';
    }
});
</script>
""", height=0)
