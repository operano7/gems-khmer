import streamlit as st
import pandas as pd
import io
import os
import asyncio
import edge_tts
import base64
import streamlit.components.v1 as components

# 1. 화면 설정
st.set_page_config(page_title="GEMS Mobile 캄보디아어 학습기", page_icon="🔊", layout="wide")
st.title("🇰🇭 GEMS 모바일 캄보디아어 학습기 (공통 배속 지원)")

# 💡 [UI 최적화 및 팩트 기반 수정]
# 드롭다운을 폐기하고, 기존처럼 가로로 3등분하여 깔끔하게 배치된 다중 체크박스 도입
st.markdown("🗣️ **발음 목소리 선택:** (여러 개를 체크하면 바통을 넘기듯 순차적으로 재생됩니다)")
col_v1, col_v2, col_v3 = st.columns(3)

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

st.markdown("---")

# 🐢 [신규 업그레이드 및 팩트 수정: 전 TTS 공통 속도 설정]
st.markdown("🐢 **전 TTS 공통 재생 속도를 설정하세요:** (모든 엔진에 공통 적용됩니다)")
col_s1, col_s2, col_s3 = st.columns(3)

# 오미로님 요청에 따른 배속 설명 수정
with col_s1:
    speed_l1 = st.button(" 아주 느리게 (0.6x)")
with col_s2:
    speed_l2 = st.button(" 조금 느리게 (0.8x)")
with col_s3:
    speed_l3 = st.button(" 보통 속도 (1.0x)")

# 💡 [핵심 최적화: 속도 매핑 엔진]
# 마지막으로 클릭한 버튼의 속도 매핑을 세션 메모리에 저장합니다.
if "final_edge_rate_str" not in st.session_state:
    st.session_state.final_edge_rate_str = "+0%"  # 보통 속도 (기본값)
if "final_gtts_slow" not in st.session_state:
    st.session_state.final_gtts_slow = False     # 구글 보통 속도 (기본값)
if "final_speed_level_desc" not in st.session_state:
    st.session_state.final_speed_level_desc = "보통 속도 (1.0x)" # 기본값

if speed_l1:
    st.session_state.final_edge_rate_str = "-40%" # 💡 0.6x (-40%)로 수정
    st.session_state.final_gtts_slow = True      # Google slow 모드 (실제 0.5x)
    st.session_state.final_speed_level_desc = "아주 느리게 (0.6x)"
if speed_l2:
    st.session_state.final_edge_rate_str = "-20%" # 💡 0.8x (-20%)로 수정
    st.session_state.final_gtts_slow = False     # Google은 0.8 지원 안 함. 보통 속도로 대응
    st.session_state.final_speed_level_desc = "조금 느리게 (0.8x)"
if speed_l3:
    st.session_state.final_edge_rate_str = "+0%"  # 1.0x (normal)
    st.session_state.final_gtts_slow = False
    st.session_state.final_speed_level_desc = "보통 속도 (1.0x)"

# 설정 완료 및 Google TTS 제한 안내 팩트 업데이트
final_edge_rate_str = st.session_state.final_edge_rate_str
final_gtts_slow = st.session_state.final_gtts_slow
final_speed_level_desc = st.session_state.final_speed_level_desc

st.markdown(f"✅ **현재 설정된 공통 속도 단계:** {final_speed_level_desc}")

# Google TTS 제한 안내 메시지 팩트 업데이트 (사용자가 구글을 선택했을 때만)
if use_google and final_speed_level_desc == "조금 느리게 (0.8x)":
    st.markdown("💡 [알림] Google TTS는 기술적 제약으로 '조금 느리게(0.8x)'를 지원하지 않아,")
    st.markdown("   이 단계에서는 보통 속도(1.0x)로 재생됩니다.")
elif use_google and final_speed_level_desc == "아주 느리게 (0.6x)":
    st.markdown("💡 [알림] Google TTS는 기술적 제약으로 '아주 느리게(0.6x)'를 지원하지 않아,")
    st.markdown("   이 단계에서는 0.5배속(slow 모드)으로 재생됩니다.")

st.markdown("---")

st.write("표에서 원하는 문장을 터치하면 발음이 재생됩니다.")

# 엑셀 파일 탐색
EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

if not EXCEL_FILE:
    st.error("❌ 엑셀 파일이 없습니다.")
    st.stop()

