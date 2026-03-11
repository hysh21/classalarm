import time
import hashlib
from typing import Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


@st.cache_data(ttl=20)
def fetch_sheet(url: str) -> pd.DataFrame:
    """구글 시트 URL에서 데이터를 읽어온다.

    - 권장: 구글 시트에서 `웹에 게시` → CSV 링크 사용
    - 일반 편집 URL인 경우, CSV export 주소로 변환을 시도한다.
    """
    sheet_url = url.strip()

    # 일반 편집 URL을 CSV export URL로 변환 시도
    if "/edit" in sheet_url and "export?format=csv" not in sheet_url:
        # 예: https://docs.google.com/spreadsheets/d/FILE_ID/edit#gid=0
        #  → https://docs.google.com/spreadsheets/d/FILE_ID/export?format=csv&gid=0
        base, _, tail = sheet_url.partition("/edit")
        gid = "0"
        if "gid=" in tail:
            # #gid=숫자 형식
            try:
                gid = tail.split("gid=")[1].split("&")[0]
            except Exception:
                pass
        sheet_url = f"{base}/export?format=csv&gid={gid}"

    df = pd.read_csv(sheet_url)
    return df


def df_hash(df: Optional[pd.DataFrame]) -> str:
    if df is None or df.empty:
        return ""
    # 정렬 & 문자열 변환을 통해 내용 기반 해시 생성
    normalized = df.sort_index(axis=1).to_json(date_format="iso", orient="split")
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def play_ding():
    """변경 시 1회 재생용 오디오 태그 (HTML5, components 사용)."""
    audio_html = """
    <audio autoplay>
        <source src="ding.wav" type="audio/wav">
        Your browser does not support the audio element.
    </audio>
    """
    components.html(audio_html, height=0)


def render_board(df: Optional[pd.DataFrame]):
    """전광판 스타일로 데이터 렌더링."""
    if df is None or df.empty:
        st.markdown(
            '<div class="board-text">표시할 데이터가 없습니다.</div>',
            unsafe_allow_html=True,
        )
        return

    # 컬럼이 '내용' 또는 '메시지' 같은 이름일 수 있으므로 우선순위로 선택
    preferred_cols = ["내용", "메시지", "공지", "title", "message"]
    text_col = None
    for c in preferred_cols:
        if c in df.columns:
            text_col = c
            break

    if text_col is None:
        # 첫 번째 열 기준으로 전체를 큰 글자로 표시
        lines = df.astype(str).agg(" | ".join, axis=1).tolist()
    else:
        lines = df[text_col].astype(str).tolist()

    if not lines:
        st.markdown(
            '<div class="board-text">표시할 데이터가 없습니다.</div>',
            unsafe_allow_html=True,
        )
        return

    # 여러 줄을 전광판 스타일로 표시
    html_lines = "<br>".join(lines)
    st.markdown(
        f'<div class="board-text">{html_lines}</div>', unsafe_allow_html=True
    )


def main():
    st.set_page_config(
        page_title="학급 안내 전광판",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # 전체 화면, 검은 배경, 큰 글자, 여백 제거 CSS
    st.markdown(
        """
        <style>
        /* 기본 배경 및 글자색, 전체 여백 제거 */
        .stApp, .main .block-container, section.main {
            background-color: #000000;
            color: #ffffff;
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }

        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            max-width: 100% !important;
        }

        /* 스크롤바 제거 (가능한 범위에서) */
        ::-webkit-scrollbar {
            width: 0px;
            background: transparent;
        }

        /* 전광판 텍스트: 15vw, 수직 중앙보다 약간 위, 정중앙, 줄 간격 가독성 */
        .board-text {
            width: 100%;
            min-height: 100vh;
            box-sizing: border-box;
            margin: 0 auto;
            padding: 0 1rem 14vh 1rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            font-size: 10vw;
            font-weight: 700;
            line-height: 1.55;
            letter-spacing: 0.02em;
            color: #ffff66;
            font-family: "Pretendard", system-ui, -apple-system, BlinkMacSystemFont,
                         "Segoe UI", sans-serif;
        }

        /* 헤더/푸터 요소 등 불필요한 요소 최소화 */
        header[data-testid="stHeader"] {
            display: none;
        }
        footer {
            visibility: hidden;
        }

        /* 자동 재생 안내 문구 (아주 작게 하단에 표시) */
        .autoplay-hint {
            position: fixed;
            bottom: 4px;
            right: 8px;
            font-size: 10px;
            color: #666666;
            opacity: 0.7;
            z-index: 9999;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title(" ")  # 실제 화면에서는 숨기고 CSS로만 구성

    # 고정된 구글 시트 CSV URL (앱 시작 시 자동 사용)
    sheet_url = (
        "https://docs.google.com/spreadsheets/"
        "d/1dffblmQyM895-ONRKOnwArHwO4T17RHHtKyEoMh4ccI/export?format=csv"
    )

    refresh_interval = 30  # 초

    # 세션 상태 초기화
    if "last_hash" not in st.session_state:
        st.session_state.last_hash = ""
    if "last_update_ts" not in st.session_state:
        st.session_state.last_update_ts = 0.0

    placeholder = st.empty()

    # 자동 새로고침 (30초마다 한 번씩 페이지 리런)
    # 최신 버전에서는 st.experimental_rerun 대신 st.rerun 사용
    st_autorefresh = st.rerun  # 타입 힌트용 더미
    from streamlit_autorefresh import st_autorefresh  # type: ignore

    st_autorefresh(interval=refresh_interval * 1000, key="sheet_autorefresh")

    # 데이터 로드 및 변경 감지
    try:
        df = fetch_sheet(sheet_url)
    except Exception:
        # 에러 상세 내용은 숨기고, 전광판 스타일의 안내 문구만 표시
        with placeholder:
            st.markdown(
                '<div class="board-text">데이터를 불러오지 못했습니다.<br>잠시 후 자동으로 다시 시도합니다.</div>',
                unsafe_allow_html=True,
            )
        return

    current_hash = df_hash(df)
    changed = current_hash != st.session_state.last_hash

    # 변경된 경우에만 화면 갱신 + 소리 재생
    if changed:
        st.session_state.last_hash = current_hash
        st.session_state.last_update_ts = time.time()
        with placeholder:
            render_board(df)
        play_ding()
    else:
        # 기존 화면을 유지하기 위해, 직전에 그렸던 데이터가 없으면 한 번만 그림
        with placeholder:
            render_board(df)

    # 브라우저 자동 재생 정책 안내 (아주 작은 글씨로 하단에 표시)
    st.markdown(
        '<div class="autoplay-hint">※ 브라우저 정책 때문에 처음 접속 시 화면을 한 번 클릭해야 소리가 재생됩니다.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

