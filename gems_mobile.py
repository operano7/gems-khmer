import streamlit as st
import pandas as pd
import io
import os
import asyncio
import edge_tts
import base64
import streamlit.components.v1 as components

# 1. 앱 설정
st.set_page_config(page_title="GEMS Mobile 캄보디아어 학습기", page_icon="🔊", layout="wide")
st.title("🇰🇭 GEMS 모바일 캄보디아어 학습기 (공통 배속 지원)")

# 💡 [핵심 최적화: UI 통일 및 최신 UI 도입]
# 드롭다운과 버튼을 폐기하고, 기존처럼 가로로 3등분하여 깔끔하게 배치된 인라인 라디오 버튼 도입
st.markdown("🗣️ **발음 목소리 선택:** (여러 개를 체크하면 바통을 넘기듯 순차적으로 재생됩니다)")
col_v1, col_v2, col_v3 = st.columns(3)

with col_v1:
    use_google = st.radio("Google (여성)", value=True)
with col_v2:
    use_edge_m = st.radio("Edge 남성 (Piseth Neural)")
with col_v3:
    use_edge_f = st.radio("Edge 여성 (Sreymom Neural)")

# 원본 스크립트에서 목소리 차용
voice_options = []
if use_google: voice_options.append("Google (여성)")
if use_edge_m: voice_options.append("Edge 남성 (Piseth Neural)")
if use_edge_f: voice_options.append("Edge 여성 (Sreymom Neural)")

if not voice_options:
    st.warning("⚠️ 재생할 목소리를 최소 1개 이상 체크해 주세요.")

st.markdown("---")

# 🐢 [신규 업그레이드 및 팩트 수정: 전 TTS 공통 속도 설정]
# 이 섹션의 버튼을 이미지 3.png와 같은 인라인 라디오 버튼으로 교체
st.markdown("🐢 **전 TTS 공통 재생 속도를 설정하세요:** (모든 엔진에 공통 적용됩니다)")
col_s1, col_s2, col_s3 = st.columns(3)

with col_s1:
    speed_l1 = st.radio(" 아주 느리게 (0.6x)")
with col_s2:
    speed_l2 = st.radio(" 조금 느리게 (0.8x)")
with col_s3:
    speed_l3 = st.radio(" 보통 속도 (1.0x)")

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

final_edge_rate_str = st.session_state.final_edge_rate_str
final_gtts_slow = st.session_state.final_gtts_slow
final_speed_level_desc = st.session_state.final_speed_level_desc

st.markdown(f"✅ **현재 설정된 공통 속도 단계:** {final_speed_level_desc}")

# Google TTS 제한 안내 메시지 팩트 업데이트
if use_google and final_speed_level_desc == "조금 느리게 (0.8x)":
    st.markdown("💡 Google TTS는 기술적 제약으로 '조금 느리게(0.8x)'를 지원하지 않아,")
    st.markdown("   이 단계에서는 보통 속도(1.0x)로 재생됩니다.")
elif use_google and final_speed_level_desc == "아주 느리게 (0.6x)":
    st.markdown("💡 Google TTS는 기술적 제약으로 '아주 느리게(0.6x)'를 지원하지 않아,")
    st.markdown("   이 단계에서는 0.5배속(slow 모드)으로 재생됩니다.")

st.markdown("---")

# 앱 지침
st.write("표에서 원하는 문장을 터치하면 발음이 재생됩니다.")

# 엑셀 데이터 시뮬레이션
# 원본 스크립트에서 파일명 차용
EXCEL_FILE = "캄보디아어 공부.xlsx"

@st.cache_data
def load_all_data_simulation(filepath):
    # 가짜 데이터 생성
    sheet_names = ["사택건축", "기초회화", "생활캄보디아어"]
    sheets_dict = {}
    
    # 원본 스크립트의 4단 구조 구현
    data = {
        '번호': list(range(1, 1001)),
        '캄보디아어': [f"សូម ធ្វើประวัติ...{i}" for i in range(1, 1001)],
        '발음': [f"쏨 락싸똑 에까싸 느응 껌넛뜨라 떼양어{i}" for i in range(1, 1001)],
        '해석': [f"모든 문서와 기록을 보관해 주세요 / Keep all documents and records {i}" for i in range(1, 1001)]
    }
    df = pd.DataFrame(data)
    
    for sheet in sheet_names:
        sheets_dict[sheet] = df.copy()
        
    return sheet_names, sheets_dict

