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

@st.cache_data
def load_data():
    if not EXCEL_FILE:
        st.error("❌ 서버 저장소에 '캄보디아어 공부' 엑셀 파일이 존재하지 않습니다.")
        return None
    try:
        # 엑셀 파일 로드 (헤더를 자동 지정하지 않고 기본 로드)
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        
        # 💡 [정밀 헤더 및 열 매핑 매스터 시스템]
        # 엑셀 내에서 '크메르어'라는 단어가 포함된 진짜 제목줄 위치를 정확하게 찾습니다.
        header_row_idx = None
        for idx in range(min(10, len(df))):
            row_values = df.iloc[idx].astype(str).tolist()
            if any('크메르어' in val or '단어' in val for val in row_values):
                header_row_idx = idx
                break
        
        # 진짜 제목줄을 찾았다면 해당 행을 컬럼명으로 선언하고 상부 데이터 절단
        if header_row_idx is not None:
            df.columns = [str(c).strip() for c in df.iloc[header_row_idx]]
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
        
        cols = list(df.columns)
        word_col, mean_col = None, None
        
        # 💡 정확한 엑셀 원문 매칭 (우선순위 철저 분리)
        # 1) '크메르어' 혹은 '단어'가 들어간 열을 원문으로 매핑
        for col in cols:
            if '크메르어' in str(col) or '단어' in str(col):
                word_col = col
                break
                
        # 2) 한글 및 영문 해석(뜻) 열 매핑
        for col in cols:
            if any(x in str(col) for x in ['뜻', '의미', '해석', '한국어', '번역']):
                mean_col = col
                break
        
        # 만약 키워드 매칭이 실패했을 경우 안전 장치
        if not word_col or not mean_col:
            if len(cols) >= 3:
                word_col, mean_col = cols[1], cols[2]
            elif len(cols) >= 2:
                word_col, mean_col = cols[0], cols[1]
        
        if word_col and mean_col:
            # 원문과 해석 데이터만 추출 후 결측치 제거
            sub_df = df[[word_col, mean_col]].dropna()
            sub_df.columns = ['단어', '의미']
            
            # 제목용 유령 데이터 청소
            sub_df = sub_df[~sub_df['단어'].astype(str).str.contains('크메르어|단어|번호|헤더', na=False)]
            return sub_df
        else:
            st.error(f"❌ 유효한 열을 찾지 못했습니다. (현재 인식된 열: {cols})")
            return None
            
    except Exception as e:
        st.error(f"❌ 엑셀 파일을 읽어올 수 없습니다: {e}")
        return None

df = load_data()

if df is not None:
    # 3. 검색 및 필터링 기능
    search_query = st.text_input("🔍 단어 또는 의미 검색:", "")
    if search_query:
        filtered_df = df[df['단어'].astype(str).str.contains(search_query, na=False) | 
                        df['의미'].astype(str).str.contains(search_query, na=False)]
    else:
        filtered_df = df

    st.write(f"총 {len(filtered_df)}개의 단어가 검색되었습니다.")

    # 4. 모바일용 리스트 형식 UI 구현 (포맷 엄격 고정)
    display_list = [f"[{i+1}] {row['단어']} : {row['의미']}" for i, row in filtered_df.iterrows()]
    
    if display_list:
        selected_item = st.radio("학습할 단어를 터치하세요:", display_list, index=0)
        
        # 선택된 단어 추출
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
