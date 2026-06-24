import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import os

# 1. 모바일 3단 표를 위해 화면을 꽉 채우는 'wide' 레이아웃 적용
st.set_page_config(page_title="GEMS Mobile Table", page_icon="🔊", layout="wide")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("표에서 원하는 문장을 터치하면 발음이 재생됩니다.")

# 자동 확장자 추적
EXCEL_FILE = None
for ext in ['.xlsx', '.xlsm']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

if EXCEL_FILE:
    xl = pd.ExcelFile(EXCEL_FILE, engine='openpyxl')
    selected_sheet = st.selectbox("📂 학습할 단어장 시트:", xl.sheet_names)
else:
    st.error("❌ 엑셀 파일이 없습니다.")
    st.stop()

@st.cache_data
def load_data(sheet_name):
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name, header=None, engine='openpyxl')
        
        start_row = 0
        for i in range(min(15, len(df))):
            val = str(df.iloc[i, 0]).strip()
            if val.isdigit() or val == '번호' or 'no' in val.lower():
                start_row = i if val.isdigit() else i + 1
                break
                
        df = df.iloc[start_row:].reset_index(drop=True)
        num_cols = df.shape[1]
        
        # 물리적 열 분리
        df['원문'] = df.iloc[:, 1].astype(str) if num_cols > 1 else ""
        df['발음'] = df.iloc[:, 2].astype(str) if num_cols > 2 else ""
        
        # 해석 싹쓸이
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

        # 💡 [요청 반영] 의미를 하나로 합치지 않고 3개의 열로 독립 추출
        sub_df = df[['원문', '발음', '해석']].dropna()
        sub_df.columns = ['크메르어', '발음', '한국어 해석']
        return sub_df
            
    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
        return None

# 💡 [핵심 최적화] 지연 시간(Latency) 소멸을 위한 오디오 캐싱 엔진
# 한 번 생성된 음성은 메모리에 저장되어 다음 터치 시 0.1초 만에 로드됩니다.
@st.cache_data(show_spinner=False)
def get_audio_bytes(text):
    tts = gTTS(text=text, lang='km')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

df = load_data(selected_sheet)

if df is not None:
    search_query = st.text_input("🔍 검색어 입력:", "")
    if search_query:
        filtered_df = df[
            df['크메르어'].str.contains(search_query, na=False) | 
            df['발음'].str.contains(search_query, na=False) |
            df['한국어 해석'].str.contains(search_query, na=False)
        ].reset_index(drop=True)
    else:
        filtered_df = df.reset_index(drop=True)

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
        
        # 하단에 재생 중인 정보 깔끔하게 표시
        st.success(f"🔊 재생 중: {selected_word}")
        st.info(f"💡 [{selected_pron}] {selected_mean}")

        # 캐시된 오디오 데이터를 즉각 호출하여 재생
        audio_data = get_audio_bytes(selected_word)
        st.audio(audio_data, format="audio/mp3", autoplay=True)
    else:
        st.info("💡 표에서 원하는 행을 터치하세요.")
