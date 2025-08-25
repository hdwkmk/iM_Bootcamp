# app_staying_pro_light.py
# ⏱️ 히트곡의 체류시간 (간이 지표) — Expert+ 라이트 테마

import io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone

from utils import fetch_artist_top_df  # utils에 use_search 지원되어 있어야 함!

st.set_page_config(page_title="K-POP 데이터로 본 ‘오래 사랑받는 곡’의 조건", page_icon="⏱️", layout="wide")
PRETTY_LEVEL = 8

def theme(level:int=8):
    import numpy as _np
    level = int(_np.clip(level, 1, 10))
    radius = 6 + level; shadow = 4 + 2*level
    return dict(
        radius=radius, shadow=shadow,
        primary="#6D28D9", accent="#0891B2",
        bg_from="#ffffff", bg_to="#ffffff",
        border="#E5E7EB", text="#111827"
    )
T = theme(PRETTY_LEVEL)

st.markdown(f"""
<style>
:root {{
  --card-radius: {T['radius']}px;
  --card-shadow: 0 {int(T['shadow']/2)}px {T['shadow']}px rgba(17,24,39,0.08);
  --primary: {T['primary']}; --accent: {T['accent']};
  --border: {T['border']}; --text: {T['text']};
}}
.stApp {{ background: linear-gradient(135deg, {T['bg_from']} 0%, {T['bg_to']} 100%); }}
.block-container {{ padding-top: 0.6rem; }}
h1, h2, h3, h4, h5, h6, .stMarkdown p {{ color: var(--text); }}
div[data-testid="stMetric"] {{
  background:#fff;border:1px solid var(--border);border-radius:var(--card-radius);
  box-shadow:var(--card-shadow);padding:8px 12px;
}}
.stDataFrame, .stPlotlyChart {{
  background:#fff;border:1px solid var(--border);border-radius:var(--card-radius);
  box-shadow:var(--card-shadow);padding:6px;
}}
.stButton>button, [data-baseweb="select"]>div, .stSlider>div {{ border-radius:var(--card-radius)!important; }}
hr.custom {{ border:0;height:1px;background:linear-gradient(90deg,transparent,rgba(0,0,0,.15),transparent);margin:.8rem 0 1rem; }}
.badge {{
  display:inline-block;padding:3px 10px;font-size:12px;border-radius:999px;
  background:rgba(109,40,217,.10);color:var(--text);border:1px solid rgba(109,40,217,.25)
}}
.small-dim {{ color:#6B7280;font-size:12px; }}
</style>
""", unsafe_allow_html=True)

PX_TEMPLATE = "plotly"

TOP_SPACER = 56
st.markdown(f"<div style='height:{TOP_SPACER}px;background:transparent;'></div>", unsafe_allow_html=True)

st.title("⏱️ K-POP 데이터로 본 ‘오래 사랑받는 곡’의 조건")
st.caption("**staying_index = popularity / (1 + age_years)** — 실제 '차트 체류 주'가 아니라 **발매 연식 대비 현재 인기도**를 간단히 본 값입니다.")

# ── 필터 ──
st.markdown('<span class="badge">필터</span>', unsafe_allow_html=True)
colA, colB, colC, colD, colE, colF = st.columns([2.4, 1.2, 1.1, 1.0, 1.2, 1.2])
with colA:
    artists = st.multiselect("아티스트 선택",
        ["BTS","BLACKPINK","NewJeans","SEVENTEEN","IU","EXO","TWICE"],
        default=["BTS","BLACKPINK"])
with colB:
    # ⬇️ 상한을 늘려 더 많이 가져오기
    top_n = st.slider("아티스트당 곡 수", 5, 200, 25, step=5)
with colC:
    lite = st.toggle("라이트 모드(오디오 특성 미로딩)", value=True)
with colD:
    min_pop = st.slider("최소 인기도", 0, 100, 0, step=1)
