import base64
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def load_ding_base64() -> str:
    """ding.wav를 앱 기준 경로에서 읽어 base64 문자열 반환. 실패 시 빈 문자열."""
    try:
        path = Path(__file__).resolve().parent / "ding.wav"
        if not path.is_file():
            return ""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def render_sound_component(trigger: str, ding_b64: str = "") -> None:
    """
    B2가 1이 되는 순간 무조건 new Audio().play() 실행.
    localStorage 체크 없음. 재생 실패 시 화면에 에러 표시.
    """
    b64 = ding_b64 or load_ding_base64()
    if not b64:
        st.error("ding.wav를 불러올 수 없습니다. (파일 경로 확인)")
        return
    trigger_esc = trigger.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
    html = f"""
    <div id="dingError" style="display:none; background:#ff4b4b; color:#fff; padding:8px 12px; border-radius:4px; font-size:14px; margin:4px 0;"></div>
    <audio id="dingAudio" preload="auto" style="display:none">
        <source src="data:audio/wav;base64,{b64}" type="audio/wav">
    </audio>
    <script>
    (function() {{
        var trigger = "{trigger_esc}";
        if (!trigger) return;
        var el = document.getElementById("dingAudio");
        var errEl = document.getElementById("dingError");
        var dataUrl = el && el.querySelector("source") ? el.querySelector("source").src : "";
        if (!dataUrl) {{
            if (errEl) {{ errEl.textContent = "오디오 URL 없음"; errEl.style.display = "block"; }}
            return;
        }}
        var audio = new Audio(dataUrl);
        audio.play().then(function() {{}}).catch(function(e) {{
            var msg = (e && e.message) ? e.message : String(e);
            if (errEl) {{ errEl.textContent = "소리 재생 실패: " + msg; errEl.style.display = "block"; }}
        }});
    }})();
    </script>
    """
    components.html(html, height=56)


@st.cache_data(ttl=20)
def fetch_sheet(url: str) -> pd.DataFrame:
    """구글 시트 URL에서 데이터를 읽어온다.

    - 권장: 구글 시트에서 `웹에 게시` → CSV 링크 사용
    - 일반 편집 URL인 경우, CSV export 주소로 변환을 시도한다.
    """
 url = url.strip()

    # 일반 편집 URL을 CSV export URL로 변환 시도
    if "/edit" in  and "export?format=csv" not in :
        # 예: https://docs.google.com/spreadsheets/d/FILE_ID/edit#gid=0
        #  → https://docs.google.com/spreadsheets/d/FILE_ID/export?format=csv&gid=0
        base, _, tail = .partition("/edit")
        gid = "0"
        if "gid=" in tail:
            # #gid=숫자 형식
            try:
                gid = tail.split("gid=")[1].split("&")[0]
            except Exception:
                pass
         = f"{base}/export?format=csv&gid={gid}"

    df = pd.read_csv()
    return df


def df_hash(df: Optional[pd.DataFrame]) -> str:
    if df is None or df.empty:
        return ""
    # 정렬 & 문자열 변환을 통해 내용 기반 해시 생성
    normalized = df.sort_index(axis=1).to_json(date_format="iso", orient="split")
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def get_b2_value(df: pd.DataFrame) -> str:
    """B2 셀 값 (소리 재생 판단용). 시트: A=내용, B=소리, C=점멸."""
    if df is None or df.empty or len(df.columns) < 2:
        return ""
    return str(df.iloc[0, 1]).strip()


def get_c2_value(df: pd.DataFrame) -> str:
    """C2 셀 값 (점멸 여부 판단용)."""
    if df is None or df.empty or len(df.columns) < 3:
        return ""
    return str(df.iloc[0, 2]).strip()


def render_board(
    df: Optional[pd.DataFrame],
    flash: bool = False,
    flash_elapsed: float = 0.0,
):
    """전광판: A열(내용)만 표시. B·C열은 화면에 절대 표시하지 않음.
    flash=True일 때 flash_elapsed(초)만큼 animation-delay를 주어 새로고침 후에도 애니메이션이 이어지도록 함."""
    if df is None or df.empty:
        st.markdown(
            '<div class="board-text">표시할 데이터가 없습니다.</div>',
            unsafe_allow_html=True,
        )
        return

    # A열(내용)만 사용. B(소리), C(점멸) 열은 사용하지 않음.
    col_a = df.iloc[:, 0]
    lines = col_a.astype(str).tolist()

    if not lines:
        st.markdown(
            '<div class="board-text">표시할 데이터가 없습니다.</div>',
            unsafe_allow_html=True,
        )
        return

    cls = "board-text flash" if flash else "board-text"
    html_lines = "<br>".join(lines)
    if flash and flash_elapsed > 0:
        delay_style = f" style=\"animation-delay: -{flash_elapsed:.1f}s\""
    else:
        delay_style = ""
    st.markdown(
        f'<div class="{cls}"{delay_style}>{html_lines}</div>',
        unsafe_allow_html=True,
    )


