# streamlit_app.py
# 실행: streamlit run streamlit_app.py
# 필요: pip install streamlit pandas matplotlib seaborn

import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from matplotlib import font_manager as fm

# ===================== 기본 설정 =====================
st.set_page_config(page_title="Charlie Puth 트랙 분석 대시보드", layout="wide")

sns.set_theme(style="whitegrid")
# 한글 폰트 설정
try:
    plt.rcParams['font.family'] = 'Batang'
except:
    pass
plt.rcParams['axes.unicode_minus'] = False

ACCENT = "#5b8def"
MUTED  = "#8fa3bf"

def annotate_bar(ax):
    for p in ax.patches:
        h = p.get_height()
        if pd.isna(h): continue
        ax.annotate(f"{int(h):,}", (p.get_x()+p.get_width()/2, h),
                    ha="center", va="bottom", fontsize=9, color="#333", xytext=(0,3), textcoords="offset points")

def percent_axis(ax): ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
def to_mmss(x):
    if pd.isna(x): return ""
    x=float(x); m=int(x//60); s=int(round(x%60)); return f"{m:02d}:{s:02d}"

# ===================== 데이터 로드 & 보정 =====================
@st.cache_data
def load_csv(file):
    return pd.read_csv(file, encoding="utf-8-sig")

def prepare_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # artists_primary 없으면 artists_all에서 1번째 이름 추출
    if "artists_primary" not in df.columns:
        if "artists_all" in df.columns:
            df["artists_primary"] = df["artists_all"].fillna("").astype(str).str.split(",").str[0]
        else:
            df["artists_primary"] = ""

    # name_normalized 없으면 track_name을 소문자/공백정리
    if "name_normalized" not in df.columns and "track_name" in df.columns:
        df["name_normalized"] = df["track_name"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str.lower()

    # explicit은 bool로
    if "explicit" in df.columns:
        if df["explicit"].dtype != bool:
            m = {"true":True,"1":True,"t":True,"y":True,"yes":True,"false":False,"0":False,"f":False,"n":False,"no":False}
            df["explicit"] = df["explicit"].astype(str).str.lower().map(m).fillna(False)
    else:
        df["explicit"] = False

    # duration_sec 없으면 ms→sec
    if "duration_sec" not in df.columns and "duration_ms" in df.columns:
        df["duration_sec"] = pd.to_numeric(df["duration_ms"], errors="coerce")/1000.0

    # release_year 보강
    if "release_year" not in df.columns and "album_release_date" in df.columns:
        dt = pd.to_datetime(df["album_release_date"], errors="coerce")
        df["release_year"] = dt.dt.year

    # album_name 없으면 fallback
    if "album_name" not in df.columns:
        df["album_name"] = df.get("album", "")
        df["album_name"] = df["album_name"].fillna("").astype(str)
        df.loc[df["album_name"].eq(""), "album_name"] = "Unknown Album"

    # charlie_role 자동 추론 (없을 때만)
    if "charlie_role" not in df.columns:
        ap = df["artists_primary"].fillna("").astype(str).str.lower()
        aa = df.get("artists_all", pd.Series([""]*len(df))).fillna("").astype(str).str.lower()
        df["charlie_role"] = np.where(
            ap.str.contains("charlie puth"),
            "primary",
            np.where(aa.str.contains("charlie puth"), "featuring", "other")
        )

    return df

# ===================== UI =====================
st.markdown(
    """
    <style>
      .big-title {font-size: 28px; font-weight: 800; margin-bottom: 0.2rem;}
      .subtle   {color: #6b7a90; font-size: 13px;}
      .card {background: #f8fafc; border: 1px solid #eef2f7; padding: 14px 16px; border-radius: 12px;}
      .section-title {font-size: 20px; font-weight: 700; margin: 12px 0 4px 0;}
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown('<div class="big-title">🎶 Charlie Puth 트랙 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">`charlie_puth_min.cleaned.csv` 파일을 자동으로 분석합니다.</div>', unsafe_allow_html=True)

# --- CSV 파일 직접 로드 ---
file_path = "charlie_puth_min.cleaned.csv"
if not os.path.exists(file_path):
    st.error(f"'{file_path}' 파일을 찾을 수 없습니다. 스크립트와 동일한 폴더에 파일이 있는지 확인하세요.")
    st.stop()

df = prepare_columns(load_csv(file_path))


# ===================== 사이드바 필터 =====================
with st.sidebar:
    st.header("🔎 필터")
    if "release_year" in df.columns and df["release_year"].notna().any():
        y_min, y_max = int(np.nanmin(df["release_year"])), int(np.nanmax(df["release_year"]))
        year_range = st.slider("연도 범위", y_min, y_max, (y_min, y_max))
    else:
        year_range = (None, None)

    roles = sorted(df.get("charlie_role", pd.Series(["unknown"])).fillna("unknown").unique().tolist())
    role_sel = st.multiselect("역할 선택", roles, default=roles)

    exp_map = {"모두": "all", "Explicit만": "exp", "Clean만": "clean"}
    exp_choice = st.radio("Explicit 필터", list(exp_map.keys()), index=0, horizontal=True)
    exp_mode = exp_map[exp_choice]

    kw = st.text_input("제목/앨범/아티스트 검색", value="")

# ---- 필터 적용 ----
df_f = df.copy()
if year_range != (None, None) and "release_year" in df_f.columns:
    df_f = df_f[df_f["release_year"].between(year_range[0], year_range[1], inclusive="both")]
if "charlie_role" in df_f.columns:
    df_f = df_f[df_f["charlie_role"].fillna("unknown").isin(role_sel)]
if exp_mode != "all" and "explicit" in df_f.columns:
    df_f = df_f[df_f["explicit"] == (exp_mode == "exp")]
if kw:
    kw_l = kw.lower()
    cols = [c for c in ["track_name","album_name","artists_primary","name_normalized"] if c in df_f.columns]
    if cols:
        m = pd.Series(False, index=df_f.index)
        for c in cols:
            m = m | df_f[c].fillna("").astype(str).str.lower().str.contains(kw_l)
        df_f = df_f[m]

# ===================== KPI =====================
st.markdown('<div class="section-title">요약 KPI</div>', unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("총 곡 수", f"{len(df_f):,}")
    st.markdown('</div>', unsafe_allow_html=True)
if "duration_sec" in df_f.columns and len(df_f):
    with k2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric("평균 길이(초)", f"{df_f['duration_sec'].mean():.1f}")
        st.caption(f"≈ {to_mmss(df_f['duration_sec'].mean())}")
        st.markdown('</div>', unsafe_allow_html=True)
    with k3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric("중앙 길이(초)", f"{df_f['duration_sec'].median():.1f}")
        st.caption(f"≈ {to_mmss(df_f['duration_sec'].median())}")
        st.markdown('</div>', unsafe_allow_html=True)
if "explicit" in df_f.columns and len(df_f):
    with k4:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric("Explicit 비율", f"{df_f['explicit'].mean()*100:.1f}%")
        st.caption("필터 조건 반영")
        st.markdown('</div>', unsafe_allow_html=True)

# ===================== 탭 =====================
tab_overview, tab_length, tab_explicit, tab_roles, tab_albums = st.tabs(
    ["📋 개요", "⏱ 길이 분석", "🔞 Explicit", "🎤 역할", "💿 앨범"]
)

# ---------- 개요 ----------
with tab_overview:
    st.markdown("#### 데이터 미리보기")
    st.dataframe(df_f.head(50), use_container_width=True)
    st.caption(f"행: {len(df_f):,}  |  컬럼: {len(df_f.columns)}")

    if {"release_year","duration_sec"}.issubset(df_f.columns) and len(df_f):
        yearly = df_f.groupby("release_year").agg(
            track_count=("track_name","count"),
            avg_duration=("duration_sec","mean")
        ).reset_index().sort_values("release_year")

        c1, c2 = st.columns([1.2, 1])
        with c1:
            fig, ax1 = plt.subplots(figsize=(9, 4.6), dpi=150)
            sns.lineplot(x="release_year", y="avg_duration", data=yearly, marker="o", label="평균", ax=ax1)
            sns.lineplot(x="release_year", y="track_count", data=yearly, marker="o", label="곡 수", ax=ax1)
            ax1.set_xlabel("연도"); ax1.set_ylabel("")
            ax1.legend(loc="upper left")
            st.pyplot(fig)

        with c2:
            st.markdown("**연도별 핵심 수치**")
            st.dataframe(yearly.style.format({"avg_duration":"{:.1f}"}), use_container_width=True)
    else:
        st.info("연도/길이 정보가 부족해 개요 그래프를 만들 수 없습니다.")

# ---------- 길이 분석 ----------
with tab_length:
    if "duration_sec" in df_f.columns and len(df_f):
        st.markdown("#### 길이 분포")
        c1, c2 = st.columns([1,1])
        with c1:
            fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
            sns.histplot(df_f["duration_sec"].dropna(), bins=30, kde=True, color=ACCENT, ax=ax)
            ax.set_xlabel("길이(초)"); ax.set_ylabel("곡 수")
            st.pyplot(fig)

        if "release_year" in df_f.columns:
            with c2:
                st.markdown("**연도별 평균/중앙 길이**")
                yr = df_f.groupby("release_year")["duration_sec"].agg(["mean","median"]).reset_index()
                fig2, axm = plt.subplots(figsize=(8, 4.2), dpi=150)
                sns.lineplot(x="release_year", y="mean", data=yr, marker="o", label="평균", color=ACCENT, ax=axm)
                sns.lineplot(x="release_year", y="median", data=yr, marker="o", label="중앙", color=MUTED, ax=axm)
                axm.set_xlabel("연도"); axm.set_ylabel("초"); axm.legend()
                st.pyplot(fig2)

        st.markdown("#### 최장/최단 트랙 Top 10")
        cols = [c for c in ["track_name","duration_sec","explicit","release_year","charlie_role","album_name","external_url"] if c in df_f.columns]
        if cols:
            left, right = st.columns(2)
            with left:
                st.markdown("**최장 Top 10**")
                top_long = df_f.sort_values("duration_sec", ascending=False).head(10)[cols].copy()
                if "duration_sec" in top_long: top_long["mm:ss"] = top_long["duration_sec"].map(to_mmss)
                st.dataframe(top_long, use_container_width=True)
            with right:
                st.markdown("**최단 Top 10**")
                top_short = df_f.sort_values("duration_sec", ascending=True).head(10)[cols].copy()
                if "duration_sec" in top_short: top_short["mm:ss"] = top_short["duration_sec"].map(to_mmss)
                st.dataframe(top_short, use_container_width=True)
        else:
            st.info("표시 가능한 컬럼이 부족합니다.")
    else:
        st.info("duration_sec 컬럼이 없어 길이 분석을 표시할 수 없습니다.")

# ---------- Explicit ----------
with tab_explicit:
    if "explicit" in df_f.columns and len(df_f):
        st.markdown("#### Explicit vs Clean")
        c1, c2 = st.columns([1,1])
        with c1:
            counts = df_f["explicit"].value_counts(dropna=False)
            labels = ["Explicit" if b else "Clean" for b in counts.index]
            fig, ax = plt.subplots(figsize=(5.6, 5.6), dpi=150)
            # ===== [수정된 부분] colors 인자를 삭제하여 원본 코드로 복구 =====
            ax.pie(counts, labels=labels, autopct="%1.1f%%", startangle=90)
            # ==========================================================
            ax.axis("equal")
            st.pyplot(fig)
        if "release_year" in df_f.columns:
            with c2:
                st.markdown("**연도별 Explicit 비율**")
                exp_year = df_f.groupby("release_year")["explicit"].mean().reset_index()
                fig2, ax2 = plt.subplots(figsize=(8, 4.2), dpi=150)
                sns.lineplot(x="release_year", y="explicit", data=exp_year, marker="o", color=ACCENT, ax=ax2)
                ax2.set_xlabel("연도"); ax2.set_ylabel("Explicit 비율")
                percent_axis(ax2)
                st.pyplot(fig2)

        if {"has_clean_explicit_pair","pair_role","clean_pair_group"}.issubset(df_f.columns):
            st.markdown("#### 클린·익스플리싯 페어링")
            pairs = df_f[df_f["has_clean_explicit_pair"] == True].copy()
            if len(pairs):
                pair_counts = pairs["pair_role"].value_counts().reindex(["clean","explicit"]).fillna(0)
                fig3, ax3 = plt.subplots(figsize=(6.5, 3.6), dpi=150)
                sns.barplot(x=pair_counts.index, y=pair_counts.values, color="#c9d7f2", ax=ax3)
                ax3.set_xlabel("역할"); ax3.set_ylabel("곡 수")
                annotate_bar(ax3)
                st.pyplot(fig3)
            else:
                st.info("감지된 클린·익스플리싯 페어가 없습니다.")
    else:
        st.info("explicit 컬럼이 없어 분석을 표시할 수 없습니다.")

# ---------- 역할 ----------
with tab_roles:
    if "charlie_role" in df_f.columns and len(df_f):
        st.markdown("#### 역할별 요약")
        role_summary = df_f.groupby("charlie_role").agg(
            track_count=("track_name","count"),
            explicit_ratio=("explicit","mean") if "explicit" in df_f.columns else ("track_name","size"),
            avg_duration=("duration_sec","mean") if "duration_sec" in df_f.columns else ("track_name","size"),
        ).reset_index().sort_values("track_count", ascending=False)
        if "explicit" not in df_f.columns: role_summary = role_summary.drop("explicit_ratio", axis=1)
        if "duration_sec" not in df_f.columns: role_summary = role_summary.drop("avg_duration", axis=1)


        c1, c2 = st.columns([1,1])
        with c1:
            st.dataframe(role_summary.style.format({"explicit_ratio":"{:.1%}", "avg_duration":"{:.1f}"}), use_container_width=True)
        with c2:
            fig, ax = plt.subplots(figsize=(7.5, 4), dpi=150)
            sns.barplot(x="charlie_role", y="track_count", data=role_summary, hue="charlie_role",
                        dodge=False, legend=False, palette="Set2", ax=ax)
            ax.set_xlabel("역할"); ax.set_ylabel("곡 수")
            annotate_bar(ax)
            st.pyplot(fig)
    else:
        st.info("charlie_role 컬럼이 없어 역할 분석을 표시할 수 없습니다.")

# ---------- 앨범 ----------
with tab_albums:
    if "album_name" in df_f.columns and len(df_f):
        st.markdown("#### 앨범별 요약")
        group_cols = ["album_name"]
        if "release_year" in df_f.columns: group_cols.append("release_year")
        album_sum = df_f.groupby(group_cols).agg(
            track_count=("track_name","count"),
            avg_duration=("duration_sec","mean") if "duration_sec" in df_f.columns else ("track_name","size"),
            explicit_ratio=("explicit","mean") if "explicit" in df_f.columns else ("track_name","size"),
        ).reset_index().sort_values(["track_count","avg_duration"], ascending=[False, True])
        if "duration_sec" not in df_f.columns: album_sum = album_sum.drop("avg_duration", axis=1)
        if "explicit" not in df_f.columns: album_sum = album_sum.drop("explicit_ratio", axis=1)


        st.dataframe(album_sum.head(30).style.format({"avg_duration":"{:.1f}","explicit_ratio":"{:.2%}"}),
                     use_container_width=True)

        topN = st.slider("상위 앨범 N", 5, 20, 10, key="album_slider")
        top_albums = album_sum.head(topN)
        fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
        sns.barplot(y="album_name", x="track_count", data=top_albums, color="#d9e6ff", ax=ax)
        ax.set_xlabel("곡 수"); ax.set_ylabel("앨범")
        for p in ax.patches:
            w = p.get_width()
            ax.annotate(f"{int(w)}", (w, p.get_y()+p.get_height()/2),
                        va="center", ha="left", fontsize=9, xytext=(3,0), textcoords="offset points")
        st.pyplot(fig)
    else:
        st.info("album_name 컬럼이 없어 앨범 분석을 표시할 수 없습니다.")