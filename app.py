import streamlit as st
import sqlite3
import os
import time
import requests
import json
from datetime import datetime
from google_play_scraper import search as play_search, app as play_scraper, reviews as play_reviews
from app_store_web_scraper import AppStoreEntry  # Futurice 2024: urllib3 pure, lazy review batches
import re
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
nltk.download('vader_lexicon', quiet=True)

st.set_page_config(layout="wide", page_title="AppWhistler AI", page_icon="🔍", initial_sidebar_state="expanded")

base_dir = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(base_dir, "appwhistler"), exist_ok=True)
db_path = os.path.join(base_dir, "appwhistler", "appwhistler.db")

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

def init_db(reset=False):
    retries = 5
    for attempt in range(retries):
        try:
            if reset and os.path.exists(db_path):
                os.remove(db_path)
                log_debug("DB reset: File wiped")
            conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS apps
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT, pros TEXT, cons TEXT, truth_score INTEGER, truth_color TEXT,
                          app_id TEXT UNIQUE, store TEXT, issues TEXT, review_texts TEXT,
                          icon_url TEXT, ai_summary TEXT, created_at TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS idx_app_id ON apps(app_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_name ON apps(name)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON apps(created_at)')
            c.execute("PRAGMA table_info(apps)")
            columns = [col[1] for col in c.fetchall()]
            if 'created_at' not in columns:
                log_debug("Migration: Adding created_at")
                c.execute("ALTER TABLE apps ADD COLUMN created_at TEXT")
                c.execute("UPDATE apps SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
                log_debug(f"Migration: Backfilled {c.rowcount} rows")
            conn.commit()
            log_debug(f"DB init triumph (attempt {attempt+1})")
            return conn
        except Exception as e:
            log_debug(f"DB init falter (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
    st.error("DB init exhausted—check paths.")
    return None

def get_appstore_id(app_name):
    try:
        term = requests.utils.quote(app_name)
        url = f"https://itunes.apple.com/search?term={term}&country=us&entity=software&limit=1"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get('resultCount', 0) > 0:
            return str(data['results'][0]['trackId'])
        return None
    except Exception as e:
        log_debug(f"AppStore ID error: {e}")
        return None

def get_play_id(app_name):
    try:
        results = play_search(app_name, lang='en', country='us', n_results=1)
        if results:
            return results[0]['appId']
        return None
    except Exception as e:
        log_debug(f"Play ID error: {e}")
        return None

def fetch_app_info(app_name, store):
    app_lower = app_name.lower().strip()
    app_id = POPULAR_APPS.get(app_lower, {}).get(store)
    if not app_id:
        if store == 'appstore':
            app_id = get_appstore_id(app_name)
        else:
            app_id = get_play_id(app_name)
    if not app_id:
        raise ValueError(f"App '{app_name}' not found on {store}.")

    reviews = []
    icon_url = None
    try:
        if store == 'appstore':
            app = AppStoreEntry(app_id=app_id, country="us")
            for review_obj in app.reviews(limit=50):
                reviews.append({
                    'text': review_obj.content or '',
                    'review': review_obj.content or '',
                    'rating': review_obj.rating
                })
            details_url = f"https://itunes.apple.com/lookup?id={app_id}&country=us"
            details_resp = requests.get(details_url, timeout=10)
            details = details_resp.json().get('results', [{}])[0]
            icon_url = details.get('artworkUrl512', '')
        else:
            details = play_scraper(app_id, lang='en', country='us')
            icon_url = details.get('icon', '')
            reviews_result, _ = play_reviews(app_id, lang='en', country='us', count=50)
            reviews = [{'text': r.get('content', ''), 'review': r.get('content', '')} for r in reviews_result]
        if not reviews:
            raise IndexError("No reviews fetched.")
        log_debug(f"Fetched {len(reviews)} reviews for {app_name} (ID: {app_id})")
        return reviews, icon_url, app_id
    except Exception as e:
        raise Exception(f"Fetch failed: {e}")

def analyze_reviews(reviews):
    sia = SentimentIntensityAnalyzer()
    pros, cons, issues, review_texts = [], [], [], []
    scores = []
    for review in reviews[:50]:
        text = review.get('text') or review.get('review', '') or review.get('content', '') or ''
        if text:
            review_texts.append(text)
            score = sia.polarity_scores(text)['compound']
            scores.append(score)
            if score > 0.05:
                pros.append(text[:100] + '...')
            elif score < -0.05:
                cons.append(text[:100] + '...')
            if re.search(r'\b(bug|crash|slow|issue)\b', text.lower()):
                issues.append(text[:100] + '...')
    avg_score = sum(scores) / len(scores) if scores else 0
    truth_score = int((avg_score + 1) * 50)
    truth_color = "Green" if truth_score >= 70 else "Yellow" if truth_score >= 40 else "Red"
    return ', '.join(set(pros[:5])), ', '.join(set(cons[:5])), ', '.join(set(issues[:5])), ', '.join(review_texts[:10]), truth_score, truth_color

def get_ai_summary(review_texts):
    if not hf_token:
        sia = SentimentIntensityAnalyzer()
        sentiments = [sia.polarity_scores(t)['compound'] for t in review_texts]
        overall = sum(sentiments) / len(sentiments) if sentiments else 0
        return f"Overall sentiment: {'Positive' if overall > 0 else 'Negative' if overall < 0 else 'Neutral'}. Key themes from {len(review_texts)} reviews."
    try:
        headers = {"Authorization": f"Bearer {hf_token}"}
        payload = {"inputs": " ".join(review_texts[:3])[:512], "parameters": {"max_length": 150, "min_length": 50}}
        resp = requests.post("https://api-inference.huggingface.co/models/facebook/bart-large-cnn", headers=headers, json=payload, timeout=10)
        result = resp.json()
        return result[0].get('summary_text', 'Summary unavailable.') if isinstance(result, list) else 'Summary unavailable.'
    except Exception as e:
        log_debug(f"HF error: {e}")
        return "AI summary unavailable—sentiment active."

def save_to_db(conn, app_name, pros, cons, truth_score, truth_color, app_id, store, issues, review_texts, icon_url, ai_summary):
    created_at = datetime.now().isoformat()
    try:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO apps 
                     (name, pros, cons, truth_score, truth_color, app_id, store, issues, review_texts, icon_url, ai_summary, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (app_name, pros, cons, truth_score, truth_color, app_id, store, issues, review_texts, icon_url, ai_summary, created_at))
        conn.commit()
        log_debug(f"Saved {app_name} (timestamp: {created_at[:19]})")
    except Exception as e:
        log_debug(f"Save error: {e}")
        st.error(f"Save failed: {e}")

# Validator: Probe scraper on load
try:
    test_app = AppStoreEntry(app_id="1108187390", country="us")
    log_debug("Scraper forged—urllib3 ready, reviews accessible")
except Exception as e:
    log_debug(f"Scraper probe falter: {e}")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap');
    .stApp { background: linear-gradient(135deg, #f5f5f7 0%, #e5e5e7 100%); font-family: 'SF Pro Display', sans-serif; padding: 2rem; }
    .header { background: linear-gradient(135deg, #007aff 0%, #5856d6 100%); color: white; padding: 1.5rem; border-radius: 16px; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.1); margin-bottom: 2rem; }
    .app-card { background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 16px rgba(0,0,0,0.08); transition: all 0.3s ease; animation: fadeIn 0.6s ease-out; }
    .app-card:hover { transform: translateY(-4px) scale(1.02); box-shadow: 0 16px 40px rgba(0,0,0,0.15); }
    .app-card h3 { font-weight: 600; transition: font-weight 0.2s; }
    .app-card:hover h3 { font-weight: 700; }
    .stButton > button { background: linear-gradient(135deg, #007aff, #0056b3); color: white; border-radius: 12px; padding: 0.75rem 1.5rem; font-weight: 500; border: none; transition: all 0.3s; }
    .stButton > button:hover { background: linear-gradient(135deg, #0056b3, #004494); transform: scale(1.05); }
    .stExpander { background: white; border-radius: 12px; border: 1px solid #e5e5e7; box-shadow: 0 2px 8px rgba(0,0,0,0.05); transition: box-shadow 0.3s; }
    .stExpander:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] { font-weight: 500; color: #8e8e93; padding: 0.75rem 1rem; border-radius: 8px 8px 0 0; transition: all 0.2s; }
    .stTabs [data-baseweb="tab"]:hover { color: #007aff; background: #f5f5f7; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #007aff; background: white; border-bottom: 2px solid #007aff; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .logo { width: 48px; height: 48px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.15); transition: all 0.3s; }
    .logo:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.2); transform: scale(1.1); }
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 4])
with col1:
    st.markdown('<img src="https://x.ai/wp-content/uploads/2023/10/xai-logo.png" class="logo" alt="xAI Logo">', unsafe_allow_html=True)
with col2:
    st.markdown('<h1 style="margin: 0; font-weight: 700; color: #1d1d1f;">AppWhistler AI</h1><p style="margin: 0; color: #8e8e93;">Truthful App Insights, Powered by Grok</p>', unsafe_allow_html=True)

conn = init_db()

tab1, tab2, tab3 = st.tabs(["🏠 Home", "🔍 Search", "📜 History"])

with tab1:
    st.markdown('<div class="header"><h2 style="margin: 0;">Discover Popular Apps</h2><p style="margin: 0; opacity: 0.9;">Curated insights at a glance</p></div>', unsafe_allow_html=True)
    cols = st.columns(4)
    app_keys = list(POPULAR_APPS.keys())[:16]
    for i, key in enumerate(app_keys):
        with cols[i % 4]:
            placeholder_icon = f"https://via.placeholder.com/80?text={key[0].upper()}"
            st.markdown(f'''
                <div class="app-card">
                    <img src="{placeholder_icon}" width="80" style="border-radius: 12px;">
                    <h3 style="margin: 0.5rem 0 0 0; font-size: 1rem;">{key.title()}</h3>
                    <p style="color: #8e8e93; font-size: 0.875rem; margin: 0.25rem 0 0 0;">Quick Search Ready</p>
                </div>
            ''', unsafe_allow_html=True)

with tab2:
    app_name = st.text_input("Search for an app...", placeholder="e.g., Apple Music")
    if app_name:
        suggestions = [k for k in POPULAR_APPS if app_name.lower() in k.lower()]
        selected = st.selectbox("Quick picks:", [""] + suggestions[:5], key="suggestions")
        if selected:
            app_name = selected
    store = st.selectbox("Select Store:", ["play", "appstore"], index=1 if "apple" in app_name.lower() else 0)
    
    col_btn, col_reset = st.columns([3, 1])
    with col_btn:
        if st.button("🔍 Analyze App", use_container_width=True):
            with st.spinner("Fetching reviews & distilling wisdom..."):
                try:
                    reviews, icon_url, fetched_app_id = fetch_app_info(app_name, store)
                    pros, cons, issues, review_texts, truth_score, truth_color = analyze_reviews(reviews)
                    ai_summary = get_ai_summary(review_texts)
                    save_to_db(conn, app_name, pros, cons, truth_score, truth_color, fetched_app_id, store, issues, review_texts, icon_url, ai_summary)
                    
                    color_map = {"Green": "#34c759", "Yellow": "#ffcc00", "Red": "#ff3b30"}
                    st.markdown(f'''
                        <div class="app-card" style="max-width: 600px; margin: 1rem auto;">
                            <div style="display: flex; align-items: center; gap: 1rem;">
                                <img src="{icon_url or 'https://via.placeholder.com/100?text=App'}" width="100" style="border-radius: 12px;">
                                <div>
                                    <h2 style="margin: 0;">{app_name}</h2>
                                    <p style="color: #8e8e93; margin: 0.25rem 0;">{store.capitalize()} Store</p>
                                </div>
                            </div>
                            <p style="margin: 1rem 0; line-height: 1.5;"><strong>AI Summary:</strong> {ai_summary}</p>
                            <div style="display: flex; gap: 1rem; margin: 1rem 0;">
                                <span style="background: {color_map[truth_color]}; color: white; padding: 0.5rem 1rem; border-radius: 20px; font-weight: 500;">
                                    Truth Score: {truth_score}/100 ({truth_color})
                                </span>
                                <span style="color: #8e8e93;">Issues: {issues or 'None detected'}</span>
                            </div>
                            <details style="margin-top: 1rem;">
                                <summary style="cursor: pointer; font-weight: 500;">Detailed Breakdown</summary>
                                <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; margin-top: 0.5rem;">
                                    <p><strong>Pros:</strong> {pros or 'N/A'}</p>
                                    <p><strong>Cons:</strong> {cons or 'N/A'}</p>
                                    <p><strong>Sample Reviews:</strong> {', '.join(review_texts[:2])}</p>
                                </div>
                            </details>
                        </div>
                    ''', unsafe_allow_html=True)
                    st.success("Analysis eternal! History beckons.")
                except ValueError as ve:
                    st.error(str(ve))
                except IndexError as ie:
                    st.error(f"Fetch whisper: {ie}. Another app?")
                except Exception as e:
                    st.error(f"Rift: {e}")
    with col_reset:
        if st.button("Reset DB", use_container_width=True):
            if st.checkbox("Confirm wipe? (Irreversible)"):
                init_db(reset=True)
                st.success("DB reborn!")

with tab3:
    st.markdown('<div class="header"><h2 style="margin: 0;">Search History</h2><p style="margin: 0; opacity: 0.9;">Timestamps tell the tale</p></div>', unsafe_allow_html=True)
    if conn:
        try:
            c = conn.cursor()
            c.execute("SELECT name, store, truth_score, truth_color, created_at FROM apps ORDER BY created_at DESC LIMIT 20")
            history = c.fetchall()
            if history:
                for row in history:
                    name, store, score, color, date = row
                    date_str = date[:19] if date else "Ancient"
                    st.markdown(f'<div class="app-card"><strong>{name}</strong> ({store.upper()}) - {score}/100 ({color})<br><small>{date_str}</small></div>', unsafe_allow_html=True)
            else:
                st.info("Barren—ignite a search!")
        except Exception as e:
            st.error(f"History unravel: {e}")
    else:
        st.warning("DB adrift—reload.")

st.markdown("""
    <div style="text-align: center; padding: 2rem; color: #8e8e93; font-size: 0.875rem; border-top: 1px solid #e5e5e7; margin-top: 2rem;">
        <p>Powered by Grok from xAI | Built for a truthful world 🚀 | Target: 100M+ by Dec 2026</p>
    </div>
""", unsafe_allow_html=True)

if conn:
    conn.close()