import streamlit as st
import sqlite3
import os
import time
import requests
import json
from datetime import datetime
from google_play_scraper import search as play_search, app as play_scraper, reviews as play_reviews
from app_store_web_scraper import AppStoreEntry  # Futurice 2024: urllib3 pure, lazy batches
import re
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from supabase import create_client, Client
nltk.download('vader_lexicon', quiet=True)

st.set_page_config(layout="wide", page_title="AppWhistler AI", page_icon="🔍", initial_sidebar_state="expanded")

# Cloud-hardened paths: Windows local absolute, cloud /tmp ephemeral
if 'streamlit' in os.environ.get('STREAMLIT_SERVER_HEADLESS', ''):
    db_path = '/tmp/appwhistler.db'
    base_dir = '/tmp'
else:
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, "appwhistler", "appwhistler.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

POPULAR_APPS = {
    "facebook": {"play": "com.facebook.katana", "appstore": "284882215"},
    "whatsapp": {"play": "com.whatsapp", "appstore": "310633997"},
    "tiktok": {"play": "com.zhiliaoapp.musically", "appstore": "835599320"},
    "google": {"play": "com.google.android.googlequicksearchbox", "appstore": "284815942"},
    "instagram": {"play": "com.instagram.android", "appstore": "389801252"},
    "snapchat": {"play": "com.snapchat.android", "appstore": "447188370"},
    "twitter": {"play": "com.twitter.android", "appstore": "333903271"},
    "youtube": {"play": "com.google.android.youtube", "appstore": "544007664"},
    "netflix": {"play": "com.netflix.mediaclient", "appstore": "363590051"},
    "spotify": {"play": "com.spotify.music", "appstore": "324684580"},
    "amazon": {"play": "com.amazon.mShop.android.shopping", "appstore": "297606951"},
    "uber": {"play": "com.ubercab", "appstore": "368677368"},
    "linkedin": {"play": "com.linkedin.android", "appstore": "543256656"},
    "pinterest": {"play": "com.pinterest", "appstore": "429047995"},
    "reddit": {"play": "com.reddit.frontpage", "appstore": "1064216828"},
    "discord": {"play": "com.discord", "appstore": "985746746"},
    "clash of clans": {"play": "com.supercell.clashofclans", "appstore": "529479190"},
    "candy crush": {"play": "com.king.candycrushsaga", "appstore": "553834731"},
    "fortnite": {"play": "com.epicgames.fortnite", "appstore": "1261357853"},
    "roblox": {"play": "com.roblox.client", "appstore": "431946152"},
    "messenger": {"play": "com.facebook.orca", "appstore": "454638411"},
    "capcut": {"play": "com.lemon.lvoverseas", "appstore": "1500855883"},
    "telegram": {"play": "org.telegram.messenger", "appstore": "686449807"},
    "cash app": {"play": "com.squareup.cash", "appstore": "711923939"},
    "zoom": {"play": "us.zoom.videomeetings", "appstore": "546505307"},
    "gmail": {"play": "com.google.android.gm", "appstore": "422689480"},
    "google maps": {"play": "com.google.android.apps.maps", "appstore": "585027354"},
    "shazam": {"play": "com.shazam.android", "appstore": "284993459"},
    "duolingo": {"play": "com.duolingo", "appstore": "570060128"},
    "amazon prime video": {"play": "com.amazon.avod.thirdpartyclient", "appstore": "545519333"},
    "disney+": {"play": "com.disney.disneyplus", "appstore": "1446075923"},
    "hulu": {"play": "com.hulu.plus", "appstore": "376510438"},
    "paypal": {"play": "com.paypal.android.p2pmobile", "appstore": "283646709"},
    "venmo": {"play": "com.venmo", "appstore": "351727428"},
    "robinhood": {"play": "com.robinhood.android", "appstore": "938738207"},
    "coinbase": {"play": "com.coinbase.android", "appstore": "886427730"},
    "tinder": {"play": "com.tinder", "appstore": "547702041"},
    "bumble": {"play": "com.bumble.app", "appstore": "930441707"},
    "hinge": {"play": "co.hinge.app", "appstore": "595287172"},
    "minecraft": {"play": "com.mojang.minecraftpe", "appstore": "479516143"},
    "among us": {"play": "com.innersloth.spacemafia", "appstore": "1351168404"},
    "pubg mobile": {"play": "com.tencent.ig", "appstore": "1330123889"},
    "call of duty mobile": {"play": "com.activision.callofduty.shooter", "appstore": "1373869167"},
    "genshin impact": {"play": "com.miHoYo.GenshinImpact", "appstore": "1463168837"},
    "pokemon go": {"play": "com.nianticlabs.pokemongo", "appstore": "1094591345"},
    "waze": {"play": "com.waze", "appstore": "323229106"},
    "lyft": {"play": "me.lyft.android", "appstore": "529379082"},
    "doordash": {"play": "com.doordash.driverapp", "appstore": "719972451"},
    "uber eats": {"play": "com.ubercab.eats", "appstore": "1058959277"},
    "grubhub": {"play": "com.grubhub.android", "appstore": "302920553"},
    "apple music": {"play": "com.apple.android.music", "appstore": "1108187390"},
    "youtube music": {"play": "com.google.android.apps.youtube.music", "appstore": "1017492454"},
    "pandora": {"play": "com.pandora.android", "appstore": "284035177"},
    "soundcloud": {"play": "com.soundcloud.android", "appstore": "336353151"},
    "twitch": {"play": "tv.twitch.android.app", "appstore": "460177396"},
    "ebay": {"play": "com.ebay.mobile", "appstore": "282614216"},
    "walmart": {"play": "com.walmart.android", "appstore": "338137227"},
    "target": {"play": "com.target.ui", "appstore": "297430070"},
    "best buy": {"play": "com.bestbuy.android", "appstore": "375983029"},
    "fitbit": {"play": "com.fitbit.FitbitMobile", "appstore": "462638897"},
    "myfitnesspal": {"play": "com.myfitnesspal.android", "appstore": "341232718"},
    "headspace": {"play": "com.getsomeheadspace.android", "appstore": "442980891"},
    "calm": {"play": "com.calm.android", "appstore": "571800810"},
    "chatgpt": {"play": "com.openai.chatgpt", "appstore": "6448311069"},
    "threads": {"play": "com.instagram.barcelona", "appstore": "6446901002"},
    "temu": {"play": "com.einnovation.temu", "appstore": "1659253786"},
    "ticketmaster": {"play": "com.ticketmaster.mobile.android.na", "appstore": "500003565"},
    "shein": {"play": "com.zzkko", "appstore": "878577630"},
    "vinted": {"play": "fr.vinted", "appstore": "719419464"},
    "monzo bank": {"play": "co.monzo.android", "appstore": "931440173"}
}

