# spotify_dashboard.py

import streamlit as st
import pandas as pd
from pathlib import Path
import json
import plotly.express as px

st.set_page_config(page_title="Spotify Wrapped Dashboard", layout="wide")
st.title("🎵 My Spotify Wrapped Dashboard (Interactive)")

# -------------------------
# 1️⃣ Load Data
# -------------------------
BASE_DIR = Path("..") / "data"
streaming_path = BASE_DIR / "streaming-history"
account_path = BASE_DIR / "account-data"

# Streaming History
streaming_files = list(streaming_path.glob("Streaming_History*.json"))
dfs = [pd.read_json(f) for f in streaming_files]
streaming_df = pd.concat(dfs, ignore_index=True)
streaming_df["ts"] = pd.to_datetime(streaming_df["ts"])
streaming_df["minutes_played"] = streaming_df["ms_played"] / 60000
streaming_df['year'] = streaming_df['ts'].dt.year
streaming_df['month'] = streaming_df['ts'].dt.month_name()

# Playlists
playlist_files = list(account_path.glob("Playlist*.json"))
playlist_list = []

for f in playlist_files:
    try:
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict) and "playlists" in data:
            playlist_list.extend(data["playlists"])
        elif isinstance(data, list):
            playlist_list.extend(data)
    except Exception as e:
        st.write(f"Failed to read {f.name}: {e}")

playlist_records = []
for playlist in playlist_list:
    playlist_meta = {
        "name": playlist.get("name"),
        "lastModifiedDate": playlist.get("lastModifiedDate"),
        "collaborators": playlist.get("collaborators")
    }
    items = playlist.get("items", [])
    if isinstance(items, dict):
        items = [items]
    elif not isinstance(items, list):
        items = []
    for item in items:
        if isinstance(item, dict):
            track_data = item.get("track", {})
            record = {**playlist_meta, **track_data}
            playlist_records.append(record)

all_tracks = pd.DataFrame(playlist_records)

# Search Queries
try:
    searches = pd.read_json(account_path / "SearchQueries.json")
except:
    searches = pd.DataFrame()

# -------------------------
# 2️⃣ Year Filter
# -------------------------
available_years = streaming_df['year'].dropna().unique()
selected_year = st.selectbox("Select Year to Filter Dashboard", sorted(available_years, reverse=True))
df_year = streaming_df[streaming_df['year'] == selected_year].copy()

# -------------------------
# 3️⃣ Summary Stats
# -------------------------
st.header(f"Summary - {selected_year}")
st.markdown(f"**Total minutes played:** {df_year['minutes_played'].sum():,.0f}")
st.markdown(f"**Total tracks played:** {df_year.shape[0]:,}")
st.markdown(f"**Total playlists:** {all_tracks['name'].nunique() if not all_tracks.empty and 'name' in all_tracks.columns else 0}")

# -------------------------
# 4️⃣ Top Artists & Tracks
# -------------------------
st.header(f"Top 10 Artists - {selected_year}")
if "master_metadata_album_artist_name" in df_year.columns:
    top_artists = (
        df_year.groupby("master_metadata_album_artist_name")["minutes_played"]
        .sum().sort_values(ascending=False).head(10)
    )
    fig = px.bar(top_artists, x=top_artists.values, y=top_artists.index, orientation='h', labels={'x':'Minutes Played','y':'Artist'})
    st.plotly_chart(fig, use_container_width=True)

st.header(f"Top 10 Tracks - {selected_year}")
if "master_metadata_track_name" in df_year.columns:
    top_tracks = (
        df_year.groupby("master_metadata_track_name")["minutes_played"]
        .sum().sort_values(ascending=False).head(10)
    )
    fig = px.bar(top_tracks, x=top_tracks.values, y=top_tracks.index, orientation='h', labels={'x':'Minutes Played','y':'Track'})
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# 5️⃣ Top Artists per Year
# -------------------------
st.header("Top 10 Artists Per Year (All Years)")
top_artists_per_year = (
    streaming_df.groupby(['year', 'master_metadata_album_artist_name'])
    .agg(total_minutes=('minutes_played', 'sum'))
    .reset_index()
)
top_artists_per_year['rank'] = (
    top_artists_per_year.groupby('year')['total_minutes']
    .rank(method='first', ascending=False)
)
top10_artists_per_year = top_artists_per_year[top_artists_per_year['rank'] <= 10]
st.dataframe(top10_artists_per_year)

# -------------------------
# 6️⃣ Listening Trends Over Time
# -------------------------
st.header(f"Listening Trends Over Time - {selected_year}")
if not df_year.empty:
    daily_minutes = df_year.set_index("ts")["minutes_played"].resample("D").sum()
    fig = px.line(daily_minutes, x=daily_minutes.index, y=daily_minutes.values, labels={'x':'Date','y':'Minutes Played'}, title="Daily Listening")
    st.plotly_chart(fig, use_container_width=True)

    monthly_minutes = df_year.set_index("ts")["minutes_played"].resample("M").sum()
    fig = px.line(monthly_minutes, x=monthly_minutes.index, y=monthly_minutes.values, labels={'x':'Month','y':'Minutes Played'}, title="Monthly Listening")
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# 7️⃣ Playlists Insights
# -------------------------
st.header("Playlists Insights")
if not all_tracks.empty and "name" in all_tracks.columns:
    playlist_sizes = all_tracks.groupby("name").size().sort_values(ascending=False).head(10)
    fig = px.bar(playlist_sizes, x=playlist_sizes.values, y=playlist_sizes.index, orientation='h', labels={'x':'Number of Tracks','y':'Playlist'})
    st.plotly_chart(fig, use_container_width=True)

    if "artistName" in all_tracks.columns:
        top_playlist_artists = all_tracks.groupby("artistName")["trackName"].count().sort_values(ascending=False).head(10)
        fig = px.bar(top_playlist_artists, x=top_playlist_artists.values, y=top_playlist_artists.index, orientation='h', labels={'x':'Number of Tracks','y':'Artist'}, title="Top Artists in Playlists")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No playlist data available.")

# -------------------------
# 8️⃣ Search Queries
# -------------------------
st.header("Top Search Queries")
if not searches.empty and "searchQuery" in searches.columns:
    top_searches = searches["searchQuery"].value_counts().head(10)
    fig = px.bar(top_searches, x=top_searches.values, y=top_searches.index, orientation='h', labels={'x':'Count','y':'Search Query'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No search queries found.")

# -------------------------
# 9️⃣ Optional Insights
# -------------------------
st.header("Optional Insights")
if "platform" in df_year.columns:
    platform_minutes = df_year.groupby("platform")["minutes_played"].sum()
    fig = px.bar(platform_minutes, x=platform_minutes.values, y=platform_minutes.index, orientation='h', labels={'x':'Minutes Played','y':'Platform'})
    st.plotly_chart(fig, use_container_width=True)

if "shuffle" in df_year.columns:
    shuffle_minutes = df_year.groupby("shuffle")["minutes_played"].sum()
    fig = px.bar(shuffle_minutes, x=shuffle_minutes.values, y=shuffle_minutes.index, orientation='h', labels={'x':'Minutes Played','y':'Shuffle Enabled'})
    st.plotly_chart(fig, use_container_width=True)
