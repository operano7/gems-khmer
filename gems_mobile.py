import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import os

# 1. 모바일 맞춤형 화면 설정
st.set_page_config(page_title="GEMS Mobile", page_icon="🔊", layout="centered")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("단어 목록에서 항목을 선택하면 폰에서 발음이 자동 재생됩니다.")

# 💡 [자동 확장자 추적 시스템]
# 폴더 내에 .xlsx가 있으면 최우선으로 읽고, 없으면 .xlsm을 순차 탐색하여 에러를 원천 차단합니다.
EXCEL_FILE = None
for ext in ['.xlsx', '.xlsm']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

@st.cache_data
def load_data():
    if not EXCEL_FILE:
        st.error("❌ 서버 저장소에 '캄보디아어 공부.xlsx' 또는 '.xlsm' 파일이 존재하지 않습니다.")
        return None
    try:
        # 엑셀 파일 로드
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        
        # 💡 [슈퍼 헤더 자동 격상 시스템]
        # 엑셀 상단에 빈 줄이나 타이틀이 있어 진짜 제목줄이 데이터 행으로 내려앉은 경우를 자동 치유합니다.
        header_row_idx = None
        for idx in range(min(5, len(df))):
            row_values = df.iloc[idx].astype(str).tolist()
            if any('크메르어' in val or '단어' in val for val in row_values):
                header_row_idx = idx
                break
        
        # 진짜 제목줄을 찾았다면 컬럼명으로 격상시키고 상부 데이터는 정리합니다.
        if header_row_idx is not None:
            df.columns = [str(c).strip() for c in df.iloc[header_row_idx]]
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
        
        cols = list(df.columns)
        word_col, mean_col = None, None
        
        # 키워드 기반 스마트 열 매핑 (열 밀림 방지)
        for col in cols:
            col_str = str(col).strip()
            if any(x in col_str for x in ['크메르어', '단어', '원문', 'khmer', 'word']):
                word_col = col
                break
                
        for col in cols:
            col_str = str(col).strip()
            if any(x in col_str for x in ['뜻', '의미', '번역', '한국어', 'mean', 'korean']):
                mean_col = col
                break
        
        # 매칭 실패 시 최종 보루 로직
        if not word_col or not mean_col:
            if len(cols) >= 3 and (cols[0] == '번호' or 'no' in str(cols[0]).lower()):
                word_col, mean_col = cols[1], cols[2]
            elif len(cols) >= 2:
                word_col, mean_col = cols[0], cols[1]
        
        if word_col and mean_col:
            sub_df = df[[word_col, mean_col]].dropna()
            sub_df.columns = ['단어', '의미']
            # 제목줄 문자열이 데이터에 잔존해 있다면 청소
            sub_df = sub_df[~sub_df['단어'].astype(str).str.contains('크메르어|단어|번호', na=False)]
            return sub_df
        else:
            st.error(f"❌ 엑셀에 유효한 데이터 열이 부족합니다. (확인된 열 목록: {cols})")
            return None
            
    except Exception as e:
        st.error(f"❌ 엑셀 파일을 읽어올 수 없습니다: {e}")
        return None

df = load_data()

if df is not None:
    # 3. 검색 및 필터링 기능 (모바일 자판 입력 최적화)
    search_query = st.text_input("🔍 단어 또는 의미 검색:", "")
    if search_query:
        filtered_df = df[df['단어'].astype(str).str.contains(search_query, na=False) | 
                        df['의미'].astype(str).str.contains(search_query, na=False)]
    else:
        filtered_df = df

    st.write(f"총 {len(filtered_df)}개의 단어가 검색되었습니다.")

    # 4. 모바일용 리스트 형식 UI 구현
    display_list = [f"[{i+1}] {row['단어']} : {row['의미']}" for i, row in filtered_df.iterrows()]
    
    if display_list:
        selected_item = st.radio("학습할 단어를 터치하세요:", display_list, index=0)
        selected_word = selected_item.split("] ")[1].split(" : ")[0]
        st.success(f"현재 선택된 단어: {selected_word}")

        # 5. 스마트폰 오디오 스트리밍 자동 재생
        tts = gTTS(text=selected_word, lang='km')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3", autoplay=True)
    else:
        st.warning("검색 결과가 없습니다.")
