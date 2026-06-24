import streamlit as st
import pandas as pd
import io
import os
import asyncio
import edge_tts  # 오미로님의 PC 코드와 동일한 무료 고품질 TTS

# 1. 화면 설정
st.set_page_config(page_title="GEMS Mobile Table", page_icon="🔊", layout="wide")
st.title("🇰🇭 GEMS 모바일 크메르어 학습기")

# 💡 [OpenAI 폐기 및 Edge TTS 도입]
voice_option = st.radio(
    "🗣️ 발음 목소리 선택:", 
    ["Google (여성)", "Edge 남성 (Piseth)", "Edge 여성 (Sreymom)"], 
    horizontal=True
)

st.write("표에서 원하는 문장을 터치하면 발음이 재생됩니다.")

EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

if not EXCEL_FILE:
    st.error("❌ 엑셀 파일이 없습니다.")
    st.stop()

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
    sub_df.columns = ['번호', '크메르어', '발음', '해석']
    return sub_df

processed_df = process_sheet_data(all_sheets[selected_sheet])

# 💡 [Edge TTS 비동기 처리기] 스트림릿 서버에서 안전하게 작동하도록 래핑
def get_edge_audio_sync(text, voice_model):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _generate():
        communicate = edge_tts.Communicate(text, voice_model)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
        
    result = loop.run_until_complete(_generate())
    loop.close()
    return result

@st.cache_data(show_spinner=False)
def generate_audio_bytes_final(khmer_text, v_option):
    if "Edge" in v_option:
        try:
            # PC 코드와 동일한 캄보디아어 모델 지정
            voice_model = "km-KH-PisethNeural" if "남성" in v_option else "km-KH-SreymomNeural"
            audio_content = get_edge_audio_sync(khmer_text, voice_model)
            return audio_content, None
        except Exception as e:
            return None, f"❌ Edge TTS 에러: {str(e)}"
    else:
        try:
            from gtts import gTTS
            tts = gTTS(text=khmer_text, lang='km')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            return fp.getvalue(), None
        except Exception as e:
            return None, f"❌ Google TTS 에러: {str(e)}"

if processed_df is not None:
    search_query = st.text_input("🔍 검색어 입력:", "")
    if search_query:
        filtered_df = processed_df[
            processed_df['번호'].str.contains(search_query, na=False) |
            processed_df['크메르어'].str.contains(search_query, na=False) | 
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
        selected_word = filtered_df.iloc[selected_idx]['크메르어']
        selected_pron = filtered_df.iloc[selected_idx]['발음']
        selected_mean = filtered_df.iloc[selected_idx]['해석']
        
        st.markdown("---")
        num_str = f"[{selected_num}] " if selected_num else ""
        st.success(f"🔊 현재 선택됨: **{num_str}{selected_word}**")
        st.info(f"💡 [{selected_pron}] {selected_mean}")

        with st.spinner("🎵 고품질 음성을 생성하는 중입니다..."):
            audio_data, error_msg = generate_audio_bytes_final(selected_word, voice_option)
        
        if error_msg:
            st.error(error_msg)
        elif audio_data:
            st.audio(audio_data, format="audio/mp3", autoplay=True)
    else:
        st.info("💡 위 표에서 원하는 행을 손가락으로 터치하세요.")