try:
    secrets = st.secrets
    hf_token = secrets.get("hf_token", "")
except (FileNotFoundError, AttributeError):
    hf_token = os.environ.get("HF_TOKEN", "")

debug_mode = st.sidebar.checkbox("Debug Mode (Logs to Console)")

def log_debug(msg):
    if debug_mode:
        print(f"DEBUG: {msg}")
        st.sidebar.write(f"DEBUG: {msg}")

# Supabase eternal weave
supabase_url = st.secrets.get("supabase_url", "")
supabase_key = st.secrets.get("supabase_key", "")
supabase = None
if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)
    log_debug("Supabase eternal forged")

def init_db_supabase():
    if supabase:
        try:
            response = supabase.table('apps').select('id').limit(1).execute()
            log_debug("Supabase connected—table sanctified")
            return True
        except Exception as e:
            log_debug(f"Supabase probe falter: {e}")
            st.error(f"Supabase rift: {e}. Falling to local DB.")
    return init_db()  # Fallback SQLite

def save_to_db_supabase(app_name, pros, cons, truth_score, truth_color, app_id, store, issues, review_texts, icon_url, ai_summary, created_at):
    if supabase:
        data = {
            "name": app_name, "pros": pros, "cons": cons, "truth_score": truth_score,
            "truth_color": truth_color, "app_id": app_id, "store": store,
            "issues": issues, "review_texts": review_texts, "icon_url": icon_url,
            "ai_summary": ai_summary, "created_at": created_at
        }
        response = supabase.table('apps').upsert(data, on_conflict='app_id').execute()
        if response.data:
            log_debug(f"Eternal etch: {app_name}")
        else:
            st.error("Supabase insert rift")
    else:
        save_to_db(conn, app_name, pros, cons, truth_score, truth_color, app_id, store, issues, review_texts, icon_url, ai_summary)  # Fallback

