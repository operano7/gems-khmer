import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import os

# 1. 화면을 꽉 채우는 'wide' 레이아웃 적용
st.set_page_config(page_title="GEMS Mobile Table", page_icon="🔊", layout="wide")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("표에서 원하는 문장을 터치하면 발음이 재생됩니다.")

# 💡 [안전장치 1] 용량이 비정상적으로 작은 유령 파일을 걸러내고, 진짜 파일만 찾습니다.
EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:  # 최근 작업하신 xlsm을 최우선으로 탐색
    filename = f"캄보디아어 공부{ext}"
    if os.path.exists(filename) and os.path.getsize(filename) > 500:
        EXCEL_FILE = filename
        break

if not EXCEL_FILE:
    st.error("❌ 유효한 엑셀 파일(500바이트 이상)을 찾을 수 없습니다.")
    st.stop()

# 💡 [안전장치 2] 에러를 일으킨 함수를 폐기하고, 이전의 안정적인 방식으로 모든 시트를 한 번에 캐시합니다.
@st.cache_data
def load_entire_workbook(filepath):
    try:
        # sheet_name=None을 주면 엑셀 안의 모든 시트를 딕셔너리 형태로 한 방에 안전하게 가져옵니다.
        return pd.read_excel(filepath, sheet_name=None, header=None, engine='openpyxl')
    except Exception as e:
        return str(e)

all_sheets = load_entire_workbook(EXCEL_FILE)

if isinstance(all_sheets, str):
    st.error(f"❌ 엑셀 파일 읽기 실패: {all_sheets}")
    st.info("💡 팁: 스트림릿 우측 하단 [Manage app] ➔ [⋮] ➔ [Clear cache]를 눌러 서버 메모리를 초기화해 보세요.")
    st.stop()

# 안정적으로 확보한 시트 이름들을 상단 메뉴에 배치
selected_sheet = st.selectbox("📂 학습할 단어장 시트:", list(all_sheets.keys()))

# 선택된 시트의 데이터를 3단 포맷으로 가공하는 엔진
def process_sheet_data(df):
    start_row = 0
    for i in range(min(15, len(df))):
        val = str(df.iloc[i, 0]).strip()
        if val.isdigit() or val == '번호' or 'no' in val.lower():
            start_row = i if val.isdigit() else i + 1
            break
            
    df = df.iloc[start_row:].reset_index(drop=True)
    num_cols = df.shape[1]
    
    df['원문'] = df.iloc[:, 1].astype(str) if num_cols > 1 else ""
    df['발음'] = df.iloc[:, 2].astype(str) if num_cols > 2 else ""
    
    def sweep_all_meanings(row):
        meanings = []
        for col_idx in range(3, num_cols):
            val = str(row.values[col_idx]).strip()
            if val and val.lower() not in ['nan', 'none', 'nat']:
                meanings.append(val)
        return " / ".join(meanings)
        
    df['해석'] = df.apply(sweep_all_meanings, axis=1) if num_cols > 3 else ""
    
    def clean_text(text):
        t = str(text).strip()
        return "" if t.lower() in ['nan', 'none', 'nat'] else t

    df['원문'] = df['원문'].apply(clean_text)
    df['발음'] = df['발음'].apply(clean_text)
    
    df = df[df['원문'] != '']

    sub_df = df[['원문', '발음', '해석']].dropna()
    sub_df.columns = ['크메르어', '발음', '한국어 해석']
    return sub_df

processed_df = process_sheet_data(all_sheets[selected_sheet])

# 💡 [핵심 최적화] 지연 시간 소멸을 위한 초고속 발음 재생 캐시 엔진
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
            processed_df['크메르어'].str.contains(search_query, na=False) | 
            processed_df['발음'].str.contains(search_query, na=False) |
            processed_df['한국어 해석'].str.contains(search_query, na=False)
        ].reset_index(drop=True)
    else:
        filtered_df = processed_df.reset_index(drop=True)

    st.caption(f"총 {len(filtered_df)}개의 항목")

    # 3단 분리 엑셀 표 구현
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
        selected_word = filtered_df.iloc[selected_idx]['크메르어']
        selected_pron = filtered_df.iloc[selected_idx]['발음']
        selected_mean = filtered_df.iloc[selected_idx]['한국어 해석']
        
        st.success(f"🔊 재생 중: {selected_word}")
        st.info(f"💡 [{selected_pron}] {selected_mean}")

        # 캐시된 오디오 데이터를 즉각 호출하여 재생
        audio_data = get_audio_bytes(selected_word)
        st.audio(audio_data, format="audio/mp3", autoplay=True)
    else:
        st.info("💡 표에서 원하는 행을 터치하세요.")
