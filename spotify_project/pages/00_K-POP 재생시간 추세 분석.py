# kpop_duration_analysis_big.py
import os
import re
import math
import pandas as pd
import plotly.express as px
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from urllib.parse import urlparse

# =========================
# 설정: Spotify API 인증
# =========================
CLIENT_ID = "7cb475144edb4b40b2f687052c79c378"
CLIENT_SECRET = "bce6af21bbe04caaaaa5ec7740e70cea"

if not CLIENT_ID or not CLIENT_SECRET:
    st.error("Spotify CLIENT_ID / CLIENT_SECRET가 설정되지 않았습니다.")
    st.stop()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID, client_secret=CLIENT_SECRET
))

# =========================
# 유틸: 날짜 파싱 & 연도 필터
# =========================
def parse_release_date(s):
    try:
        return pd.to_datetime(s, errors="coerce")
    except Exception:
        return pd.NaT

def filter_2020_2025(df):
    df = df.copy()
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["release_year"] = df["release_date"].dt.year
    return df[(df["release_year"] >= 2020) & (df["release_year"] <= 2025)]

# =========================
# 수집 모드 1: 장르 검색(빠름)
# =========================
@st.cache_data(show_spinner=False)
def fetch_kpop_by_genre(total=200, market="KR"):
    all_rows = []
    fetched = 0
    for offset in range(0, total, 50):
        limit = min(50, total - fetched)
        res = sp.search(q='genre:"k-pop"', type="track", limit=limit, offset=offset, market=market)
        items = res.get("tracks", {}).get("items", [])
        for it in items:
            all_rows.append({
                "track_id": it["id"],
                "track_name": it["name"],
                "artist": ", ".join([a["name"] for a in it["artists"]]),
                "album": it["album"]["name"],
                "release_date": it["album"]["release_date"],
                "duration_min": it["duration_ms"] / 60000.0
            })
        fetched += len(items)
        if len(items) < limit:
            break
    df = pd.DataFrame(all_rows).drop_duplicates(subset=["track_id"])
    df = filter_2020_2025(df)
    return df

# =========================
# 수집 모드 2: 아티스트 기반(정확)
# =========================
DEFAULT_KPOP_ARTISTS = [
    "BTS", "BLACKPINK", "NewJeans", "SEVENTEEN", "TWICE", "NCT", "EXO",
    "IVE", "LE SSERAFIM", "Stray Kids", "ATEEZ", "TXT", "ENHYPEN", "ITZY",
    "aespa", "Red Velvet", "(G)I-DLE", "TREASURE", "fromis_9",
    "STAYC", "ILLIT", "I.N", "BOYNEXTDOOR", "ZEROBASEONE", "KISS OF LIFE",
    "RIIZE", "SHINee", "SNSD", "Super Junior", "MONSTA X", "MAMAMOO", "BIGBANG",
    "Sunmi", "TAEYANG", "TAEMIN", "JENNIE", "JISOO", "ROSÉ", "LISA", "Jung Kook",
    "Jimin", "SUGA", "J-Hope", "V", "Agust D"
]

def search_artist_id(name: str):
    res = sp.search(q=name, type="artist", limit=1)
    items = res.get("artists", {}).get("items", [])
    return items[0]["id"] if items else None

def fetch_artist_tracks_in_years(artist_id: str, country="KR", max_albums=30):
    rows = []
    seen_album_ids = set()
    for album_type in ["single", "album", "compilation", "appears_on"]:
        offset = 0
        while True:
            albums = sp.artist_albums(artist_id, album_type=album_type, country=country, limit=50, offset=offset)
            items = albums.get("items", [])
            for alb in items:
                if alb["id"] in seen_album_ids:
                    continue
                seen_album_ids.add(alb["id"])
                rd = alb.get("release_date")
                dt = parse_release_date(rd)
                if pd.isna(dt):
                    continue
                year = dt.year
                if 2020 <= year <= 2025:
                    tracks = sp.album_tracks(alb["id"], limit=50)
                    for t in tracks.get("items", []):
                        dur_ms = t.get("duration_ms")
                        rows.append({
                            "track_id": t["id"],
                            "track_name": t["name"],
                            "artist": ", ".join([a["name"] for a in t["artists"]]),
                            "album": alb["name"],
                            "release_date": rd,
                            "duration_min": (dur_ms or 0) / 60000.0
                        })
            if len(items) < 50 or len(seen_album_ids) >= max_albums:
                break
            offset += 50
    df = pd.DataFrame(rows).drop_duplicates(subset=["track_id"])
    df = filter_2020_2025(df)
    return df

