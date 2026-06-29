import streamlit as st
import time
import asyncio

# (기존 오디오 재생 함수가 있다고 가정 - 예: play_audio)

def play_normal_mode(lang1_text, lang2_text, lang1_audio_path, lang2_audio_path, wait_time):
    """
    일반 재생 모드 실행 함수
    """
    # 1. 화면에 텍스트가 들어갈 빈 공간(Placeholder)을 순서대로 생성
    text1_placeholder = st.empty()
    text2_placeholder = st.empty()

    # 2. 제1언어 자막 출력 및 오디오 재생
    # 첫 번째 공간에만 텍스트를 채워 넣습니다.
    text1_placeholder.markdown(f"### {lang1_text}")
    
    # 제1언어 오디오 재생 로직 실행 (기존 구축하신 재생 함수 호출)
    # play_audio(lang1_audio_path) 

    # 3. 언어 간 대기 시간 적용 
    # 이 시간 동안 제2언어 자막 공간(text2_placeholder)은 빈 상태로 유지됩니다.
    time.sleep(wait_time) 
    
    # 💡 만약 edge_tts 등과 연동하여 전체 로직을 비동기(async/await)로 처리 중이시라면 
    # time.sleep 대신 아래 코드를 사용해야 화면 멈춤이 발생하지 않습니다.
    # await asyncio.sleep(wait_time)

    # 4. 대기 시간이 끝난 직후 제2언어 자막 출력 및 오디오 재생
    text2_placeholder.markdown(f"<div class='khmer-custom-font'>{lang2_text}</div>", unsafe_allow_html=True)
    
    # 제2언어 오디오 재생 로직 실행
    # play_audio(lang2_audio_path)