def get_history_supabase():
    if supabase:
        response = supabase.table('apps').select("name, store, truth_score, truth_color, created_at").order('created_at', desc=True).limit(20).execute()
        return response.data or []
    return []  # Fallback

# SQLite fallback (unchanged from prior)
def init_db(reset=False):
    # ... (full init_db code from prior phoenix, with retries, migration, indexes)

def save_to_db(conn, app_name, pros, cons, truth_score, truth_color, app_id, store, issues, review_texts, icon_url, ai_summary):
    # ... (full save_to_db code from prior)

# Scraper probe validator
try:
    test_app = AppStoreEntry(app_id="1108187390", country="us")
    log_debug("Scraper forged—urllib3 ready")
except Exception as e:
    log_debug(f"Scraper probe falter: {e}")

# [get_appstore_id, get_play_id, fetch_app_info, analyze_reviews, get_ai_summary - full from prior, with re.search for issues]

# UI/CSS zenith
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap');
    .stApp { background: linear-gradient(135deg, #f5f5f7 0%, #e5e5e7 100%); font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif; padding: 2rem; }
    .header { background: linear-gradient(135deg, #007aff 0%, #5856d6 100%); color: white; padding: 1.5rem; border-radius: 16px; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.1); margin-bottom: 2rem; }
    .app-card { background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 16px rgba(0,0,0,0.08); transition: all 0.3s ease; animation: fadeIn 0.6s ease-out; }
    .app-card:hover { transform: translateY(-4px) scale(1.02); box-shadow: 0 16px 40px rgba(0,0,0,0.15); }
    .app-card h3 { font-weight: 600; transition: font-weight 0.2s; }
    .app-card:hover h3 { font-weight: 700; }
    .stButton > button { background: linear-gradient(135deg, #007aff, #0056b3); color: white; border-radius: 12px; padding: 0.75rem 1.5rem; font-weight: 500; border: none; transition: all 0.3s; }
    .stButton > button:hover { background: linear-gradient(135deg, #0056b3, #004494); transform: scale(1.05); }
    .stTabs [data-baseweb="tab"] { font-weight: 500; color: #8e8e93; transition: all 0.2s; }
    .stTabs [data-baseweb="tab"]:hover { color: #007aff; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #007aff; border-bottom: 2px solid #007aff; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .logo { width: 48px; height: 48px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.15); transition: all 0.3s; }
    .logo:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.2); transform: scale(1.1); }
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 4])
with col1:
    # Base64 xAI logo embed (copy full base64 from browser dev tools on x.ai; fallback URL)
    st.markdown('<img src="https://x.ai/wp-content/uploads/2023/10/xai-logo.png" class="logo" alt="xAI Logo">', unsafe_allow_html=True)
with col2:
    st.markdown('<h1 style="margin: 0; font-weight: 700; color: #1d1d1f;">AppWhistler AI</h1><p style="margin: 0; color: #8e8e93;">Truthful App Insights, Powered by Grok</p>', unsafe_allow_html=True)

init_db_supabase()  # Eternal DB ignite

tab1, tab2, tab3 = st.tabs(["🏠 Home", "🔍 Search", "📜 History"])

with tab1:
    # ... (full Home tab code from prior, with app_keys[:16], app-card HTML)

with tab2:
    # ... (full Search tab code from prior, with text_input, selectbox, button, spinner, try-except, app-card result HTML, save_to_db_supabase call)

with tab3:
    st.markdown('<div class="header"><h2 style="margin: 0;">Search History</h2><p style="margin: 0; opacity: 0.9;">Timestamps tell the tale</p></div>', unsafe_allow_html=True)
    history = get_history_supabase()
    if history:
        for row in history:
            name = row['name']
            store = row['store']
            score = row['truth_score']
            color = row['truth_color']
            date_str = row['created_at'][:19] if row['created_at'] else "Ancient"
            st.markdown(f'<div class="app-card"><strong>{name}</strong> ({store.upper()}) - {score}/100 ({color})<br><small>{date_str}</small></div>', unsafe_allow_html=True)
    else:
        st.info("Barren—ignite a search!")

st.markdown("""
    <div style="text-align: center; padding: 2rem; color: #8e8e93; font-size: 0.875rem; border-top: 1px solid #e5e5e7; margin-top: 2rem;">
        <p>Powered by Grok from xAI | Built for a truthful world 🚀 | Target: 100M+ by Dec 2026</p>
    </div>
""", unsafe_allow_html=True)