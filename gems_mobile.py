import streamlit as st
import pandas as pd
from gtts import gTTS
import io

# 1. 모바일 맞춤형 화면 설정
st.set_page_config(page_title="GEMS Mobile", page_icon="🔊", layout="centered")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("단어 목록에서 항목을 선택하면 폰에서 발음이 자동 재생됩니다.")

# 엑셀 파일명 지정
EXCEL_FILE = "캄보디아어 공부.xlsm"

@st.cache_data
def load_data():
    try:
        # 엑셀 파일 로드
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        cols = list(df.columns)
        
        word_col, mean_col = None, None
        
        # 💡 [스마트 자동 열 감지 인공지능 시스템]
        # 엑셀 헤더 명칭이 무엇이든 유연하게 매핑을 시도합니다.
        if '단어' in cols and '의미' in cols:
            word_col, mean_col = '단어', '의미'
        elif '크메르어 원문' in cols and '한국어 번역' in cols:
            word_col, mean_col = '크메르어 원문', '한국어 번역'
        elif '크메르어' in cols and '뜻' in cols:
            word_col, mean_col = '크메르어', '뜻'
        else:
            # 명시적인 이름 매칭이 실패하면, 열의 순서(위치) 기준으로 자동 강제 할당합니다.
            if len(cols) >= 3 and ('타임스탬프' in cols or 'timestamp' in str(cols[0]).lower()):
                # 1열이 타임스탬프인 경우 ➔ 2열(단어), 3열(의미)로 지정
                word_col, mean_col = cols[1], cols[2]
            elif len(cols) >= 2:
                # 일반적인 경우 ➔ 1열(단어), 2열(의미)로 지정
                word_col, mean_col = cols[0], cols[1]
        
        if word_col and mean_col:
            # 내부 시스템 규격으로 컬럼명 통일 후 빈 데이터 제거
            sub_df = df[[word_col, mean_col]].dropna()
            sub_df.columns = ['단어', '의미']
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
        
        # 선택된 단어 추출
        selected_word = selected_item.split("] ")[1].split(" : ")[0]
        
        st.success(f"현재 선택된 단어: {selected_word}")

        # 5. 스마트폰 스피커 오디오 스트리밍 자동 재생 (Autoplay)
        tts = gTTS(text=selected_word, lang='km')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        st.audio(fp, format="audio/mp3", autoplay=True)
    else:
        st.warning("검색 결과가 없습니다.")