sheet_names, all_sheets = load_all_data_simulation(EXCEL_FILE)

# 시트 선택
selected_sheet = st.selectbox("📂 학습할 단어장 시트:", sheet_names)

# 데이터프레임 및 검색
processed_df = all_sheets[selected_sheet]

# 검색어 입력
search_query = st.text_input("🔍 검색어 입력:", "")

# 데이터 필터링
if search_query:
    filtered_df = processed_df.astype(str).str.contains(search_query, na=False) |
        processed_df['캄보디아어'].str.contains(search_query, na=False) | 
        processed_df['발음'].str.contains(search_query, na=False) |
        processed_df['해석'].str.contains(search_query, na=False)
    ].reset_index(drop=True)
else:
    filtered_df = processed_df.reset_index(drop=True)

# 총 항목 수 캡션
st.caption(f"총 {len(filtered_df)}개의 항목")

# 데이터프레임 표시
selection = st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row"
)

# 재생 시뮬레이션
selected_rows =
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
    num_str = f"[{cite: {selected_num}}] " if selected_num else ""
    st.success(f"🔊 현재 선택됨: **{num_str}{selected_word}**")
    st.info(f"💡 [{cite: {selected_pron}}] {selected_mean}")

    # 가짜 오디오 데이터 생성 (원본 스크립트 논리 차용: gtts 및 edge-tts의 속도 적용)
    # 원본 스크립트의 PC 이벤트를 감시하는 부분은 Streamlit 앱에 통합할 수 없으므로 무시합니다.
    audio_datas = []
    error_msgs = []
    
    for opt in voice_options:
        if "Edge" in opt:
            # 원본 스크립트의 edge-tts 목소리 차용
            voice_model = "km-KH-PisethNeural" if "남성" in opt else "km-KH-SreymomNeural"
            try:
                # 가짜 비동기 처리
                audio_content = b"fake edge audio data" 
                audio_datas.append(audio_content)
            except Exception as e:
                error_msgs.append(f"Edge TTS ({opt}) 에러: {str(e)}")
        else:
            try:
                # 가짜 gtts 처리 (slow 모드 적용)
                audio_content = b"fake google audio data"
                audio_datas.append(audio_content)
            except Exception as e:
                error_msgs.append(f"Google TTS 에러: {str(e)}")
                
    # 플레이어 표시 (가로로 병합하여 재생)
    # 파이썬과 Streamlit에는 오디오를 순차적으로 재생하는 기능이 없으므로, 자바스크립트를 사용해 플레이어를 구현합니다.
    if audio_datas:
        # 오디오 데이터를 웹에서 읽을 수 있는 Base64 텍스트로 변환
        b64_audios = []
        for ab in audio_datas:
            b64 = base64.b64encode(ab).decode()
            b64_audios.append(f"data:audio/mp3;base64,{b64}")

        js_array = str(b64_audios).replace("'", '"')

        # 자바스크립트를 활용해 1번이 끝나면 2번, 2번이 끝나면 3번을 재생하도록 지시
        html_code = f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px;">
            <audio id="sequentialPlayer" controls autoplay style="width: 100%; outline: none;"></audio>
            <div id="statusText" style="text-align: center; font-family: sans-serif; font-size: 14px; margin-top: 5px; color: #333;">
                오디오 로딩 중...
            </div>
        </div>
        <script>
            var audios = {cite: {js_array}};
            var currentIdx = 0;
            var player = document.getElementById("sequentialPlayer");
            var status = document.getElementById("statusText");

            function updateStatus() {{
                status.innerText = "🔊 재생 중... 공통 배속: {final_speed_level_desc} (" + (currentIdx + 1) + " / " + audios.length + " 번째 목소리)";
            }}

            if(audios.length > 0) {{
                player.src = audios;
                updateStatus();
                player.play();

                player.onended = function() {{
                    currentIdx++;
                    if(currentIdx < audios.length) {{
                        player.src = audios;
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
else:
    st.info("💡 위 표에서 원하는 행을 손가락으로 터치하세요.")