with colE:
    sort_key = st.selectbox("정렬 기준", ["staying_index","popularity","age_years"], index=0)
with colF:
    market_opt = st.selectbox("시장(market)", ["전체","KR","US","JP","GB","DE","FR","BR"], index=0)
market = None if market_opt == "전체" else market_opt

st.markdown("<hr class='custom'/>", unsafe_allow_html=True)

# ── 사이드바 ──
with st.sidebar:
    st.header("🔬 전문가 분석 옵션")
    adv = st.toggle("고급 분석 활성화", value=True)
    show_trend = st.checkbox("산점도에 전역 추세선(선형) 표시", value=True)
    label_top = st.checkbox("상위 과성과(잔차) 라벨 표시", value=True)
    top_k_label = st.number_input("라벨 개수(상위)", 3, 30, 8, step=1)
    cohort_on = st.checkbox("코호트(연식 버킷) 히트맵", value=True)
    pca_on = st.checkbox("오디오 PCA 2D(오디오 특성 로딩 필요)", value=False)
    st.caption("※ 라이트 모드 해제 시 danceability/energy/valence/PCA 사용 가능")
    st.divider()
    st.subheader("내보내기")
    want_download = st.checkbox("CSV 다운로드 버튼 표시", value=True)

go_btn = st.button("불러오기", use_container_width=True)

# ── 데이터 로드 ──
@st.cache_data(show_spinner=False)
def load_data(artist_list, limit, include_features, pop_floor, sort_key, market):
    frames = []
    for a in artist_list:
        # ⬇️ 핵심: 검색 기반 페이지네이션으로 limit까지 수집
        df = fetch_artist_top_df(
            a,
            limit=limit,
            include_features=include_features,
            use_search=True,      # ★ 중요: top-tracks 10개 한계 우회
            market=market         # 선택: KR 등 지역 필터
        )
        if df is None or df.empty:
            continue
        df["main_artist"] = a
        rel = pd.to_datetime(df["album_release_date"], errors="coerce")
        today = pd.Timestamp.now(tz="UTC").tz_convert(None)
        age_days = (today - rel).dt.days
        df["age_years"] = (age_days / 365).round(2)
        df["staying_index"] = (df["popularity"] / (1 + df["age_years"])).round(2)
        if pop_floor and pop_floor > 0:
            df = df[df["popularity"].fillna(0) >= pop_floor]
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    data = pd.concat(frames, ignore_index=True)
    data["release_year"] = pd.to_datetime(data["album_release_date"], errors="coerce").dt.year

    if sort_key in data.columns:
        ascending = False if sort_key in ["staying_index","popularity"] else True
        data = data.sort_values([sort_key,"popularity"], ascending=[ascending, False], na_position="last")
    return data.reset_index(drop=True)

# ── 유틸 함수들(회귀/잔차 등) ──
def fit_line(x, y):
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    msk = np.isfinite(x) & np.isfinite(y)
    if msk.sum() < 2:
        return np.nan, np.nan, np.nan, np.nan
    b, a = np.polyfit(x[msk], y[msk], 1)
    r = np.corrcoef(x[msk], y[msk])[0,1]
    return float(a), float(b), float(r), float(r**2)

def add_residuals(df, xcol="age_years", ycol="popularity"):
    a,b,r,r2 = fit_line(df[xcol], df[ycol])
    if np.isnan(a) or np.isnan(b):
        df = df.copy(); df["pred_pop"] = np.nan; df["resid"] = np.nan
        return df, (a,b,r,r2)
    pred = a + b*df[xcol]; resid = df[ycol] - pred
    out = df.copy(); out["pred_pop"] = pred.round(2); out["resid"] = resid.round(2)
    return out, (a,b,r,r2)

def cohort_bucket(x):
    if pd.isna(x): return np.nan
    if x < 1: return "0-1y"
    if x < 3: return "1-3y"
    if x < 6: return "3-6y"
    if x < 9: return "6-9y"
    return "9y+"

