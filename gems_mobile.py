import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import os

# 1. 모바일 및 PC 통합 표 스타일 화면 설정
st.set_page_config(page_title="GEMS Mobile Table", page_icon="🔊", layout="centered")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("표에서 원하는 문장을 터치하면 발음이 자동으로 재생됩니다.")

# 자동 확장자 추적 시스템
EXCEL_FILE = None
for ext in ['.xlsx', '.xlsm']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

if EXCEL_FILE:
    xl = pd.ExcelFile(EXCEL_FILE, engine='openpyxl')
    sheet_names = xl.sheet_names
    selected_sheet = st.selectbox("📂 학습할 단어장 시트를 선택하세요:", sheet_names)
else:
    st.error("❌ 서버 저장소에 '캄보디아어 공부' 엑셀 파일이 존재하지 않습니다.")
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
        
        df['원문'] = df.iloc[:, 1].astype(str) if num_cols > 1 else ""
        df['발음'] = df.iloc[:, 2].astype(str) if num_cols > 2 else ""
        
        # D열부터 끝까지 존재하는 모든 해석을 긁어오는 싹쓸이 로직
        def sweep_all_meanings(row):
            meanings = []
            for col_idx in range(3, num_cols):
                val = str(row.values[col_idx]).strip()
                if val and val.lower() not in ['nan', 'none', 'nat']:
                    meanings.append(val)
            return " / ".join(meanings)
            
        df['한국어'] = df.apply(sweep_all_meanings, axis=1) if num_cols > 3 else ""
        
        def clean_text(text):
            t = str(text).strip()
            return "" if t.lower() in ['nan', 'none', 'nat'] else t

        df['원문'] = df['원문'].apply(clean_text)
        df['발음'] = df['발음'].apply(clean_text)
        
        df = df[df['원문'] != '']

        def combine_meanings(row):
            parts = []
            pron = str(row['발음']).strip()
            kor = str(row['한국어']).strip()
            
            if pron: parts.append(f"[{pron}]")
            if kor: parts.append(kor)
            
            return "  ➔  ".join(parts) if parts else "해석 없음"

        df['의미'] = df.apply(combine_meanings, axis=1)
        
        sub_df = df[['원문', '의미']].dropna()
        sub_df.columns = ['크메르어 문장', '발음 및 한국어 해석']
        return sub_df
            
    except Exception as e:
        st.error(f"❌ 엑셀 파일을 읽어올 수 없습니다: {e}")
        return None

df = load_data(selected_sheet)

if df is not None:
    search_query = st.text_input("🔍 단어, 발음 또는 해석 검색:", "")
    if search_query:
        filtered_df = df[df['크메르어 문장'].str.contains(search_query, na=False) | 
                        df['발음 및 한국어 해석'].str.contains(search_query, na=False)].reset_index(drop=True)
    else:
        filtered_df = df.reset_index(drop=True)

    st.write(f"총 {len(filtered_df)}개의 항목이 포함되어 있습니다.")

    # Excel 스타일 대화형 표 구현
    selection = st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"  # 💡 [치명적 오타 교정 완료: 언더바(_) ➔ 하이픈(-)]
    )

    selected_rows = []
    if hasattr(selection, "selection"):
        selected_rows = selection.selection.rows
    elif isinstance(selection, dict):
        selected_rows = selection.get("selection", {}).get("rows", [])

    if selected_rows:
        selected_idx = selected_rows[0]
        selected_word = filtered_df.iloc[selected_idx]['크메르어 문장']
        selected_meaning = filtered_df.iloc[selected_idx]['발음 및 한국어 해석']
        
        st.success(f"🔊 발음 재생 중: {selected_word}")
        st.caption(f"💡 뜻: {selected_meaning}")

        tts = gTTS(text=selected_word, lang='km')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3", autoplay=True)
    else:
        st.info("💡 위 표에서 원하는 행을 손가락으로 터치하면 오디오 발음이 자동 재생됩니다.")
