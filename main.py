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
    try:
        path = Path(__file__).resolve().parent / "ding.wav"
        if not path.is_file():
            return ""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def render_sound_component(trigger: str, ding_b64: str = "") -> None:
    b64 = ding_b64 or load_ding_base64()
    if not b64:
        st.error("ding.wav를 불러올 수 없습니다. (파일 경로 확인)")
        return

    trigger_esc = trigger.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

    html = f"""
    <audio id="dingAudio" preload="auto" style="display:none">
        <source src="data:audio/wav;base64,{b64}" type="audio/wav">
    </audio>

    <script>
    (function() {{
        const trigger = "{trigger_esc}";
        if (!trigger) return;

        const audio = document.getElementById("dingAudio");
        if (!audio) return;

        try {{
            audio.pause();
            audio.currentTime = 0;
            audio.load();

            const playPromise = audio.play();
            if (playPromise !== undefined) {{
                playPromise.catch(function(err) {{
                    console.log("소리 재생 실패:", err);
                }});
            }}
        }} catch (err) {{
            console.log("오디오 처리 실패:", err);
        }}
    }})();
    </script>
    """
    components.html(html, height=1)


@st.cache_data(ttl=20)
def fetch_sheet(url: str) -> pd.DataFrame:
    url = url.strip()

    if "/edit" in url and "export?format=csv" not in url:
        base, _, tail = url.partition("/edit")
        gid = "0"

        if "gid=" in tail:
            try:
                gid = tail.split("gid=")[1].split("&")[0]
            except Exception:
                pass

        url = f"{base}/export?format=csv&gid={gid}"

    return pd.read_csv(url)


def get_b2_value(df: pd.DataFrame) -> str:
    if df is None or df.empty or len(df.columns) < 2:
        return ""
    return str(df.iloc[0, 1]).strip()


def get_c2_value(df: pd.DataFrame) -> str:
    if df is None or df.empty or len(df.columns) < 3:
        return ""
    return str(df.iloc[0, 2]).strip()


def get_d2_value(df: pd.DataFrame) -> str:
    if df is None or df.empty or len(df.columns) < 4:
        return ""
    return str(df.iloc[0, 3]).strip()


def get_text_signature(df: Optional[pd.DataFrame]) -> str:
    """A열 내용만 기준으로 변경 감지."""
    if df is None or df.empty:
        return ""
    col_a = df.iloc[:, 0].astype(str).tolist()
    joined = "\n".join(col_a)
    return hashlib.md5(joined.encode("utf-8")).hexdigest()


