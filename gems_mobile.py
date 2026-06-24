import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import os

# 1. 화면을 꽉 채우는 'wide' 레이아웃 적용
st.set_page_config(page_title="GEMS Mobile Table", page_icon="🔊", layout="wide")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("표에서 원하는 문장을 터치하면 발음이 재생됩니다.")

# 파일 안전 탐색
EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:
    filename = f"캄보디아어 공부{ext}"
    if os.path.exists(filename) and os.path.getsize(filename) > 500:
        EXCEL_FILE = filename
        break

if not EXCEL_FILE:
    st.error("❌ 유효한 엑셀 파일(500바이트 이상)을 찾을 수 없습니다.")
    st.stop()

@st.cache_data
def load_entire_workbook(filepath):
    try:
        return pd.read_excel(filepath, sheet_name=None, header=None, engine='openpyxl')
    except Exception as e:
        return str(e)

all_sheets = load_entire_workbook(EXCEL_FILE)

if isinstance(all_sheets, str):
    st.error(f"❌ 엑셀 파일 읽기 실패: {all_sheets}")
    st.stop()

selected_sheet = st.selectbox("📂 학습할 단어장 시트:", list(all_sheets.keys()))

def process_sheet_data(df):
    start_row = 0
    for i in range(min(15, len(df))):
        val = str(df.iloc[i, 0]).strip()
        if val.isdigit() or val == '번호' or 'no' in val.lower():
            start_row = i if val.isdigit() else i + 1
            break
            
    df = df.iloc[start_row:].reset_index(drop=True)
    num_cols = df.shape[1]
    
    # 💡 [요청 1&2 반영] 0번째(번호)부터 4번째(영어)까지만 명확히 잘라서 가져옵니다.
    df['번호'] = df.iloc[:, 0].astype(str) if num_cols > 0 else ""
    df['원문'] = df.iloc[:, 1].astype(str) if num_cols > 1 else ""
    df['발음'] = df.iloc[:, 2].astype(str) if num_cols > 2 else ""
    df['한국어'] = df.iloc[:, 3].astype(str) if num_cols > 3 else ""
    df['영어'] = df.iloc[:, 4].astype(str) if num_cols > 4 else ""
    
    def clean_text(text):
        t = str(text).strip()
        if t.lower() in ['nan', 'none', 'nat', '']: return ""
        if t.endswith('.0'): return t[:-2]  # 파이썬이 숫자를 1.0으로 읽는 현상 방지
        return t

    for c in ['번호', '원문', '발음', '한국어', '영어']:
        df[c] = df[c].apply(clean_text)
    
    df = df[df['원문'] != '']

    # 💡 [요청 1 반영] 한국어와 영어까지만 깔끔하게 결합합니다.
    def combine_meanings(row):
        parts = []
        if row['한국어']: parts.append(row['한국어'])
        if row['영어']: parts.append(row['영어'])
        return " / ".join(parts) if parts else ""
        
    df['해석'] = df.apply(combine_meanings, axis=1)

    # 💡 [요청 2 반영] 번호 열을 맨 앞에 추가하여 4단 표로 구성합니다.
    sub_df = df[['번호', '원문', '발음', '해석']]
    sub_df.columns = ['번호', '크메르어', '발음', '해석']
    return sub_df

processed_df = process_sheet_data(all_sheets[selected_sheet])

@st.cache_data(show_spinner=False)
def get_audio_bytes(text):
    tts = gTTS(text=text, lang='km')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

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

    # 4단 엑셀 표 UI
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
        
        # 하단 재생 정보창에도 번호 표기
        num_str = f"[{selected_num}] " if selected_num else ""
        st.success(f"🔊 재생 중: {num_str}{selected_word}")
        st.info(f"💡 [{selected_pron}] {selected_mean}")

        # TTS는 순수 크메르어 문장만 읽도록 하여 발음 오염 방지
        audio_data = get_audio_bytes(selected_word)
        st.audio(audio_data, format="audio/mp3", autoplay=True)
    else:
        st.info("💡 표에서 원하는 행을 터치하세요.")
