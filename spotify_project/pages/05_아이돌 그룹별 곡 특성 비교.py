# pages/05_아이돌 그룹별 곡 특성 비교.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils import fetch_artist_top_df

st.set_page_config(page_title="아이돌 그룹별 곡 특성 비교", page_icon="✨", layout="wide")
st.title("✨ 아이돌 그룹별 곡 특성 비교")

# ---------------- UI ----------------
artists_text = st.text_input(
    "아티스트(그룹) 이름을 콤마(,)로 구분해 입력하세요",
    value="BTS, BLACKPINK, NewJeans, 소녀시대",
    placeholder="예: IU, TWICE, IVE"
)
limit = st.slider("아티스트당 가져올 곡 수", 5, 200, 25, step=5)
market_opt = st.selectbox(
    "시장(market) 필터(선택)", 
    options=["전체(미지정)", "KR", "US", "JP", "GB", "DE", "FR", "BR"],
    index=0
)
market = None if market_opt == "전체(미지정)" else market_opt

# ---------------- Data Loader (cached) ----------------
@st.cache_data(show_spinner=True)
def load_groups(artist_list, limit, market):
    dfs = []
    for g in artist_list:
        df = fetch_artist_top_df(
            g, limit=limit, include_features=False,
            use_search=True, market=market  # ← 검색 기반으로 limit까지 수집
        )
        if not df.empty:
            df["main_artist"] = g  # 비교용 고정 라벨
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()

    out = pd.concat(dfs, ignore_index=True)

    # 파생 컬럼
    out["release_year"] = pd.to_datetime(out["album_release_date"], errors="coerce").dt.year
    if "duration_min" not in out:
        out["duration_min"] = (out["duration_ms"] / 60000).round(2)

    # 협업/단독 구분
    def _artists_count(s):
        if pd.isna(s): return 0
        return len([x.strip() for x in str(s).split(",") if x.strip()])
    out["artists_count"] = out["artist"].apply(_artists_count)
    out["collab_flag"] = out["artists_count"].apply(lambda n: "협업" if n > 1 else "단독")

    # 발매 월/분기
    rel = pd.to_datetime(out["album_release_date"], errors="coerce")
    out["release_month"] = rel.dt.month
    out["release_quarter"] = rel.dt.quarter

    return out