# ── 실행 ──
if go_btn:
    if not artists:
        st.warning("아티스트를 1개 이상 선택하세요."); st.stop()

    data = load_data(artists, top_n, include_features=not lite, pop_floor=min_pop, sort_key=sort_key, market=market)
    if data.empty:
        st.warning("데이터가 없습니다. 조건을 바꿔보세요."); st.stop()

    data_r, (a,b,r,r2) = add_residuals(data, "age_years", "popularity")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 곡 수", f"{len(data)}")
    c2.metric("평균 연식(년)", f"{data['age_years'].dropna().mean():.1f}")
    c3.metric("평균 체류지표", f"{data['staying_index'].dropna().mean():.1f}")
    c4.metric("전역 상관계수 r", f"{r:.2f}" if pd.notna(r) else "-")

    tabs = ["요약","산점도","TOP 10","그룹 비교","연도 추세","오디오 특성","진단","잔차 분석","데이터"]
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(tabs)

    with tab1:
        st.subheader("📌 상위 곡 요약")
        show_cols = [c for c in [
            "main_artist","track_name","album_name","album_release_date",
            "popularity","pred_pop","resid","age_years","staying_index","duration_min","tempo"
        ] if c in data_r.columns]
        head_df = data_r.sort_values(["staying_index","popularity"], ascending=[False, False]).head(20)
        st.dataframe(head_df[show_cols], use_container_width=True, height=420)
        if want_download:
            csv = data_r[show_cols].to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ 요약 CSV 다운로드", data=csv, file_name="staying_summary.csv", mime="text/csv")

    with tab2:
        st.subheader("🟣 연식 vs 인기도 (체류력 감각)")
        scat = data_r[["main_artist","track_name","age_years","popularity","resid"]].dropna()
        st.caption("→ 오른쪽(오래됨)인데도 상단(인기도↑)에 위치한 점은 '체류력'이 좋습니다.")
        if not scat.empty:
            fig = px.scatter(scat, x="age_years", y="popularity", color="main_artist",
                             hover_data=["track_name","resid"], template=PX_TEMPLATE, opacity=0.9)
            fig.update_layout(height=460, xaxis_title="연식(년)", yaxis_title="인기도")
            if adv and st.session_state.get("show_trend", True) if 'show_trend' in st.session_state else True:
                xs = np.linspace(scat["age_years"].min(), scat["age_years"].max(), 100)
                ys = a + b*xs
                fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=f"추세선 y≈{a:.1f}+{b:.2f}x",
                                         line=dict(dash="dash")))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("산점도를 그릴 데이터가 부족합니다.")

    with tab3:
        st.subheader("🏆 체류지표 상위 TOP 10")
        top_stay = (data_r.loc[data_r["staying_index"].notna(),
                    ["main_artist","track_name","staying_index"]]
                    .sort_values("staying_index", ascending=False).head(10))
        if not top_stay.empty:
            fig = px.bar(top_stay, x="staying_index", y="track_name", color="main_artist",
                         orientation="h", template=PX_TEMPLATE,
                         title="체류지표 (높을수록 연식 대비 인기 유지)")
            fig.update_layout(height=520, yaxis={'categoryorder':'total ascending'},
                              xaxis_title="staying_index", yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(top_stay, use_container_width=True)

    with tab4:
        st.subheader("👥 그룹별 평균 비교")
        grp = (data_r.groupby("main_artist")
               .agg(avg_staying=("staying_index","mean"),
                    avg_pop=("popularity","mean"),
                    avg_age=("age_years","mean"),
                    n=("track_name","count")).reset_index())
        if not grp.empty:
            colX, colY = st.columns(2)
            with colX:
                figg = px.bar(grp.sort_values("avg_staying", ascending=False),
                              x="main_artist", y="avg_staying", text=grp["n"],
                              template=PX_TEMPLATE, title="그룹별 평균 체류지표")
                figg.update_traces(texttemplate="%{text}곡", textposition="outside")
                figg.update_layout(height=420, xaxis_title="그룹", yaxis_title="평균 staying_index")
                st.plotly_chart(figg, use_container_width=True)
            with colY:
                figp = px.bar(grp.sort_values("avg_pop", ascending=False),
                              x="main_artist", y="avg_pop", template=PX_TEMPLATE,
                              title="그룹별 평균 인기도")
                figp.update_layout(height=420, xaxis_title="그룹", yaxis_title="평균 popularity")
                st.plotly_chart(figp, use_container_width=True)

    with tab5:
        st.subheader("📈 연도별 평균 인기도 / 체류지표 추이")
        tdf = data_r.dropna(subset=["release_year"])[["main_artist","release_year","popularity","staying_index"]]
        if not tdf.empty:
            pop_year = tdf.groupby(["main_artist","release_year"])["popularity"].mean().reset_index()
            st.plotly_chart(px.line(pop_year, x="release_year", y="popularity",
                                    color="main_artist", markers=True,
                                    template=PX_TEMPLATE, title="연도별 평균 인기도"),
                            use_container_width=True)
            stay_year = tdf.groupby(["main_artist","release_year"])["staying_index"].mean().reset_index()
            st.plotly_chart(px.line(stay_year, x="release_year", y="staying_index",
                                    color="main_artist", markers=True,
                                    template=PX_TEMPLATE, title="연도별 평균 체류지표"),
                            use_container_width=True)

    with tab6:
        st.subheader("🎚️ 오디오 특성 비교")
        if lite:
            st.info("라이트 모드입니다. 오디오 특성을 로드하려면 라이트 모드를 끄고 다시 불러오세요.")
        else:
            st.info("오디오 특성은 환경에 따라 제공되지 않을 수 있습니다.")

    with tab7:
        st.subheader("🩺 그룹별 연식→인기도 기울기/상관 진단")
        rows = []
        for g, gdf in data_r.groupby("main_artist"):
            a_g, b_g, r_g, r2_g = fit_line(gdf["age_years"], gdf["popularity"])
            rows.append({"group": g, "slope(b)": b_g, "intercept(a)": a_g, "corr(r)": r_g, "r2": r2_g, "n": len(gdf)})
        st.dataframe(pd.DataFrame(rows).round(3).sort_values("corr(r)", ascending=True), use_container_width=True)

    with tab8:
        st.subheader("📈 잔차(과성과/저성과) 분석 — 전역 회귀 기준")
        if "resid" in data_r.columns and data_r["resid"].notna().any():
            over = data_r.sort_values("resid", ascending=False).head(15)[
                ["main_artist","track_name","age_years","popularity","pred_pop","resid"]
            ]
            under = data_r.sort_values("resid", ascending=True).head(15)[
                ["main_artist","track_name","age_years","popularity","pred_pop","resid"]
            ]
            cL, cR = st.columns(2)
            cL.markdown("**👍 과성과(카탈로그 강세) TOP 15**"); cL.dataframe(over, use_container_width=True, height=360)
            cR.markdown("**🛠️ 저성과(재활성 대상) TOP 15**"); cR.dataframe(under, use_container_width=True, height=360)

    with tab9:
        st.subheader("📄 원본 데이터")
        show_cols = [c for c in [
            "main_artist","track_name","album_name","album_release_date","release_year",
            "popularity","pred_pop","resid","age_years","staying_index","duration_min"
        ] if c in data_r.columns]
        st.dataframe(
            data_r[show_cols].sort_values(["main_artist", sort_key], ascending=[True, False]),
            use_container_width=True, height=520
        )
        if want_download:
            csv = data_r[show_cols].to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ 전체 CSV 다운로드", data=csv, file_name="staying_full.csv", mime="text/csv")