@st.cache_data(show_spinner=False)
def fetch_kpop_by_artists(artists: list, max_albums_per_artist=20, country="KR", target_total=300):
    all_df = []
    for name in artists:
        aid = search_artist_id(name)
        if not aid:
            continue
        df_a = fetch_artist_tracks_in_years(aid, country=country, max_albums=max_albums_per_artist)
        if not df_a.empty:
            all_df.append(df_a)
        if sum(len(x) for x in all_df) >= target_total:
            break
    if all_df:
        big = pd.concat(all_df, ignore_index=True).drop_duplicates(subset=["track_id"])
        return big
    return pd.DataFrame(columns=["track_id","track_name","artist","album","release_date","duration_min","release_year"])

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="K-pop 재생시간 분석(2020–2025)", page_icon="⏱️", layout="wide")
st.title("⏱️ K-pop 재생시간 추세 분석 (2020–2025)")

st.markdown("""
- 더 많은 곡을 안정적으로 수집하기 위해 **2가지 수집 모드**를 제공합니다.  
  1) **장르 검색(빠름)**: `genre:"k-pop"` 검색으로 다중 페이지 수집 (빠르지만 누락 가능)  
  2) **아티스트 기반(정확)**: K-pop 아티스트들의 앨범/싱글에서 2020–2025 트랙만 수집 (권장)  
""")

# 중앙 상단 가로 UI
c1, c2, c3, c4 = st.columns([2,2,2,1])
with c1:
    mode = st.selectbox("수집 모드", ["아티스트 기반(권장)", "장르 검색(빠름)"])
with c2:
    market = st.selectbox("Market(국가)", ["KR", "US", "JP", "GB", "DE", "None"], index=0)
    market_val = None if market == "None" else market
with c3:
    if mode == "장르 검색(빠름)":
        total = st.slider("수집할 목표 곡 수", 50, 500, 300, step=50)
        max_albums = None
        artists = []
    else:
        total = st.slider("목표 총곡(대략)", 100, 600, 300, step=50)
        max_albums = st.slider("아티스트당 최대 앨범 수집", 5, 50, 20, step=5)
        artist_text = st.text_area(
            "아티스트 목록(줄바꿈으로 구분)",
            "\n".join(DEFAULT_KPOP_ARTISTS),
            height=180
        )
        artists = [a.strip() for a in artist_text.splitlines() if a.strip()]
with c4:
    load_btn = st.button("데이터 불러오기")

# =========================
# 데이터 로딩
# =========================
if load_btn:
    with st.spinner("Spotify에서 데이터 수집 중..."):
        if mode == "장르 검색(빠름)":
            df = fetch_kpop_by_genre(total=total, market=market_val or "KR")
        else:
            df = fetch_kpop_by_artists(artists, max_albums_per_artist=max_albums, country=market_val or "KR", target_total=total)

    if df.empty:
        st.warning("조건에 맞는 2020–2025 데이터가 없습니다. (Market/아티스트 목록을 확인하세요)")
        st.stop()

    df = df.dropna(subset=["release_date"])
    df["release_year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year
    df = df.dropna(subset=["release_year"])
    df["duration_min"] = pd.to_numeric(df["duration_min"], errors="coerce")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("수집 곡 수", f"{len(df):,}")
    with c2:
        st.metric("고유 아티스트 수", f"{df['artist'].nunique():,}")
    with c3:
        st.metric("분석 기간", "2020–2025")

    tab1, tab2, tab3, tab4 = st.tabs([
        "연도별 평균 재생시간", "재생시간 분포(바이올린)", "조사된 곡 목록", "원본 데이터"
    ])

    with tab1:
        year_avg = df.groupby("release_year", as_index=False)["duration_min"].mean()
        fig = px.line(
            year_avg, x="release_year", y="duration_min",
            markers=True, line_shape="spline",
            labels={"release_year": "연도", "duration_min": "평균 재생시간(분)"},
            title="연도별 평균 재생시간 (2020–2025)"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        top_artists = (
            df.groupby("artist")["track_id"].nunique()
              .sort_values(ascending=False)
              .head(12).index.tolist()
        )
        df_violin = df.copy()
        df_violin["artist_top12"] = df_violin["artist"].apply(lambda a: a if a in top_artists else "기타")
        fig = px.violin(
            df_violin, y="duration_min", x="artist_top12",
            box=True, points="all",
            category_orders={"artist_top12": top_artists + ["기타"]},
            labels={"artist_top12":"아티스트(상위 12 + 기타)", "duration_min":"재생시간(분)"},
            title="아티스트별 재생시간 분포 (상위 12 + 기타)"
        )
        fig.update_layout(height=800, width=1200)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("🎵 조사된 K-pop 곡 목록 (2020–2025)")
        q = st.text_input("곡명/아티스트/앨범 검색")
        view = df[["track_name", "artist", "album", "release_year", "duration_min"]].copy()
        if q:
            q_low = q.lower()
            mask = (
                view["track_name"].str.lower().str.contains(q_low, na=False) |
                view["artist"].str.lower().str.contains(q_low, na=False) |
                view["album"].str.lower().str.contains(q_low, na=False)
            )
            view = view[mask]
        st.dataframe(view.sort_values(["release_year", "artist", "track_name"]), use_container_width=True)

    with tab4:
        st.dataframe(df, use_container_width=True)
