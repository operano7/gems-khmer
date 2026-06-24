import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import os

# 1. 모바일 맞춤형 화면 설정
st.set_page_config(page_title="GEMS Mobile", page_icon="🔊", layout="centered")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("단어 목록에서 항목을 선택하면 폰에서 발음이 자동 재생됩니다.")

# 자동 확장자 추적 시스템
EXCEL_FILE = None
for ext in ['.xlsx', '.xlsm']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

if EXCEL_FILE:
    # 멀티 시트 자동 감지 엔진
    xl = pd.ExcelFile(EXCEL_FILE, engine='openpyxl')
    sheet_names = xl.sheet_names
    selected_sheet = st.selectbox("📂 학습할 단어장 시트를 선택하세요:", sheet_names)
else:
    st.error("❌ 서버 저장소에 '캄보디아어 공부' 엑셀 파일이 존재하지 않습니다.")
    st.stop()

@st.cache_data
def load_data(sheet_name):
    try:
        # 헤더 없이 순수 데이터 구조로 로드
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name, header=None, engine='openpyxl')
        
        # 💡 시작 행 추적 (유령 타이틀 스킵)
        start_row = 0
        for i in range(min(15, len(df))):
            val = str(df.iloc[i, 0]).strip()
            if val.isdigit() or val == '번호' or 'no' in val.lower():
                start_row = i if val.isdigit() else i + 1
                break
                
        df = df.iloc[start_row:].reset_index(drop=True)
        num_cols = df.shape[1]
        
        # 💡 [iloc 물리적 위치 강제 매핑] 
        # 열의 이름이나 형태에 의존하지 않고 A=0, B=1, C=2, D=3 구조로 무조건 잘라옵니다.
        df['원문'] = df.iloc[:, 1].astype(str) if num_cols > 1 else ""
        df['발음'] = df.iloc[:, 2].astype(str) if num_cols > 2 else ""
        df['한국어'] = df.iloc[:, 3].astype(str) if num_cols > 3 else ""
        
        # 💡 빈칸(float, NaN)을 빈 문자열로 완벽하게 소독하는 정제 함수
        def clean_text(text):
            t = str(text).strip()
            return "" if t.lower() in ['nan', 'none', 'nat'] else t

        df['원문'] = df['원문'].apply(clean_text)
        df['발음'] = df['발음'].apply(clean_text)
        df['한국어'] = df['한국어'].apply(clean_text)
        
        df = df[df['원문'] != '']

        # 💡 [float 에러 원천 차단 결합 로직]
        def combine_meanings(row):
            parts = []
            # 여기서 한 번 더 str()로 감싸 타입 충돌의 싹을 자릅니다.
            pron = str(row['발음']).strip()
            kor = str(row['한국어']).strip()
            
            if pron: parts.append(f"[{pron}]")
            if kor: parts.append(kor)
            
            return "  ➔  ".join(parts) if parts else "해석 없음"

        df['의미'] = df.apply(combine_meanings, axis=1)
        
        sub_df = df[['원문', '의미']].dropna()
        sub_df.columns = ['단어', '의미']
        
        sub_df = sub_df[~sub_df['단어'].str.contains('크메르어|단어|번호|헤더', na=False)]
        return sub_df
            
    except Exception as e:
        st.error(f"❌ 엑셀 파일을 읽어올 수 없습니다: {e}")
        return None

df = load_data(selected_sheet)

if df is not None:
    search_query = st.text_input("🔍 단어, 발음 또는 해석 검색:", "")
    if search_query:
        filtered_df = df[df['단어'].str.contains(search_query, na=False) | 
                        df['의미'].str.contains(search_query, na=False)]
    else:
        filtered_df = df

    st.write(f"총 {len(filtered_df)}개의 단어가 검색되었습니다.")

    display_list = [f"[{i+1}] {row['단어']} : {row['의미']}" for i, row in filtered_df.iterrows()]
    
    if display_list:
        selected_item = st.radio("학습할 단어를 터치하세요:", display_list, index=0)
        selected_word = selected_item.split("] ")[1].split(" : ")[0]
        st.success(f"현재 선택된 단어: {selected_word}")

        tts = gTTS(text=selected_word, lang='km')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3", autoplay=True)
    else:
        st.warning("검색 결과가 없습니다.")