# 메모리 격리 파일 로드 (BadZipFile 에러 원천 차단)
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

def process_sheet_data(df):
    start_row = 0
    for i in range(min(15, len(df))):
        val = str(df.iloc[i, 0]).strip()
        if val.isdigit() or val == '번호' or 'no' in val.lower():
            start_row = i if val.isdigit() else i + 1
            break
            
    df = df.iloc[start_row:].reset_index(drop=True)
    num_cols = df.shape[1]
    
    # 4단 독립 표 포맷팅
    df['번호'] = df.iloc[:, 0].astype(str) if num_cols > 0 else ""
    df['원문'] = df.iloc[:, 1].astype(str) if num_cols > 1 else ""
    df['발음'] = df.iloc[:, 2].astype(str) if num_cols > 2 else ""
    df['한국어'] = df.iloc[:, 3].astype(str) if num_cols > 3 else ""
    df['영어'] = df.iloc[:, 4].astype(str) if num_cols > 4 else ""
    
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

    sub_df = df[['번호', '원문', '발음', '해석']]
    sub_df.columns = ['번호', '캄보디아어', '발음', '해석']
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

# 💡 [수정된 다중 오디오 동시 생성 캐시 엔진: 배속 파라미터 수신]
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
                # 💡 구글 TTS 속도 적용 (slow=True/False)
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

    html_code = f"""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px;">
        <audio id="sequentialPlayer" controls autoplay style="width: 100%; outline: none;"></audio>
        <div id="statusText" style="text-align: center; font-family: sans-serif; font-size: 14px; margin-top: 5px; color: #333;">
            오디오 로딩 중...
        </div>
    </div>
    <script>
        var audios = {js_array};
        var currentIdx = 0;
        var player = document.getElementById("sequentialPlayer");
        var status = document.getElementById("statusText");
        var globalSpeedDesc = "{speed_desc}";

        function updateStatus() {{
            status.innerText = "🔊 재생 중: 공통 배속: " + globalSpeedDesc + " (" + (currentIdx + 1) + " / " + audios.length + " 번째 목소리)";
        }}

        if(audios.length > 0) {{
            player.src = audios[0];
            updateStatus();
            
            var playPromise = player.play();
            if (playPromise !== undefined) {{
                playPromise.catch(function(error) {{
                    status.innerText = "⏸️ 스마트폰 보안 차단: 위 재생(▶) 버튼을 수동으로 눌러주세요.";
                }});
            }}

            player.onended = function() {{
                currentIdx++;
                if(currentIdx < audios.length) {{
                    player.src = audios[currentIdx];
                    updateStatus();
                    player.play();
                }} else {{
                    status.innerText = "✅ 모든 재생 완료 (다시 듣기를 원하시면 표를 다시 터치하세요)";
                }}
            }};
        }}
    </script>
    """
    components.html(html_code, height=100)

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

    st.caption(f"총 {len(filtered_df)}개의 항목")

    selection = st.dataframe(
        filtered_df,
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

    if selected_rows:
        selected_idx = selected_rows[0]
        selected_num = filtered_df.iloc[selected_idx]['번호']
        selected_word = filtered_df.iloc[selected_idx]['캄보디아어']
        selected_pron = filtered_df.iloc[selected_idx]['발음']
        selected_mean = filtered_df.iloc[selected_idx]['해석']
        
        st.markdown("---")
        num_str = f"[{selected_num}] " if selected_num else ""
        st.success(f"현재 선택됨: **{num_str}{selected_word}**")
        st.info(f"💡 [{selected_pron}] {selected_mean}")

        if voice_options:
            # 💡 [수정된 로직] 사용자가 선택한 공통 속도 매핑 값을 음성 생성 엔진에 전송합니다.
            with st.spinner(f"🎵 선택하신 {len(voice_options)}개의 고품질 음성(배속: {final_speed_level_desc})을 동시 준비 중입니다..."):
                audio_datas, error_msgs = generate_multiple_audios(selected_word, voice_options, final_edge_rate_str, final_gtts_slow)
            
            for err in error_msgs:
                st.error(err)
            
            if audio_datas:
                # 플레이어에도 현재 배속 단계를 표시하기 위해 전송
                play_sequential_audio(audio_datas, final_speed_level_desc)
    else:
        st.info("💡 위 표에서 원하는 행을 손가락으로 터치하세요.")
