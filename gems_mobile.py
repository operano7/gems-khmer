import streamlit as st
import pandas as pd
from gtts import gTTS
import io

# 1. 모바일 맞춤형 화면 설정
st.set_page_config(page_title="GEMS Mobile", page_icon="🔊", layout="centered")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")
st.write("단어 목록에서 항목을 선택하면 폰에서 발음이 자동 재생됩니다.")

# 2. 엑셀 파일 로드 (본인의 엑셀 파일명과 경로에 맞게 수정)
EXCEL_FILE = "캄보디아어 공부.xlsm"

@st.cache_data
def load_data():
    try:
        # 엑셀 파일을 읽어옵니다.
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        # 필요한 컬럼만 추출 (엑셀 헤더명에 맞게 조정 필요)
        return df[['단어', '의미']].dropna()
    except Exception as e:
        st.error(f"❌ 엑셀 파일을 읽어올 수 없습니다: {e}")
        return None

df = load_data()

if df is not None:
    # 3. 검색 및 필터링 기능 (모바일 자판 입력 최적화)
    search_query = st.text_input("🔍 단어 또는 의미 검색:", "")
    if search_query:
        filtered_df = df[df['단어'].str.contains(search_query, na=False) | df['의미'].str.contains(search_query, na=False)]
    else:
        filtered_df = df

    st.write(f"총 {len(filtered_df)}개의 단어가 검색되었습니다.")

    # 4. 모바일용 단어 선택 라디오박스/셀렉트박스 구현
    # 폰화면에서 터치하기 쉽게 리스트 형식으로 제공합니다.
    display_list = [f"[{i+1}] {row['단어']} : {row['의미']}" for i, row in filtered_df.iterrows()]
    
    if display_list:
        selected_item = st.radio("학습할 단어를 터치하세요:", display_list, index=0)
        
        # 선택된 단어 텍스트 추출
        selected_word = selected_item.split("] ")[1].split(" : ")[0]
        
        st.success(f"현재 선택된 단어: {selected_word}")

        # 5. 스마트폰 스피커로 오디오 전송 및 자동 재생 (Autoplay)
        # 구글 서버에서 생성된 발음 음성 파일을 폰의 브라우저 메모리로 직송합니다.
        tts = gTTS(text=selected_word, lang='km')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        # autoplay=True 옵션으로 폰에서 터치하자마자 바로 소리가 납니다.
        st.audio(fp, format="audio/mp3", autoplay=True)
    else:
        st.warning("검색 결과가 없습니다.")
