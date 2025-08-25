# app.py — 메인 홈 (프로 리팩토링)
import base64
from pathlib import Path
import plotly.express as px
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spotify API 기반 K-POP 대시보드",
    page_icon="🎵",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def img_base64(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode()

def right_align(*widgets):
    cols = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])  # 균등 12그리드
    with cols[-1]:
        for w in widgets:
            w

# ──────────────────────────────────────────────────────────────────────────────
# 최소 스타일(가독성 + 일관성 위주, 과한 박스/그라데이션 제거)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    :root {
      --text:#0f172a; --muted:#475569; --border:#e2e8f0;
    }
    .stApp { background:#ffffff; }
    .main .block-container { padding-top: 1.25rem; }
    h1,h2,h3,h4,p,li { color: var(--text); }
    .subtitle { font-size: 1.05rem; color: var(--muted); margin-top:.25rem; }
    .hero-wrap { display:flex; align-items:center; gap:.5rem; }
    .hero-logo { height: 40px; opacity:.9; }
    .hero-img { width:100%; max-height:460px; object-fit:cover; border-radius:12px; border:1px solid var(--border); }
    .thin-hr { border:0; height:1px; background:#eaeef3; margin: 0.75rem 0 1.25rem; }
    .small { color: var(--muted); font-size: 12px; }
    .nav-wrap p { margin:.25rem 0 .9rem 0; color: var(--muted); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────────────────────────────────────
b64_spotify = img_base64("assets/spotify.png")
spotify_html = (
    f'<img src="data:image/png;base64,{b64_spotify}" class="hero-logo" alt="Spotify" />'
    if b64_spotify else ""
)

st.markdown(
    f"""
    <div class="hero-wrap">
      <h1 style="margin:0;">Spotify API 기반 K-POP 대시보드</h1>
      {spotify_html}
    </div>
    <p class="subtitle">음악별 특성·인기도·발매 패턴을 한눈에.</p>
    """,
    unsafe_allow_html=True,
)

# 상단 오른쪽에 빠른 링크(옵션): 깔끔한 상단/우측 정렬 버튼 예시
# right_align(st.page_link("pages/05_아이돌 그룹별 곡 특성 비교.py", label="바로 가기: 그룹 비교"))

st.markdown('<hr class="thin-hr" />', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 히어로 이미지
# ──────────────────────────────────────────────────────────────────────────────
b64_concert = img_base64("assets/concert.png")
if b64_concert:
    st.image(f"data:image/png;base64,{b64_concert}", use_container_width=True, caption=None)
else:
    st.info("assets/concert.png 파일을 추가하면 상단 이미지를 표시합니다.", icon="ℹ️")

# ──────────────────────────────────────────────────────────────────────────────
# 요약 섹션(탭으로 간결하게)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("### 📌 프로젝트 개요")
tab1, tab2, tab3, tab4 = st.tabs(["범위 정의", "작업 분해", "일정·간트차트", "Streamlit 사용 예시"])

with tab1:
    st.markdown(
        """
- **🎯 목표**
  - Spotify API를 활용해 곡 특성, 인기 유지력, 발매 패턴을 다각도로 분석하고, 그룹 비교 등을 진행
- **분석 범위**  
  - 연도/분기별 발매 추세  
  - 아티스트별 평균 인기도 및 곡 특성  
  - 장기 인기 유지력  
  - 협업곡 / Explicit 비율  
        """
    )

with tab2:
    st.markdown(
        """
- **데이터 수집**  
  - Spotify Web API 활용 
  - 아티스트별 상위 곡 메타데이터 및 발매 정보 수집  

- **시각화 개발 (Streamlit + Plotly)**  
  - `line`: 연도별/분기별 발매 추세  
  - `bar`: 그룹별 평균 인기도, 곡 길이, Explicit 비율  
  - `scatter` + 회귀선: 연식 대비 인기도 (체류력) 분석  
  - `box`: 곡 길이, 앨범 수록곡 분포  
  - `heatmap`: 연식 버킷별 인기(코호트)  

- **대시보드 구현**  
  - Streamlit Pages 기반 6개 주요 분석 모듈  
  - KPI 카드, 탭형 차트, 고급 분석 옵션(잔차·PCA) 제공  
  - 사용자가 직접 아티스트 입력 및 곡 수 설정 가능
        """
    )

with tab3:
    # 비율 조정 (왼쪽 좁게, 오른쪽 넓게)
    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(
            """
**일정(예시)**  
- **1시간차**: 목표 정리, API 연동, `utils.py` 골격  
- **2–3시간차**: 데이터 수집(검색 페이지네이션/market)
- **3–5시간차**: 개별 페이지 개발 및 병합(탭·차트)  
- **5–6시간차**: 통합·버그픽스(중복 제거·limit 검증)  
- **6–7시간차**: 메인 페이지/전체 UI 폴리싱
            """
        )

    with c2:
        gantt_md = """
### 📊 간트 차트

| 작업             | 1h  | 2h  | 3h  | 4h  | 5h  | 6h  | 7h  |
|------------------|-----|-----|-----|-----|-----|-----|-----|
| 목표 설정         | ■■■ |     |     |     |     |     |     |
| 데이터 수집       |     | ■■■ |     |     |     |     |     |
| 개별 페이지 개발  |     |     | ■■■ | ■■■ | ■■■ |     |     |
| 전체 UI 수정      |     |     |     |     | ■■■ | ■■■ | ■■■ |
"""
        st.markdown(gantt_md)

# 예시 코드 스니펫 모음
FEATURE_SNIPPETS = {
    "st.set_page_config": """st.set_page_config(page_title="Demo", page_icon="🎵", layout="wide")""",
    "st.sidebar": """with st.sidebar():\n    st.header("필터")\n    year = st.slider("발매 연도", 1990, 2025, (2015,2025))""",
    "st.columns": """c1, c2 = st.columns(2)\nc1.metric("총 곡 수", 1200)\nc2.metric("평균 인기도", 68)""",
    "st.tabs": """tab1, tab2 = st.tabs(["요약", "세부"])\nwith tab1:\n    st.write("요약 탭")""",
    "st.expander": """with st.expander("자세히 보기"):\n    st.write("추가 설명")""",
    "st.metric": """st.metric(label="상위 10% 히트곡 수", value=120, delta="+8")""",
    "st.dataframe / st.table": """import pandas as pd\ndf = pd.DataFrame({"A":[1,2]})\nst.dataframe(df)""",
    "st.image / st.audio / st.video": """st.image("https://picsum.photos/720/420")""",
    "st.download_button": """st.download_button("CSV 다운로드", data="a,b\\n1,2", file_name="sample.csv")""",
    "st.slider": """val = st.slider("값 선택", 0, 100, 50)""",
    "st.plotly_chart": """import plotly.express as px, pandas as pd\ndf = pd.DataFrame({"x":[1,2,3],"y":[2,4,8]})\nst.plotly_chart(px.line(df, x="x", y="y"))""",
}
FEATURE_KEYS = list(FEATURE_SNIPPETS.keys())

with tab4:
    st.markdown("#### 사용해 볼 기능을 선택하세요")
    select_feats = st.multiselect(
        "예시 코드를 탭으로 보여드립니다",
        FEATURE_KEYS,
        default=["st.sidebar","st.columns","st.metric","st.plotly_chart"]
    )

    if select_feats:
        example_tabs = st.tabs(select_feats)
        for i, feat in enumerate(select_feats):
            with example_tabs[i]:
                st.markdown(f"**✅ {feat}**")
                st.code(FEATURE_SNIPPETS[feat], language="python")
    else:
        st.info("위에서 기능을 선택하면 예시 코드가 탭으로 표시됩니다.")


st.markdown('<hr class="thin-hr" />', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 페이지 네비게이션(네이티브 위주, 가벼운 설명 캡션)
# ──────────────────────────────────────────────────────────────────────────────
PAGE_PATHS = {
    "release_time":  "pages/00_K-POP 재생시간 추세 분석.py",
    "long_loved":    "pages/01_K-POP 데이터로 본 '오래 사랑받는 곡'의 조건.py",
    "yearly_hits":   "pages/02_K-POP 인기곡 메타 분석.py",
    "artist_meta":   "pages/03_각 아티스트의 발매곡 인기도 분석.py",
    "mood_length":   "pages/04_Charlie Puth 트랙 분석.py",
    "group_compare": "pages/05_아이돌 그룹별 곡 특성 비교.py",
}

st.markdown("### 🔎 분석 페이지")

row1 = st.columns(3)
with row1[0]:
    st.page_link(PAGE_PATHS["release_time"], label="⏳ 재생시간 추세 분석")
    st.caption("발매 시점에 따른 평균 재생시간 변화 추세")

with row1[1]:
    st.page_link(PAGE_PATHS["long_loved"], label="💖 오래 사랑받는 곡")
    st.caption("체류 지표·스트리밍 지표로 장기 흥행 특성 탐색")

with row1[2]:
    st.page_link(PAGE_PATHS["yearly_hits"], label="📈 인기곡 메타분석")
    st.caption("시대별 인기 트렌드의 변곡점 확인")

row2 = st.columns(3)
with row2[0]:
    st.page_link(PAGE_PATHS["artist_meta"], label="🎤 각 아티스트의 발매곡 인기도 분석")
    st.caption("특정 아티스트의 앨범 인기도를 분석")

with row2[1]:
    st.page_link(PAGE_PATHS["mood_length"], label="🎤 Charlie Puth 트랙 분석")
    st.caption("템포·무드 분포 및 구조적 변화")

with row2[2]:
    st.page_link(PAGE_PATHS["group_compare"], label="✨ 그룹별 특성 비교")
    st.caption("인기도·발매 패턴·협업 비율 등 비교")

st.markdown('<hr class="thin-hr" />', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 푸터(경고/안내 최소화, 메타 정보)
# ──────────────────────────────────────────────────────────────────────────────