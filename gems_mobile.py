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
    
    # 모바일 화면 상단에 시트 선택 박스 배치
    selected_sheet = st.selectbox("📂 학습할 단어장 시트를 선택하세요:", sheet_names)
else:
    st.error("❌ 서버 저장소에 '캄보디아어 공부' 엑셀 파일이 존재하지 않습니다.")
    st.stop()

@st.cache_data
def load_data(sheet_name):
    try:
        # 시트 로드 (헤더 없이 순수 데이터로 먼저 파싱)
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name, header=None, engine='openpyxl')
        
        # 💡 [슈퍼 헤더 탐색 및 float 에러 원천 차단 장치]
        header_row_idx = None
        for idx in range(min(15, len(df))):
            # 행 내부의 모든 값을 안전하게 '문자열'로 먼저 강제 변환하여 float 간섭을 배제합니다.
            row_values = [str(val).strip() for val in df.iloc[idx].values]
            
            # '크메르어' 또는 '단어' 키워드가 들어있는 행을 진짜 제목줄로 타깃팅합니다.
            if any('크메르어' in val or '단어' in val for val in row_values):
                header_row_idx = idx
                break
        
        # 진짜 제목줄 격상 시키기
        if header_row_idx is not None:
            df.columns = [str(c).strip() for c in df.iloc[header_row_idx]]
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
        else:
            # 제목줄 탐색 실패 시 기본 위치 기반 매핑 강제 부여
            df.columns = [f"col_{i}" for i in range(df.shape[1])]
            
        cols = list(df.columns)
        word_col, pron_col, kor_col = None, None, None
        
        # 💡 [정밀 키워드 분리 매핑 로직]
        for col in cols:
            c_str = str(col).strip()
            if '크메르어' in c_str or '원문' in c_str:
                word_col = col
            elif '발음' in c_str or '표기' in c_str:
                pron_col = col
            elif '뜻' in c_str or '의미' in c_str or '해석' in c_str or '번역' in c_str:
                kor_col = col

        # 키워드 탐색 실패 시 엑셀의 물리적 열 순서로 강제 복구 (번호 제외)
        non_no_cols = [c for c in cols if '번호' not in str(c) and 'no' not in str(c).lower() and 'col_' not in str(c)]
        if not word_col and len(non_no_cols) >= 1: word_col = non_no_cols[0]
        if not pron_col and len(non_no_cols) >= 2: pron_col = non_no_cols[1]
        if not kor_col and len(non_no_cols) >= 3: kor_col = non_no_cols[2]
        
        # 최후의 보루: 순수 열 인덱스 할당
        if not word_col and len(cols) >= 2: word_col, pron_col, kor_col = cols[1], cols[2], cols[3]

        if word_col:
            df['원문'] = df[word_col].astype(str).str.strip()
            df['발음'] = df[pron_col].astype(str).str.strip() if pron_col in df.columns else ""
            df['한국어'] = df[kor_col].astype(str).str.strip() if kor_col in df.columns else ""
            
            # 유령 결측치 처리 및 미장 청소
            for c in ['원문', '발음', '한국어']:
                df[c] = df[c].replace('nan', '').replace('None', '')
            
            df = df[df['원문'] != '']

            # 통합 한 줄 보기 포맷 가공
            def combine_meanings(row):
                parts = []
                if row['발음']: parts.append(f"[{row['발음']}]")
                if row['한국어']: parts.append(row['한국어'])
                return "  ➔  ".join(parts) if parts else "해석 없음"

            df['의미'] = df.apply(combine_meanings, axis=1)
            
            sub_df = df[['원문', '의미']].dropna()
            sub_df.columns = ['단어', '의미']
            sub_df = sub_df[~sub_df['단어'].astype(str).str.contains('크메르어|단어|번호|헤더', na=False)]
            return sub_df
        else:
            st.error(f"❌ 유효한 열을 찾지 못했습니다. (확인된 열 목록: {cols})")
            return None
            
    except Exception as e:
        st.error(f"❌ 엑셀 파일을 읽어올 수 없습니다: {e}")
        return None

# 상단에서 선택된 시트 이름을 기반으로 가동
df = load_data(selected_sheet)

if df is not None:
    # 3. 통합 검색 창
    search_query = st.text_input("🔍 단어, 발음 또는 해석 검색:", "")
    if search_query:
        filtered_df = df[df['단어'].astype(str).str.contains(search_query, na=False) | 
                        df['ve'].astype(str).str.contains(search_query, na=False)]
    else:
        filtered_df = df

    st.write(f"총 {len(filtered_df)}개의 단어가 검색되었습니다.")

    # 4. 모바일 UI 리스트 출력
    display_list = [f"[{i+1}] {row['단어']} : {row['의미']}" for i, row in filtered_df.iterrows()]
    
    if display_list:
        selected_item = st.radio("학습할 단어를 터치하세요:", display_list, index=0)
        selected_word = selected_item.split("] ")[1].split(" : ")[0]
        st.success(f"현재 선택된 단어: {selected_word}")

        # 5. 오디오 자동 재생
        tts = gTTS(text=selected_word, lang='km')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3", autoplay=True)
    else:
        st.warning("검색 결과가 없습니다.")
