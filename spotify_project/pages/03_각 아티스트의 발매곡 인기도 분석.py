import os, logging, spotipy
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 1. Spotipy 환경 설정

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=client_id,
    client_secret=client_secret
))

ACCENT = "#5b8def"
MUTED  = "#8fa3bf"

# 2-1. 아티스트 이름 기반 ID 검색 함수 정의

def get_artist_id(artist_name: str) -> str:
    result = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
    if result["artists"]["items"]:
        return result["artists"]["items"][0]["id"]
    else:
        raise ValueError(f"아티스트 '{artist_name}'를 찾을 수 없습니다.")

# 2-2. 아티스트 ID 기반 각 앨범별 인기도 계산 함수 정의

def get_album_popularity(artist_name: str, limit: int = 50) -> pd.DataFrame:

    # 0. 아티스트 ID 가져오기
    artist_id = get_artist_id(artist_name)

    # 1. 모든 앨범을 페이징 처리하여 가져오기
    albums = []
    offset = 0
    while True:
        result = sp.artist_albums(artist_id, album_type="album,single,compilation", limit=limit, offset=offset)
        items = result["items"]
        if not items:
            break
        albums.extend(items)
        offset += limit

    # 2. 앨범 정보 수집
    album_data = []
    for album in albums:
        album_id = album["id"]
        album_name = album["name"]
        release_date = album["release_date"]
        album_type = album["album_type"]

        # 2-1. 앨범의 트랙들 가져오기
        tracks = sp.album_tracks(album_id)["items"]
        track_ids = [t["id"] for t in tracks if t["id"]]
        if not track_ids:
            continue

        # 2-2. 트랙들의 세부 정보 가져오기 (50개 단위로 나눠 호출)
        track_infos = []
        for i in range(0, len(track_ids), 50):
            chunk = track_ids[i:i+50]
            track_infos.extend(sp.tracks(chunk)["tracks"])

        # 2-3. popularity 점수 추출
        popularities = [t["popularity"] for t in track_infos]

        if album_type == "single":
            # 2-3-1. 싱글이면 단일 트랙 popularity
            album_popularity = popularities[0]
        else:
            # 2-3-2. 정규 앨범/모음집이면 가장 인기 높은 곡의 popularity
            album_popularity = max(popularities)

        alb = {
            "Artist Name": artist_name,
            # "Artist Id": artist_id,
            "Album Name": album_name,
            "Album Type": album_type,
            "Release Date": release_date,
            "Album Popularity": album_popularity
        }
        album_data.append(alb)
        # logging.info(f"- 앨범 정보 수집 완료: [ {album_name} | {release_date} | {album_popularity} ]")

    # 3. DataFrame 변환 및 리턴
    df = pd.DataFrame(album_data).drop_duplicates(subset=["Album Name"])
    df = df.sort_values(by="Release Date", ascending=True).reset_index(drop=True)

    df.to_csv(f"{artist_name}_album_popularity.csv", index=False)
    # logging.info(f"앨범 인기도 정보가 '{artist_name}_album_popularity.csv'로 저장되었습니다.")

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
st.markdown('<div class="big-title">📈 각 아티스트의 발매곡 인기도 분석</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">검색한 아티스트의 앨범 인기도를 분석합니다.</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">앨범 검색에는 다소 시간이 걸릴 수 있습니다.</div>', unsafe_allow_html=True)

# ===================== 사이드바 필터 =====================
with st.sidebar:
    st.header("🔎 Search Query")

    query = st.text_input("아티스트 검색", value="")

# ===================== 필터 적용 =====================
if query:
    df = get_album_popularity(query)

# ===================== 탭 =====================

tab_overview, tab_popularity = st.tabs(
    ["📋 개요", "📈 인기도 분석"]
)

# ===================== 개요 탭 =====================

with tab_overview:
    st.markdown("### 앨범 개요")
    if query:
        st.dataframe(df.head(30), use_container_width=True)

    else:
        st.warning("검색된 앨범이 없습니다. 검색 아티스트를 입력해 주세요.")

# ===================== 인기도 분석 탭 =====================

with tab_popularity:
    st.markdown("### 인기도 분석")
    if query:
        c1, c2 = st.columns([1,1])
        with c1:
            st.markdown("**앨범 인기도 분포**")
            fig1, ax1 = plt.subplots(figsize=(12, 6), dpi=150)
            sns.histplot(df["Album Popularity"], bins=20, kde=True, color=ACCENT, ax=ax1)
            ax1.set_xlabel("인기도")
            ax1.set_ylabel("앨범 수")
            st.pyplot(fig1)

        with c2:
            st.markdown("**시계열 인기도 분포**")
            fig2, ax2 = plt.subplots(figsize=(12, 6), dpi=150)
            sns.lineplot(
                data=df,
                x="Release Date",
                y="Album Popularity",
                estimator="mean",
                color=ACCENT,
                ax=ax2
            )
            ax2.set_xlabel("발매일")
            ax2.set_ylabel("인기도")
            st.pyplot(fig2)

        st.markdown("#### 최고 인기 앨범 TOP 5")
        top_albums = df.nlargest(5, "Album Popularity")

        if top_albums.empty:
            st.warning("인기도가 높은 앨범이 없습니다.")

        st.dataframe(top_albums, use_container_width=True)

    else:
        st.warning("검색된 앨범이 없습니다. 검색 아티스트를 입력해 주세요.")