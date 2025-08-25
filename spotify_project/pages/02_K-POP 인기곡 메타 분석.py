# dashboard_top10_meta_center_tabs_theme_final.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils import fetch_artist_top_df

st.set_page_config(page_title="K-pop 인기곡 분석", page_icon="🏆", layout="wide")

# ────────────────
# 전체 테마 CSS 적용
# ────────────────
st.markdown(
    """
    <style>
    /* 버튼 스타일 */
    div.stButton > button { background-color: #1f77b4; color: white; font-weight: bold; }
    /* 다중선택, 슬라이더 배경 */
    div.stMultiSelect > div, div.stSlider > div { background-color: #e6f2ff; }
    /* Metric 값 색상 */
    .stMetric-value { color: #1f77b4; font-weight: bold; }
    /* 탭 글자 색상 및 배경 */
    .stTabs button { color: #1f77b4; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True
)

st.title("🏆 K-pop 인기곡 메타 분석 (상위 10%)")

# ────────────────
# 페이지 요약
# ────────────────
st.markdown(
    """
    ### 🔎 분석 요약
    - 선택한 K-pop 그룹의 곡 데이터를 기반으로 인기도 상위 10% 곡을 식별합니다.
    - 각 연도별 평균 인기도 및 인기곡 비율을 계산하여 추세를 시각화합니다.
    - 곡별 재생시간 분포를 확인하고, 원본 데이터를 직접 탐색할 수 있습니다.
    """
)

# ────────────────
# 분석 설정 UI (중앙 배치)
# ────────────────
st.subheader("분석 설정")
col1, col2 = st.columns(2)
default_groups = ["BTS", "BLACKPINK", "NewJeans", "SEVENTEEN",
                  "TWICE", "NCT", "EXO", "IVE", "LE SSERAFIM", "STRAY KIDS"]

with col1:
    groups = st.multiselect("그룹 선택", default_groups, default=default_groups[:5])
with col2:
    limit = st.slider("그룹당 곡 수", 10, 50, 20)

load_btn = st.button("데이터 불러오기")

# ────────────────
# 데이터 로더
# ────────────────
@st.cache_data(show_spinner=False)
def load_groups(groups, limit):
    dfs = []
    for g in groups:
        try:
            df_g = fetch_artist_top_df(g, limit=limit, include_features=False)
            dfs.append(df_g)
        except Exception as e:
            st.warning(f"{g} 처리 중 오류 발생: {e}")
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    df["group"] = df["artist"].str.split(",").str[0].str.strip()
    df = df[["group", "artist", "track_name", "popularity", "album_release_date", "duration_min"]]
    return df

# ────────────────
# 데이터 처리 및 시각화
# ────────────────
if load_btn:
    if not groups:
        st.warning("분석할 그룹을 1개 이상 선택하세요.")
        st.stop()
    df = load_groups(groups, int(limit))
    if df.empty:
        st.error("데이터를 불러오지 못했습니다.")
        st.stop()

    st.success(f"불러오기 완료: {df['group'].nunique()}개 그룹, {len(df)}곡")

    # 상위 10% 필터링 → 인기곡/기타곡 라벨
    threshold = df["popularity"].quantile(0.90)
    df["is_top10"] = df["popularity"].apply(lambda x: "인기곡" if x >= threshold else "기타곡")

    # 연도 컬럼 처리
    df['album_release_date'] = pd.to_datetime(df['album_release_date'], errors='coerce')
    df['release_year'] = df['album_release_date'].dt.year

    # ────────────────
    # 탭 구조
    # ────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "인기도 분포", 
        "연도별 평균 인기도", 
        "연도별 인기곡 비율", 
        "곡별 재생시간", 
        "원본 데이터"
    ])

    # 1) 인기도 분포
    with tab1:
        fig = px.histogram(
            df,
            x="popularity",
            color="is_top10",
            nbins=20,
            title="인기도 분포 (상위10% vs 나머지)",
            color_discrete_map={"인기곡": "#1f77b4", "기타곡": "#d3d3d3"},
            hover_data=["track_name", "group"]
        )
        st.plotly_chart(fig, use_container_width=True)

    # 2) 연도별 평균 인기도
    with tab2:
        year_avg = df.groupby('release_year')['popularity'].mean().reset_index()
        fig = px.line(
            year_avg,
            x='release_year',
            y='popularity',
            labels={'release_year': '연도', 'popularity': '평균 인기도'},
            title='연도별 평균 인기도',
            markers=True,
            line_shape='spline',
            color_discrete_sequence=["#1f77b4"]
        )
        st.plotly_chart(fig, use_container_width=True)

    # 3) 연도별 인기곡 비율
    with tab3:
        year_count = df.groupby('release_year')['track_name'].count()
        top10_count = df[df['is_top10'] == "인기곡"].groupby('release_year')['track_name'].count()
        ratio_df = pd.DataFrame({
            'year': year_count.index,
            'total': year_count.values,
            'top10': top10_count.reindex(year_count.index, fill_value=0).values
        })
        ratio_df['top10_ratio'] = ratio_df['top10'] / ratio_df['total'] * 100
        fig = px.line(
            ratio_df,
            x='year',
            y='top10_ratio',
            title='연도별 인기곡 비율 (%)',
            markers=True,
            labels={'year': '연도', 'top10_ratio': '인기곡 비율 (%)'},
            line_shape='spline',
            color_discrete_sequence=["#1f77b4"]
        )
        st.plotly_chart(fig, use_container_width=True)

    # 4) 곡별 재생시간 분포
    with tab4:
        fig = px.violin(
            df,
            y="duration_min",
            box=True,
            points="all",
            color="group",
            title="곡별 재생시간 분포 (분)",
            hover_data=["track_name", "release_year"],
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig, use_container_width=True)

        

    # 5) 원본 데이터
    with tab5:
        st.dataframe(df, use_container_width=True)
