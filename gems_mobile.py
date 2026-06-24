import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import os

# 1. 화면을 꽉 채우는 'wide' 레이아웃 적용
st.set_page_config(page_title="GEMS Mobile Table", page_icon="🔊", layout="wide")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("표에서 원하는 문장을 터치하면 발음이 재생됩니다.")

EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

if not EXCEL_FILE:
    st.error("❌ 엑셀 파일이 없습니다.")
    st.stop()

# 💡 [핵심 해결 로직: 메모리 격리 읽기]
# 엑셀 파일을 직접 여는 대신 RAM으로 데이터를 통째로 복사한 뒤 읽어냅니다.
# 엑셀 원본 파일 잠김(File Lock) 및 BadZipFile 에러를 원천 차단합니다.
@st.cache_data
def load_all_data(filepath):
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    
    # RAM 상에서 엑셀 파일 구조 해독
    excel_data = io.BytesIO(file_bytes)
    xl = pd.ExcelFile(excel_data, engine='openpyxl')
    sheet_names = xl.sheet_names
    
    sheets_dict = {}
    for sheet in sheet_names:
        # 각 시트를 읽을 때도 독립된 스트림 사용
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
    
    # 번호부터 영어(5번째 열)까지만 컷오프
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

    # 4단 독립 표 구성
    sub_df = df[['번호', '원문', '발음', '해석']]
    sub_df.columns = ['번호', '크메르어', '발음', '해석']
    return sub_df

processed_df = process_sheet_data(all_sheets[selected_sheet])

# 초고속 오디오 캐싱 유지
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
        
        num_str = f"[{selected_num}] " if selected_num else ""
        st.success(f"🔊 재생 중: {num_str}{selected_word}")
        st.info(f"💡 [{selected_pron}] {selected_mean}")

        audio_data = get_audio_bytes(selected_word)
        st.audio(audio_data, format="audio/mp3", autoplay=True)
    else:
        st.info("💡 표에서 원하는 행을 터치하세요.")
