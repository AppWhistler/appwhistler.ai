import os
import subprocess
import sys
import sqlite3
from pathlib import Path
import requests  # For HF probe

def check_python():
    if sys.version_info < (3, 11):
        print("Python 3.11+ required. Install from python.org.")
        sys.exit(1)
    print("Python version OK.")

def install_dependencies():
    packages = ["streamlit", "requests", "google-play-scraper", "nltk", "app-store-web-scraper", "supabase"]
    for pkg in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            print(f"Installed {pkg}.")
        except subprocess.CalledProcessError:
            print(f"Failed {pkg}. Check internet/pip.")
            sys.exit(1)

def create_project_structure():
    project_dir = Path.cwd()  # Main cave
    appwhistler_dir = project_dir / "appwhistler"
    appwhistler_dir.mkdir(exist_ok=True)

    # Cloud-hardened DB
    db_file = appwhistler_dir / "appwhistler.db"
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS apps
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT, pros TEXT, cons TEXT, truth_score INTEGER, truth_color TEXT,
                  app_id TEXT UNIQUE, store TEXT, issues TEXT, review_texts TEXT,
                  icon_url TEXT, ai_summary TEXT, created_at TEXT)''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_app_id ON apps(app_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_name ON apps(name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON apps(created_at)')
    conn.commit()
    conn.close()
    print(f"DB forged at {db_file}")

    # .streamlit secrets placeholder
    streamlit_dir = project_dir / ".streamlit"
    streamlit_dir.mkdir(exist_ok=True)
    with open(streamlit_dir / "secrets.toml", "w") as f:
        f.write("# HF token\nhf_token = \"your_hf_token_here\"\n# Supabase\nsupabase_url = \"your_supabase_url\"\nsupabase_key = \"your_anon_key\"")
    print("Secrets.toml placeholder created—edit with keys.")

def probe_apis():
    # HF probe
    hf_token = "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"  # Your fresh wand
    try:
        headers = {"Authorization": f"Bearer {hf_token}"}
        resp = requests.post("https://api-inference.huggingface.co/models/facebook/bart-large-cnn", headers=headers, json={"inputs": "Test summary."}, timeout=5)
        if resp.status_code == 200:
            print("HF API ether flows—summaries ready.")
        else:
            print("HF token rift—edit secrets.toml.")
    except Exception as e:
        print(f"HF probe falter: {e}")

    # Supabase placeholder probe
    print("Supabase: Edit secrets.toml with URL/publishable key, then reboot app.")

def run_app():
    try:
        subprocess.run(["streamlit", "run", "app.py"], check=True)
    except subprocess.CalledProcessError:
        print("Launch falter—ensure streamlit installed.")
        sys.exit(1)

def main():
    print("AppWhistler 2025 apotheosis...")
    check_python()
    install_dependencies()
    create_project_structure()
    probe_apis()
    print("Forge complete! Launching...")
    run_app()

if __name__ == "__main__":
    main()