# ---------------- Run ----------------
if st.button("불러오기", use_container_width=True):
    # 입력 파싱
    groups = [g.strip() for g in artists_text.split(",") if g.strip()]
    groups = list(dict.fromkeys(groups))  # 중복 제거, 순서 유지

    if not groups:
        st.warning("아티스트 이름을 1개 이상 입력하세요.")
        st.stop()

    data = load_groups(tuple(groups), limit, market)

    if data.empty:
        st.warning("데이터를 가져오지 못했습니다. 아티스트 이름/네트워크 상태/market 옵션을 확인하세요.")
        st.stop()

    # ── 상단 KPI ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 곡 수", f"{len(data)}")
    c2.metric("그룹 수", f"{data['main_artist'].nunique()}")
    c3.metric("평균 인기도", f"{data['popularity'].dropna().mean():.1f}")
    c4.metric("평균 곡 길이(분)", f"{data['duration_min'].dropna().mean():.2f}")

    st.divider()

    # ── 탭 구성 ──
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "① 그룹별 평균 지표",
        "② 연도별 발매 추세",
        "③ 곡 길이 분포",
        "④ 앨범 유형/수록곡",
        "⑤ 인기도 TOP 10",
        "⑥ 원본/다운로드",
        "⑦ Explicit 비율 & 인기",
        "⑧ 발매 월/분기 패턴",
        "⑨ 협업곡 비중",
    ])

    # ① 그룹별 평균 지표
    with tab1:
        meta_avg = (data.groupby("main_artist")
                        .agg(평균인기도=("popularity","mean"),
                             평균길이_분=("duration_min","mean"))
                        .round(2)
                        .reset_index())
        col_a, col_b = st.columns(2)
        with col_a:
            fig = px.bar(meta_avg, x="main_artist", y="평균인기도", title="그룹별 평균 인기도")
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            fig = px.bar(meta_avg, x="main_artist", y="평균길이_분", title="그룹별 평균 곡 길이(분)")
            st.plotly_chart(fig, use_container_width=True)

    # ② 연도별 발매 추세
    with tab2:
        yearly = (data.dropna(subset=["release_year"])
                    .groupby(["release_year","main_artist"])["track_name"]
                    .count().rename("count").reset_index())
        if yearly.empty:
            st.info("연도 정보가 부족합니다.")
        else:
            fig = px.line(yearly, x="release_year", y="count", color="main_artist",
                          markers=True, title="연도별 곡 수(그룹별)")
            st.plotly_chart(fig, use_container_width=True)

    # ③ 곡 길이 분포
    with tab3:
        len_df = data.dropna(subset=["duration_min"])
        if len_df.empty:
            st.info("곡 길이 정보가 부족합니다.")
        else:
            fig = px.box(len_df, x="main_artist", y="duration_min",
                         points="suspectedoutliers",
                         title="그룹별 곡 길이 분포(분)")
            st.plotly_chart(fig, use_container_width=True)

    # ④ 앨범 유형/수록곡
    with tab4:
        atype = (data.assign(album_type=data["album_type"].fillna("unknown"))
                     .groupby(["main_artist","album_type"])["track_name"]
                     .count().rename("count").reset_index())
        fig = px.bar(atype, x="main_artist", y="count", color="album_type",
                     title="그룹별 앨범 유형 분포", barmode="stack")
        st.plotly_chart(fig, use_container_width=True)

        album_unique = data.drop_duplicates("album_id").copy()
        album_unique["album_total_tracks"] = album_unique["album_total_tracks"].fillna(0)
        fig = px.box(album_unique, x="main_artist", y="album_total_tracks",
                     points="suspectedoutliers", title="그룹별 앨범 수록곡 수 분포")
        st.plotly_chart(fig, use_container_width=True)

    # ⑤ 인기도 TOP 10
    with tab5:
        top10 = (data[["main_artist","track_name","album_name","album_release_date","popularity"]]
                    .dropna(subset=["popularity"])
                    .sort_values("popularity", ascending=False)
                    .head(10))
        st.dataframe(top10, use_container_width=True)

    # ⑥ 원본/다운로드
    with tab6:
        st.download_button(
            "📥 전체 데이터 CSV 다운로드",
            data=data.to_csv(index=False, encoding="utf-8-sig"),
            file_name="idol_groups_comparison.csv",
            mime="text/csv",
            use_container_width=True
        )
        with st.expander("원본 데이터 미리보기"):
            st.dataframe(
                data[[
                    "main_artist","track_name","album_name","album_release_date",
                    "popularity","duration_min","album_type","album_total_tracks"
                ]].sort_values(["main_artist","popularity"], ascending=[True, False]),
                use_container_width=True
            )

    # ⑦ Explicit 비율 & 인기
    with tab7:
        if "explicit" in data.columns:
            rate = (data.groupby("main_artist")["explicit"]
                      .mean().mul(100).round(1).reset_index(name="explicit_rate_%"))
            st.subheader("Explicit(비속어) 비율")
            st.bar_chart(rate.set_index("main_artist")["explicit_rate_%"])

            comp = (data.assign(explicit=data["explicit"].map({True:"Explicit", False:"Clean"}))
                      .groupby(["main_artist","explicit"])["popularity"]
                      .mean().round(1).reset_index())
            fig = px.bar(comp, x="main_artist", y="popularity", color="explicit",
                         barmode="group", title="Explicit 여부별 평균 인기")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("explicit 컬럼이 없습니다.")

    # ⑧ 발매 월/분기 패턴
    with tab8:
        st.subheader("월별 발매 곡 수")
        month_counts = (data.dropna(subset=["release_month"])
                          .groupby(["release_month","main_artist"])["track_name"]
                          .count().rename("count").reset_index())
        if month_counts.empty:
            st.info("발매 월 정보가 부족합니다.")
        else:
            fig = px.bar(month_counts, x="release_month", y="count", color="main_artist",
                         barmode="group", title="월별 발매 곡 수")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("분기별 발매 곡 수")
        q_counts = (data.dropna(subset=["release_quarter"])
                      .groupby(["release_quarter","main_artist"])["track_name"]
                      .count().rename("count").reset_index())
        if q_counts.empty:
            st.info("발매 분기 정보가 부족합니다.")
        else:
            fig = px.bar(q_counts, x="release_quarter", y="count", color="main_artist",
                         barmode="group", title="분기별 발매 곡 수")
            st.plotly_chart(fig, use_container_width=True)

    # ⑨ 협업곡 비중
    with tab9:
        st.subheader("협업(피처링 포함) 비중")
        collab_rate = (data.groupby("main_artist")["collab_flag"]
                         .apply(lambda s: (s == "협업").mean() * 100)
                         .round(1).reset_index(name="collab_rate_%"))
        st.bar_chart(collab_rate.set_index("main_artist")["collab_rate_%"])

        st.subheader("단독 vs 협업 평균 인기도")
        pop_comp = (data.groupby(["main_artist","collab_flag"])["popularity"]
                      .mean().round(1).reset_index())
        fig = px.bar(pop_comp, x="main_artist", y="popularity", color="collab_flag",
                     barmode="group", title="단독/협업 평균 인기 비교")
        st.plotly_chart(fig, use_container_width=True)