def render_board(
    df: Optional[pd.DataFrame],
    flash: bool = False,
    flash_elapsed: float = 0.0,
) -> None:
    if df is None or df.empty:
        st.markdown(
            '<div class="board-wrap"><div class="board-text">표시할 데이터가 없습니다.</div></div>',
            unsafe_allow_html=True,
        )
        return

    col_a = df.iloc[:, 0]
    lines = col_a.astype(str).tolist()

    if not lines:
        st.markdown(
            '<div class="board-wrap"><div class="board-text">표시할 데이터가 없습니다.</div></div>',
            unsafe_allow_html=True,
        )
        return

    cls = "board-text flash" if flash else "board-text"
    html_lines = "<br>".join(lines)

    if flash and flash_elapsed > 0:
        delay_style = f' style="animation-delay: -{flash_elapsed:.1f}s"'
    else:
        delay_style = ""

    st.markdown(
        f'<div class="board-wrap"><div class="{cls}"{delay_style}>{html_lines}</div></div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="학급 안내 전광판",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            margin: 0 !important;
            padding: 0 !important;
            background: #000000 !important;
            overflow: hidden !important;
        }

        body {
            overscroll-behavior: none !important;
        }

        .stApp, section.main, .main {
            background-color: #000000 !important;
            color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
            max-width: 100% !important;
        }

        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        div[data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
        }

        header[data-testid="stHeader"] {
            display: none !important;
            height: 0 !important;
        }

        [data-testid="stToolbar"] {
            display: none !important;
            height: 0 !important;
        }

        footer {
            display: none !important;
        }

        #MainMenu {
            visibility: hidden !important;
        }

        ::-webkit-scrollbar {
            width: 0px;
            height: 0px;
            background: transparent;
        }

        .board-wrap {
            width: 100vw;
            height: 100vh;
            min-height: 100vh;
            margin: 0 !important;
            padding: 0 !important;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #000000;
            overflow: hidden;
        }

        .board-text {
            width: 100vw;
            height: 100vh;
            min-height: 100vh;
            box-sizing: border-box;
            margin: 0 !important;
            padding: 0 1rem 0 1rem;
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
            font-family: "Pretendard", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            overflow: hidden;
        }

        @keyframes board-flash {
            0%   { background-color: #000000; color: #ffff66; }
            50%  { background-color: #ffff66; color: #000000; }
            100% { background-color: #000000; color: #ffff66; }
        }

        .board-text.flash {
            animation: board-flash 1s linear 15 forwards;
        }

        .autoplay-hint {
            position: fixed;
            bottom: 4px;
            right: 8px;
            font-size: 10px;
            color: #666666;
            opacity: 0.7;
            z-index: 9999;
            pointer-events: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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

    sheet_url = "https://docs.google.com/spreadsheets/d/1dp1G3dyQKyM-ko0HFsbYjCxJmrvWDF5YeGFqVdVuXjk/export?format=csv"

    kst = ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    hour = now_kst.hour

    if 7 <= hour < 17:
        refresh_interval = 5
    else:
        refresh_interval = 30

    if "last_text_sig" not in st.session_state:
        st.session_state.last_text_sig = ""
    if "last_d2" not in st.session_state:
        st.session_state.last_d2 = ""
    if "flash_start_time" not in st.session_state:
        st.session_state.flash_start_time = None
    if "flash_done" not in st.session_state:
        st.session_state.flash_done = False
    if "sound_trigger" not in st.session_state:
        st.session_state.sound_trigger = ""
    if "ding_b64" not in st.session_state:
        st.session_state.ding_b64 = load_ding_base64()

    placeholder = st.empty()

    from streamlit_autorefresh import st_autorefresh  # type: ignore
    st_autorefresh(interval=refresh_interval * 1000, key="sheet_autorefresh")

    try:
        df = fetch_sheet(sheet_url)
    except Exception:
        with placeholder:
            st.markdown(
                '<div class="board-wrap"><div class="board-text">데이터를 불러오지 못했습니다.<br>잠시 후 자동으로 다시 시도합니다.</div></div>',
                unsafe_allow_html=True,
            )
        return

    current_text_sig = get_text_signature(df)
    text_changed = current_text_sig != st.session_state.last_text_sig

    current_b2 = get_b2_value(df)
    current_c2 = get_c2_value(df)
    current_d2 = get_d2_value(df)

    b2_is_one = current_b2 in ("1", "1.0")
    c2_is_one = current_c2 in ("1", "1.0")

    d2_is_checked = current_d2.upper() == "TRUE"
    trigger_checked_now = d2_is_checked and (current_d2 != st.session_state.last_d2)

    should_trigger = text_changed or trigger_checked_now

    if should_trigger and c2_is_one:
        st.session_state.flash_start_time = time.time()
        st.session_state.flash_done = False

    flash_start = st.session_state.flash_start_time
    elapsed = (time.time() - flash_start) if flash_start else 999

    if flash_start is not None and elapsed > 15.0:
        st.session_state.flash_start_time = None
        st.session_state.flash_done = True

    flash_on = st.session_state.flash_start_time is not None
    flash_elapsed = min(elapsed, 15.0) if flash_on else 0.0

    with placeholder:
        render_board(df, flash=flash_on, flash_elapsed=flash_elapsed)

    if should_trigger and b2_is_one:
        st.session_state.sound_trigger = str(time.time())

    if text_changed:
        st.session_state.last_text_sig = current_text_sig

    st.session_state.last_d2 = current_d2

    render_sound_component(
        st.session_state.get("sound_trigger", ""),
        st.session_state.get("ding_b64", ""),
    )

    st.markdown(
        '<div class="autoplay-hint">※ 처음 한 번 화면을 클릭해야 소리가 재생될 수 있음</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
