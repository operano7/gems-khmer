import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import os

# 1. 화면 설정
st.set_page_config(page_title="GEMS Mobile Table", page_icon="🔊", layout="wide")

st.title("🇰🇭 GEMS 모바일 크메르어 학습기")

# 💡 [핵심 복구] 음성 및 API 키 설정 UI
voice_option = st.radio(
    "🗣️ 발음 목소리 선택:", 
    ["Google (기본/여성)", "OpenAI 남성 (Onyx)", "OpenAI 여성 (Nova)"], 
    horizontal=True
)

# OpenAI API 키 안전 관리 (서버 Secrets에 있으면 자동 로드, 없으면 사이드바에서 입력)
OPENAI_API_KEY = ""
if "OPENAI_API_KEY" in st.secrets:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    OPENAI_API_KEY = st.sidebar.text_input("🔑 OpenAI API Key (OpenAI 음성 사용 시 필수):", type="password")

st.write("표에서 원하는 문장을 터치하면 발음이 재생됩니다. (재생기 ▶️ 버튼으로 다시 듣기 가능)")

# 파일 탐색
EXCEL_FILE = None
for ext in ['.xlsm', '.xlsx']:
    if os.path.exists(f"캄보디아어 공부{ext}"):
        EXCEL_FILE = f"캄보디아어 공부{ext}"
        break

if not EXCEL_FILE:
    st.error("❌ 엑셀 파일이 없습니다.")
    st.stop()

# 메모리 격리 로직 (엑셀 에러 원천 차단)
@st.cache_data
def load_all_data(filepath):
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    
    excel_data = io.BytesIO(file_bytes)
    xl = pd.ExcelFile(excel_data, engine='openpyxl')
    sheet_names = xl.sheet_names
    
    sheets_dict = {}
    for sheet in sheet_names:
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

    sub_df = df[['번호', '원문', '발음', '해석']]
    sub_df.columns = ['번호', '크메르어', '발음', '해석']
    return sub_df

processed_df = process_sheet_data(all_sheets[selected_sheet])

# 💡 [핵심 복구] OpenAI 및 Google 하이브리드 음성 엔진
@st.cache_data(show_spinner=False)
def get_audio_bytes(text, v_option, api_key):
    if "OpenAI" in v_option:
        if not api_key:
            return None # API 키가 없으면 생성 불가
        
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # 선택에 따라 남성(onyx) 또는 여성(nova) 배정
        voice_model = "onyx" if "남성" in v_option else "nova"
        
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice_model,
            input=text
        )
        return response.content
    else:
        # 구글 기본 음성
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
        st.success(f"🔊 현재 선택됨: {num_str}{selected_word}")
        st.info(f"💡 [{selected_pron}] {selected_mean}")

        # 음성 데이터 호출 (캐시 기반 초고속 재생)
        audio_data = get_audio_bytes(selected_word, voice_option, OPENAI_API_KEY)
        
        if audio_data:
            # 자동 재생과 동시에 재생기 UI를 화면에 남겨두어 원할 때 언제든 다시 듣기 가능
            st.audio(audio_data, format="audio/mp3", autoplay=True)
        else:
            st.warning("⚠️ OpenAI 음성을 사용하려면 왼쪽 사이드바(화살표 〉)를 열어 API Key를 입력해주세요.")
    else:
        st.info("💡 표에서 원하는 행을 터치하세요.")