def main():
    # Streamlit 렌더 순서: 설정 → CSS/스크립트 → 세션 초기화 → 자동 새로고침 → 데이터 로드 → 상태 갱신 → 전광판 렌더 → 소리 트리거 갱신 → 소리 컴포넌트
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

        /* 전광판 텍스트: 10vw, 수직 중앙보다 약간 위, 정중앙 */
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
            background-color: #000000;
            color: #ffff66;
            font-family: "Pretendard", system-ui, -apple-system, BlinkMacSystemFont,
                         "Segoe UI", sans-serif;
        }

        /* C열=1일 때: 총 15초간 1초 간격 배경/글자 반전 (노랑↔검정), 15초 후 마지막 상태 유지(forwards) */
        @keyframes board-flash {
            0%   { background-color: #000000; color: #ffff66; }
            50%  { background-color: #ffff66; color: #000000; }
            100% { background-color: #000000; color: #ffff66; }
        }
        .board-text.flash {
            animation: board-flash 1s linear 15 forwards;
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

    # 브라우저 정책: 메인 페이지에서 한 번이라도 클릭하면 오디오 재생 허용 (localStorage에 기록)
    st.markdown(
        """
        <script>
        (function() {
            document.addEventListener("click", function f() {
                document.removeEventListener("click", f);
                try { localStorage.setItem("audioUnlocked", "1"); } catch (e) {}
            }, { once: true });
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

    st.title(" ")  # 실제 화면에서는 숨기고 CSS로만 구성

    # 고정된 구글 시트 CSV URL (앱 시작 시 자동 사용)
    sheet_url = "https://docs.google.com/spreadsheets/d/1dp1G3dyQKyM-ko0HFsbYjCxJmrvWDF5YeGFqVdVuXjk/export?format=csv"
        "https://docs.google.com/spreadsheets/"
        "d/1dffblmQyM895-ONRKOnwArHwO4T17RHHtKyEoMh4ccI/export?format=csv"
    )

    # KST 기준: 오전 7시~오후 4시는 15초, 그 외(오후 5시~다음날 오전 6시 59분)는 3시간 주기
    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    hour = now_kst.hour
    if 7 <= hour < 17:
        refresh_interval = 20  # 초 (활동 시간)
    else:
        refresh_interval = 10800  # 3시간 = 10800초 (비활동 시간, 리소스 절약)

    # 세션 상태 초기화
    if "last_hash" not in st.session_state:
        st.session_state.last_hash = ""
    if "last_update_ts" not in st.session_state:
        st.session_state.last_update_ts = 0.0
    if "last_b2" not in st.session_state:
        st.session_state.last_b2 = ""
    if "last_c2" not in st.session_state:
        st.session_state.last_c2 = ""
    if "flash_start_time" not in st.session_state:
        st.session_state.flash_start_time = None  # 점멸 시작 시각 (float 또는 None)
    if "flash_done" not in st.session_state:
        st.session_state.flash_done = False  # 점멸 1회 끝나면 True, C2가 0이 되면 초기화
    if "sound_trigger" not in st.session_state:
        st.session_state.sound_trigger = ""  # B2가 1이 될 때만 설정, 소리 1회 재생용
    if "ding_b64" not in st.session_state:
        st.session_state.ding_b64 = load_ding_base64()  # 경로 예외 처리 후 한 번만 로드

    placeholder = st.empty()

    # 자동 새로고침 (KST에 따라 15초 또는 3시간 주기)
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
    current_b2 = get_b2_value(df)
    current_c2 = get_c2_value(df)
    b2_is_one = current_b2 in ("1", "1.0")  # B2 소리: 시트에서 1 또는 1.0으로 올 수 있음
    c2_is_one = current_c2 in ("1", "1.0")  # C2 점멸: 시트에서 1 또는 1.0으로 올 수 있음

    # C열 점멸: 1회만 15초 실행. C2가 0이 되면 flash_done 초기화 후 다시 1이면 작동
    if not c2_is_one:
        st.session_state.flash_start_time = None
        st.session_state.flash_done = False  # C2가 0이 되면 초기화
    elif not st.session_state.flash_done and st.session_state.flash_start_time is None:
        st.session_state.flash_start_time = time.time()  # C2=1이고 아직 1회 안 했으면 시작
    st.session_state.last_c2 = current_c2

    flash_start = st.session_state.flash_start_time
    elapsed = (time.time() - flash_start) if flash_start else 999
    if flash_start is not None and elapsed > 15.0:
        st.session_state.flash_start_time = None
        st.session_state.flash_done = True  # 15초 지나면 1회 종료, C2가 0 되기 전까지 재시작 안 함
    flash_on = c2_is_one and st.session_state.flash_start_time is not None
    flash_elapsed = min(elapsed, 15.0) if flash_on else 0.0

    # (임시) 점멸 상태 디버그 출력
    st.write(f"점멸 상태: {flash_on}, 경과 시간: {flash_elapsed}")

    # 화면: A열(내용)만 표시. 점멸 시 새로고침 후에도 이어지도록 flash_elapsed 반영
    if changed:
        st.session_state.last_hash = current_hash
        st.session_state.last_update_ts = time.time()
    with placeholder:
        render_board(df, flash=flash_on, flash_elapsed=flash_elapsed)

    # B열 값이 0→1로 바뀔 때만 sound_trigger 설정 (컴포넌트에서 1회 재생, 세션으로 중복 방지)
    last_b2_is_one = st.session_state.last_b2 in ("1", "1.0")
    if b2_is_one and not last_b2_is_one:
        st.session_state.sound_trigger = str(time.time())
        st.session_state.last_b2 = "1"
    else:
        st.session_state.last_b2 = current_b2

    # 소리 컴포넌트: 클릭 한 번 후 해제되면 trigger 시 1회만 재생 (ding.wav 경로 예외 처리됨)
    render_sound_component(
        st.session_state.get("sound_trigger", ""),
        st.session_state.get("ding_b64", ""),
    )

    # 브라우저 자동 재생 정책 안내 (아주 작은 글씨로 하단에 표시)
    st.markdown(
        '<div class="autoplay-hint">※ 브라우저 정책 때문에 처음 접속 시 화면을 한 번 클릭해야 소리가 재생됩니다.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

