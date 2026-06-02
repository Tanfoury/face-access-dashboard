import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import Session, Student, AccessLog, init_db, Schedule, get_schedules
from database1 import (
    get_all_subjects, add_subject,
    save_time_slot, delete_time_slot,
    get_time_slots, get_schedule_grid,
    CRENEAUX, JOURS
)
from tabs_emploi_du_temps import render_tab6, render_tab7
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

init_db()

st.set_page_config(
    page_title="FaceGuard — Sécurité & Présence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ══════════════════════════════════════════════════════════
   LIGHT MODE — :root defaults
   ══════════════════════════════════════════════════════════ */
:root {
    --bg:             #f0f4f9;
    --surface:        #ffffff;
    --surface2:       #e8eef6;
    --border:         #ccd8eb;
    --border2:        #a8bdd6;
    --text:           #0a1628;
    --text2:          #2e4264;
    --text3:          #6b80a0;

    --blue:           #1a56db;
    --blue-lt:        #dce8fb;
    --blue-mid:       #b8d0f7;
    --green:          #0a7d52;
    --green-lt:       #ceeede;
    --amber:          #a14b07;
    --amber-lt:       #fde4c0;
    --red:            #b52a1e;
    --red-lt:         #fcd8d6;
    --purple:         #5b1fb5;
    --purple-lt:      #e0d4fb;

    --card-blue-bg:   #eaf1ff;
    --card-green-bg:  #e4f7ef;
    --card-purple-bg: #ede8ff;
    --card-amber-bg:  #fff4e6;

    --shadow-sm: 0 1px 4px rgba(10,22,40,.08), 0 1px 2px rgba(10,22,40,.05);
    --shadow-md: 0 4px 14px rgba(10,22,40,.12), 0 1px 4px rgba(10,22,40,.07);

    --font:      'Sora', -apple-system, BlinkMacSystemFont, sans-serif;
    --mono:      'JetBrains Mono', 'Fira Code', monospace;
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 14px;
}

/* ══════════════════════════════════════════════════════════
   DARK MODE — toggled via body.fg-dark (JS below)
   ══════════════════════════════════════════════════════════ */
body.fg-dark {
    --bg:             #0f1117;
    --surface:        #1a1d27;
    --surface2:       #222636;
    --border:         #2e3347;
    --border2:        #3a4060;
    --text:           #e8ecf4;
    --text2:          #9aa3b8;
    --text3:          #5c6480;

    --blue:           #4f8ef7;
    --blue-lt:        #162240;
    --blue-mid:       #1c3060;
    --green:          #2fb87e;
    --green-lt:       #0c2419;
    --amber:          #f59e0b;
    --amber-lt:       #271a04;
    --red:            #f07171;
    --red-lt:         #280d0d;
    --purple:         #9f7af5;
    --purple-lt:      #1a1038;

    --card-blue-bg:   #151d30;
    --card-green-bg:  #101f18;
    --card-purple-bg: #160f2e;
    --card-amber-bg:  #1e1508;

    --shadow-sm: 0 1px 3px rgba(0,0,0,.32);
    --shadow-md: 0 4px 20px rgba(0,0,0,.48);
}

/* ── Override Streamlit backgrounds ──────────────────────── */
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.stApp, .main {
    background: var(--bg) !important;
}

/* ── Global ──────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--font) !important;
    -webkit-font-smoothing: antialiased;
}
.main .block-container {
    padding: 1.75rem 2.25rem 2.5rem;
    max-width: 1440px;
}

/* ── Topbar ──────────────────────────────────────────────── */
.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 0 20px;
    border-bottom: 2px solid var(--border);
    margin-bottom: 22px;
}
.topbar-left { display: flex; flex-direction: column; gap: 3px; }
.topbar-title {
    font-size: 22px; font-weight: 700;
    color: var(--text); letter-spacing: -0.4px;
}
.topbar-sub { font-size: 12px; color: var(--text3); }
.topbar-right {
    display: flex; align-items: center; gap: 8px;
}
.live-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 10px; font-weight: 700; letter-spacing: .4px;
    color: var(--green); background: var(--green-lt);
    padding: 4px 12px; border-radius: 20px;
    border: 1px solid rgba(10,125,82,.2);
}
.live-badge-dot {
    width: 6px; height: 6px;
    background: var(--green); border-radius: 50%;
    animation: blink 1.8s infinite;
}

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 14px rgba(10,22,40,.06) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }

.sid-brand {
    padding: 24px 18px 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 6px;
}
.sid-logotype {
    display: inline-flex; align-items: center; gap: 10px;
    margin-bottom: 10px;
}
.sid-logo-mark {
    width: 38px; height: 38px;
    background: var(--blue);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(26,86,219,.35);
}
.sid-logo-shield {
    width: 20px; height: 22px;
    background: #fff;
    clip-path: polygon(50% 0%, 100% 15%, 100% 60%, 50% 100%, 0% 60%, 0% 15%);
}
.sid-title {
    font-size: 16px; font-weight: 700;
    color: var(--text); letter-spacing: -0.3px; line-height: 1.1;
}
.sid-sub { font-size: 11px; color: var(--text3); margin-top: 2px; }
.sid-pill {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 10px; font-weight: 700; letter-spacing: .3px;
    color: var(--green); background: var(--green-lt);
    padding: 4px 11px; border-radius: 20px; margin-top: 10px;
    border: 1px solid rgba(10,125,82,.2);
}
.sid-pill-dot {
    width: 5px; height: 5px;
    background: var(--green); border-radius: 50%;
    animation: blink 1.8s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.25} }

.nav-section {
    font-size: 9px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.4px;
    color: var(--text3);
    padding: 14px 22px 4px; display: block;
}

/* ── Radio nav ───────────────────────────────────────────── */
div[data-testid="stRadio"] { padding: 0 10px; }
div[data-testid="stRadio"] > div { gap: 2px !important; }
div[data-testid="stRadio"] label {
    display: flex !important; align-items: center;
    padding: 9px 14px !important;
    border-radius: var(--radius-md) !important;
    font-size: 13px !important; font-weight: 500 !important;
    color: var(--text2) !important;
    cursor: pointer; transition: all .14s;
    margin: 0 !important;
    background: transparent !important;
    border: none !important;
}
div[data-testid="stRadio"] label:hover {
    background: var(--surface2) !important;
    color: var(--text) !important;
}
div[data-testid="stRadio"] label[data-checked="true"] {
    background: var(--blue-lt) !important;
    color: var(--blue) !important;
    font-weight: 700 !important;
    box-shadow: inset 3px 0 0 var(--blue) !important;
}
div[data-testid="stRadio"] label > div:first-of-type { display: none !important; }
div[data-testid="stRadio"] label [role="radio"] { display: none !important; }

.sid-clock {
    margin: 8px 10px 14px;
    padding: 8px 12px;
    background: var(--surface2);
    border-radius: var(--radius-md);
    font-family: var(--mono);
    font-size: 13px; color: var(--text3);
    text-align: center;
    border: 1px solid var(--border);
    letter-spacing: 1px;
}

/* ── Metric cards ────────────────────────────────────────── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px; margin-bottom: 22px;
}
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 3px solid transparent;
    border-radius: var(--radius-lg);
    padding: 20px 22px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow .18s, transform .18s;
}
.metric-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.metric-card.blue   { border-top-color: var(--blue);   background: var(--card-blue-bg); }
.metric-card.green  { border-top-color: var(--green);  background: var(--card-green-bg); }
.metric-card.purple { border-top-color: var(--purple); background: var(--card-purple-bg); }
.metric-card.amber  { border-top-color: var(--amber);  background: var(--card-amber-bg); }

.metric-label {
    font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.3px;
    color: var(--text3); margin-bottom: 10px;
}
.metric-val {
    font-size: 38px; font-weight: 700;
    color: var(--text); line-height: 1;
    font-feature-settings: "tnum";
    font-variant-numeric: tabular-nums;
    letter-spacing: -1.5px;
}
.metric-note {
    font-size: 11px; color: var(--text3);
    margin-top: 10px; display: flex; align-items: center; gap: 5px;
    flex-wrap: wrap;
}
.nbadge {
    display: inline-block;
    font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 5px;
}
.nb-blue   { background: var(--blue-mid);  color: var(--blue); }
.nb-green  { background: var(--green-lt);  color: var(--green); }
.nb-red    { background: var(--red-lt);    color: var(--red); }
.nb-purple { background: var(--purple-lt); color: var(--purple); }
.nb-amber  { background: var(--amber-lt);  color: var(--amber); }

div[data-testid="metric-container"] { display: none !important; }

/* ── Cards ───────────────────────────────────────────────── */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-bottom: 14px;
    box-shadow: var(--shadow-sm);
}
.card-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 18px;
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
}
.card-title { font-size: 13px; font-weight: 600; color: var(--text); }
.card-tag {
    font-size: 10px; font-weight: 600; letter-spacing: .3px;
    padding: 3px 10px; border-radius: 20px;
    background: var(--blue-mid); color: var(--blue);
}
.card-body { padding: 16px 18px; }

/* ── Activity feed ───────────────────────────────────────── */
.feed-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 0; border-bottom: 1px solid var(--border);
}
.feed-item:last-child { border-bottom: none; }
.feed-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.feed-time { font-family: var(--mono); font-size: 11px; color: var(--text3); min-width: 64px; }
.feed-name { font-size: 13px; font-weight: 500; color: var(--text); flex: 1; }
.feed-action { font-size: 11px; font-weight: 700; min-width: 46px; text-align: right; }
.fa-in  { color: var(--green); }
.fa-out { color: var(--purple); }
.feed-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px; }
.fb-ok { background: var(--green-lt);  color: var(--green);  border: 1px solid rgba(10,125,82,.18); }
.fb-no { background: var(--red-lt);    color: var(--red);    border: 1px solid rgba(181,42,30,.18); }

/* ── Category bars ───────────────────────────────────────── */
.cat-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.cat-lbl { font-size: 12px; font-weight: 500; color: var(--text2); min-width: 90px; }
.bar-track {
    flex: 1; height: 6px;
    background: var(--border);
    border-radius: 3px; overflow: hidden;
}
.bar-fill  { height: 100%; border-radius: 3px; }
.cat-cnt   { font-size: 12px; font-weight: 700; color: var(--text); min-width: 28px; text-align: right; }

/* ── Stat chips ──────────────────────────────────────────── */
.stat-row { display: flex; flex-direction: column; gap: 8px; }
.stat-chip {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
}
.stat-chip-label { font-size: 11px; color: var(--text3); }
.stat-chip-val   { font-size: 17px; font-weight: 700; font-feature-settings: "tnum"; }

/* ── Legend items ────────────────────────────────────────── */
.legend-grid { display: flex; flex-direction: column; gap: 6px; }
.legend-item {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px;
    background: var(--surface2);
    border-radius: var(--radius-sm);
    font-size: 12px; color: var(--text2);
    border: 1px solid var(--border);
}
.leg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ── Badges ──────────────────────────────────────────────── */
.badge { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; display: inline-block; }
.badge-eleve  { background: var(--blue-lt);   color: var(--blue); }
.badge-prof   { background: var(--purple-lt); color: var(--purple); }
.badge-admin  { background: var(--amber-lt);  color: var(--amber); }

/* ── Tables ──────────────────────────────────────────────── */
.stDataFrame { border-radius: var(--radius-lg) !important; overflow: hidden !important; border: 1px solid var(--border) !important; }
.stDataFrame [data-testid="stDataFrameResizable"] { background: var(--surface) !important; }
thead tr th {
    background: var(--surface2) !important;
    color: var(--text3) !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    font-weight: 600 !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 11px 14px !important;
}
tbody tr:hover { background: var(--surface2) !important; }

/* ── Form inputs ─────────────────────────────────────────── */
.stTextInput input,
.stSelectbox > div > div,
.stTextArea textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border2) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text) !important;
    font-size: 13px !important;
    font-family: var(--font) !important;
    box-shadow: none !important;
}
.stTextInput input:focus,
.stSelectbox > div > div:focus-within,
.stTextArea textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(26,86,219,.12) !important;
}
label { color: var(--text2) !important; font-size: 12px !important; font-weight: 500 !important; }

/* ── Buttons ─────────────────────────────────────────────── */
.stButton button,
.stFormSubmitButton button {
    background: var(--blue) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    font-family: var(--font) !important;
    padding: 9px 18px !important;
    transition: background .15s, transform .1s !important;
    box-shadow: none !important;
}
.stButton button:hover,
.stFormSubmitButton button:hover {
    background: #1648c4 !important;
    transform: translateY(-1px) !important;
}
.stFormSubmitButton button { width: 100% !important; margin-top: 8px !important; }

/* ── Alerts ──────────────────────────────────────────────── */
.stAlert {
    background: var(--surface) !important;
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border) !important;
    color: var(--text2) !important;
}

/* ── Camera frame ────────────────────────────────────────── */
.cam-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
}
.cam-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px;
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
    font-size: 12px; font-weight: 600; color: var(--text2);
}
.rec-dot {
    display: inline-block;
    width: 7px; height: 7px;
    background: var(--red); border-radius: 50%;
    animation: blink 1.5s infinite;
    margin-right: 6px;
}

/* ── Enrollment steps ────────────────────────────────────── */
.step-item {
    display: flex; gap: 12px; align-items: flex-start;
    background: var(--surface2);
    border-radius: var(--radius-md);
    padding: 12px 14px;
    border: 1px solid var(--border);
}
.step-num {
    font-size: 11px; font-weight: 700;
    padding: 3px 8px; border-radius: 5px;
    color: #fff; flex-shrink: 0; margin-top: 1px;
}
.step-text { font-size: 12px; color: var(--text2); line-height: 1.6; }

/* ── Scrollbar ───────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text3); }

/* ── Section label ───────────────────────────────────────── */
.section-label {
    font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
    color: var(--text3); margin-bottom: 10px;
}

/* ── Divider line ────────────────────────────────────────── */
.divider {
    border: none; border-top: 1px solid var(--border);
    margin: 12px 0;
}
</style>
""", unsafe_allow_html=True)

# ─── Theme-sync JS ─────────────────────────────────────────────────────────────
st.markdown("""
<script>
(function() {
    function syncTheme() {
        var container = document.querySelector('[data-testid="stAppViewContainer"]')
                     || document.querySelector('.stApp');
        if (!container) return;
        var theme = container.getAttribute('data-theme');
        if (!theme) {
            var bg = getComputedStyle(container).backgroundColor;
            var m  = bg.match(/\\d+/g);
            if (m && m.length >= 3) {
                var lum = (+m[0]*299 + +m[1]*587 + +m[2]*114) / 1000;
                theme = lum < 128 ? 'dark' : 'light';
            }
        }
        if (theme === 'dark') {
            document.body.classList.add('fg-dark');
        } else {
            document.body.classList.remove('fg-dark');
        }
    }
    syncTheme();
    new MutationObserver(syncTheme).observe(
        document.documentElement,
        {attributes:true, subtree:true, attributeFilter:['data-theme','class']}
    );
    setInterval(syncTheme, 400);
})();
</script>
""", unsafe_allow_html=True)

# ─── AUTHENTIFICATION ──────────────────────────────────────────────────────────
LOGIN_USER = os.environ.get("DASHBOARD_USER", "admin")
LOGIN_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "FaceGuard123")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def authenticate(username: str, password: str) -> bool:
    return username == LOGIN_USER and password == LOGIN_PASSWORD

def login_page():
    # --- INJECTION CSS POUR LE DESIGN SAAS ---
    st.markdown("""
        <style>
        /* Centrage et style global de la page */
        .block-container {
            padding-top: 4rem;
            padding-bottom: 4rem;
        }
        
        /* Cibler la boîte de formulaire générée par Streamlit */
        [data-testid="stForm"] {
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 2.5rem;
            background-color: #ffffff;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.05);
            transition: all 0.3s ease-in-out;
        }
        
        /* Styliser le bouton de soumission */
        [data-testid="stFormSubmitButton"] button {
            width: 100%;
            background-color: #0f172a;
            color: #ffffff;
            font-weight: 600;
            padding: 0.6rem;
            border-radius: 8px;
            border: none;
            margin-top: 1rem;
        }
        [data-testid="stFormSubmitButton"] button:hover {
            background-color: #1e293b;
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.2);
        }
        [data-testid="stFormSubmitButton"] button:active {
            transform: scale(0.98);
        }
        </style>
    """, unsafe_allow_html=True)

    # --- LAYOUT CENTRÉ AVEC DES COLONNES ---
    col1, col2, col3 = st.columns([1, 2.5, 1])

    with col2:
        # En-tête de la page de connexion
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 2rem;'>
                <h1 style='margin-bottom: 0.5rem; font-size: 2.5rem;'>🛡️ FaceGuard</h1>
                <p style='color: #64748b; font-size: 1.1rem; margin-top: 0;'>
                    Accès sécurisé au tableau de bord
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        # Le Formulaire
        with st.form("login_form"):
            username = st.text_input("Identifiant", placeholder="Entrez votre nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Se connecter")

        # Gestion de la soumission
        if submitted:
            # Ajout d'un léger effet de chargement pour le côté pro
            with st.spinner("Authentification en cours..."):
                time.sleep(0.6)
                
                if authenticate(username.strip(), password):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")

if not st.session_state.logged_in:
    login_page()
    st.stop()


# ─── Sidebar ──────────────────────────────────────────────────────────────────
now_str  = datetime.now().strftime("%A %d %B %Y")
time_str = datetime.now().strftime("%H:%M:%S")

with st.sidebar:
    st.markdown(f"""
    <div class="sid-brand">
        <div class="sid-logotype">
            <div class="sid-logo-mark"><div class="sid-logo-shield"></div></div>
            <div>
                <div class="sid-title">FaceGuard</div>
                <div class="sid-sub">Reconnaissance Faciale</div>
            </div>
        </div>
        <div class="sid-pill">
            <span class="sid-pill-dot"></span>
            Système actif
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<span class="nav-section">Navigation</span>', unsafe_allow_html=True)
    selected_tab = st.radio("Navigation", [
        "Vue d'ensemble",
        "Historique",
        "Annuaire",
        "Supervision Live",
        "Inscription",
        "Emplois du Temps",
        "Suivi Présences"
    ], label_visibility="collapsed")

    st.markdown(f'<div class="sid-clock">{time_str}</div>', unsafe_allow_html=True)

# ─── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def get_data():
    session = Session()
    students = session.query(Student).all()
    logs = session.query(AccessLog).all()
    student_list = [{
        "id": s.id, "name": s.name, "student_id": s.student_id,
        "category": s.category, "grade": s.grade,
        "enrolled": s.enrolled, "inside": s.inside
    } for s in students]
    log_list = [{
        "id": l.id, "name": l.name, "student_id": getattr(l, 'student_id', None),
        "timestamp": l.timestamp, "action": l.action, "granted": l.granted
    } for l in logs]
    session.close()
    return student_list, log_list

students_raw, logs_raw = get_data()

@st.cache_data(ttl=2)
def load_schedules():
    return get_schedules()

schedules = load_schedules()

today              = date.today()
logs_today         = [l for l in logs_raw if l["timestamp"].date() == today]
students_inside    = [s for s in students_raw if s["inside"]]
profs_inside       = [s for s in students_inside if s.get("category","").lower() == "prof"]
admin_inside       = [s for s in students_inside if s.get("category","").lower() == "admin"]
eleves_inside      = [s for s in students_inside if s.get("category","").lower() == "eleve"]
total_alerts_today = len([l for l in logs_today if not l["granted"]])

# ─── Page header ──────────────────────────────────────────────────────────────
TAB_TITLES = {
    "Vue d'ensemble":   ("Vue d'ensemble",        now_str + " — temps réel"),
    "Historique":       ("Historique des accès",   "200 derniers enregistrements"),
    "Annuaire":         ("Annuaire",               "Personnels & Élèves"),
    "Supervision Live": ("Supervision Live",        "Flux caméra en direct"),
    "Inscription":      ("Nouvelle Inscription",   "Enrôlement biométrique"),
    "Emplois du Temps": ("Emplois du Temps",       "Gestion des plannings"),
    "Suivi Présences":  ("Suivi des Présences",    "Rapport journalier"),
}
pg_title, pg_sub = TAB_TITLES.get(selected_tab, (selected_tab, ""))
st.markdown(f"""
<div class="topbar">
    <div class="topbar-left">
        <div class="topbar-title">{pg_title}</div>
        <div class="topbar-sub">{pg_sub}</div>
    </div>
    <div class="topbar-right">
        <span class="live-badge"><span class="live-badge-dot"></span>Temps réel</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Vue d'ensemble
# ══════════════════════════════════════════════════════════════════════════════
if selected_tab == "Vue d'ensemble":

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card blue">
            <div class="metric-label">Total inscrits</div>
            <div class="metric-val">{len(students_raw)}</div>
            <div class="metric-note">Membres enregistrés</div>
        </div>
        <div class="metric-card green">
            <div class="metric-label">À l'intérieur</div>
            <div class="metric-val">{len(students_inside)}</div>
            <div class="metric-note">
                <span class="nbadge nb-blue">{len(eleves_inside)} élèves</span>
                <span class="nbadge nb-purple">{len(profs_inside)} profs</span>
            </div>
        </div>
        <div class="metric-card purple">
            <div class="metric-label">Personnel présent</div>
            <div class="metric-val">{len(profs_inside) + len(admin_inside)}</div>
            <div class="metric-note">
                <span class="nbadge nb-amber">{len(admin_inside)} admins</span>
                <span class="nbadge nb-purple">{len(profs_inside)} profs</span>
            </div>
        </div>
        <div class="metric-card amber">
            <div class="metric-label">Événements du jour</div>
            <div class="metric-val">{len(logs_today)}</div>
            <div class="metric-note">
                <span class="nbadge nb-red">{total_alerts_today} refusés</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(
            '<div class="card">'
            '<div class="card-head"><div class="card-title">Activité récente</div>'
            '<span class="card-tag">Temps réel</span></div>'
            '<div class="card-body">',
            unsafe_allow_html=True
        )
        if logs_raw:
            feed_html = ""
            for l in logs_raw[:8]:
                is_in = l["action"] and l["action"].lower() in ["in", "entrée", "enter", "entry"]
                granted = l["granted"]
                dot_color = "#0a7d52" if granted else "#b52a1e"
                action_html = '<span class="feed-action fa-in">Entrée</span>' if is_in else '<span class="feed-action fa-out">Sortie</span>'
                badge_html  = '<span class="feed-badge fb-ok">Autorisé</span>' if granted else '<span class="feed-badge fb-no">Refusé</span>'
                ts = l["timestamp"].strftime("%H:%M:%S")
                feed_html += (
                    f'<div class="feed-item">'
                    f'<div class="feed-dot" style="background:{dot_color}"></div>'
                    f'<div class="feed-time">{ts}</div>'
                    f'<div class="feed-name">{l["name"]}</div>'
                    f'{action_html}{badge_html}'
                    f'</div>'
                )
            st.markdown(feed_html, unsafe_allow_html=True)
        else:
            st.info("Aucune activité enregistrée.")
        st.markdown('</div></div>', unsafe_allow_html=True)

    with col_right:
        cats = {"eleve": 0, "prof": 0, "admin": 0}
        for s in students_raw:
            c = (s.get("category") or "eleve").lower()
            if c in cats:
                cats[c] += 1
        total = max(len(students_raw), 1)

        bar_colors = {"eleve": "#1a56db", "prof": "#5b1fb5", "admin": "#a14b07"}
        labels_map = {"eleve": "Élèves", "prof": "Professeurs", "admin": "Admins"}
        cats_html = ""
        for cat, cnt in cats.items():
            pct = round(cnt / total * 100)
            cats_html += (
                f'<div class="cat-row">'
                f'<div class="cat-lbl">{labels_map[cat]}</div>'
                f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{bar_colors[cat]}"></div></div>'
                f'<div class="cat-cnt">{cnt}</div>'
                f'</div>'
            )

        present_pairs = [
            ("Élèves", len(eleves_inside), cats["eleve"], "#0a7d52"),
            ("Profs",  len(profs_inside),  cats["prof"],  "#0a7d52"),
            ("Admins", len(admin_inside),  cats["admin"], "#0a7d52"),
        ]
        present_html = ""
        for lbl, val, denom, color in present_pairs:
            pct_p = round(val / max(denom, 1) * 100)
            present_html += (
                f'<div class="cat-row">'
                f'<div class="cat-lbl">{lbl}</div>'
                f'<div class="bar-track"><div class="bar-fill" style="width:{pct_p}%;background:{color}"></div></div>'
                f'<div class="cat-cnt">{val}</div>'
                f'</div>'
            )

        st.markdown(
            '<div class="card">'
            '<div class="card-head"><div class="card-title">Répartition</div></div>'
            '<div class="card-body">'
            '<div class="section-label">Par catégorie</div>'
            + cats_html +
            '<hr class="divider">'
            '<div class="section-label">Présents maintenant</div>'
            + present_html +
            '</div></div>',
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Historique
# ══════════════════════════════════════════════════════════════════════════════
elif selected_tab == "Historique":

    col_f1, col_f2, col_f3 = st.columns([3, 1, 1])
    with col_f1:
        search_name = st.text_input("Rechercher par nom", placeholder="Nom de la personne…", key="log_search")
    with col_f2:
        filter_action = st.selectbox("Action", ["Tous", "Entrée", "Sortie"], key="log_action")
    with col_f3:
        filter_granted = st.selectbox("Statut", ["Tous", "Autorisé", "Refusé"], key="log_granted")

    if logs_raw:
        log_data = []
        for l in logs_raw[:200]:
            is_in = l["action"] and l["action"].lower() in ["in", "entrée", "enter", "entry"]
            log_data.append({
                "Date / Heure": l["timestamp"].strftime("%d/%m/%Y %H:%M:%S"),
                "Nom":          l["name"],
                "Action":       "Entrée" if is_in else "Sortie",
                "Accès":        "Autorisé" if l["granted"] else "Refusé"
            })

        df_logs = pd.DataFrame(log_data)
        if search_name:
            df_logs = df_logs[df_logs["Nom"].str.contains(search_name, case=False, na=False)]
        if filter_action != "Tous":
            df_logs = df_logs[df_logs["Action"] == filter_action]
        if filter_granted == "Autorisé":
            df_logs = df_logs[df_logs["Accès"] == "Autorisé"]
        elif filter_granted == "Refusé":
            df_logs = df_logs[df_logs["Accès"] == "Refusé"]

        styled = df_logs.style \
            .map(lambda v: "color:#0a7d52;font-weight:600" if v == "Autorisé" else "color:#b52a1e;font-weight:600", subset=["Accès"]) \
            .map(lambda v: "color:#1a56db" if v == "Entrée" else "color:#5b1fb5", subset=["Action"])
        st.dataframe(styled, use_container_width=True, height=520)
        st.caption(f"{len(df_logs)} enregistrement(s) affiché(s)")
    else:
        st.info("Aucun historique trouvé.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Annuaire
# ══════════════════════════════════════════════════════════════════════════════
elif selected_tab == "Annuaire":

    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search_ann = st.text_input("Rechercher", placeholder="Nom ou classe…", key="ann_search")
    with col_s2:
        cat_filter = st.selectbox("Catégorie", ["Tous", "Eleve", "Prof", "Admin"], key="ann_cat")

    if students_raw:
        cat_map = {"eleve": "Élève", "prof": "Prof", "admin": "Admin"}
        student_data = []
        for s in students_raw:
            cat = (s.get("category") or "eleve").lower()
            student_data.append({
                "Nom":            s["name"],
                "Catégorie":      cat_map.get(cat, cat.capitalize()),
                "Classe / Poste": s.get("grade") or "—",
                "Enrôlé":         "Oui" if s["enrolled"] else "Non",
                "Statut":         "Présent" if s["inside"] else "Absent"
            })

        df_stu = pd.DataFrame(student_data)
        if search_ann:
            mask = (
                df_stu["Nom"].str.contains(search_ann, case=False, na=False) |
                df_stu["Classe / Poste"].str.contains(search_ann, case=False, na=False)
            )
            df_stu = df_stu[mask]
        if cat_filter != "Tous":
            df_stu = df_stu[df_stu["Catégorie"].str.lower() == cat_filter.lower()]

        styled_stu = df_stu.style \
            .map(lambda v: "color:#0a7d52;font-weight:600" if v == "Présent" else "color:#8896b0", subset=["Statut"]) \
            .map(lambda v: "color:#0a7d52" if v == "Oui" else "color:#b52a1e", subset=["Enrôlé"])
        st.dataframe(styled_stu, use_container_width=True, height=520)
        st.caption(f"{len(df_stu)} personne(s)")
    else:
        st.info("Aucune personne inscrite.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Supervision Live
# ══════════════════════════════════════════════════════════════════════════════
elif selected_tab == "Supervision Live":

    col_cam, col_info = st.columns([3, 1])

    with col_info:
        rpi_ip = st.text_input("Adresse IP Raspberry Pi", value="192.168.1.100", key="rpi_ip")

    with col_cam:
        st.markdown(f"""
        <div class="cam-wrap">
            <div class="cam-head">
                <span><span class="rec-dot"></span>CAM-01 — Entrée principale</span>
                <span style="font-family:var(--mono);font-size:11px;color:var(--text3)">{time_str}</span>
            </div>
            <img src="http://{rpi_ip}:5000/stream.mjpg" width="100%"
                 style="display:block;"
                 alt="Flux vidéo non disponible">
        </div>
        """, unsafe_allow_html=True)

    with col_info:
        entries_today = len([l for l in logs_today if l["action"] and l["action"].lower() in ["in","entrée","enter","entry"]])
        exits_today   = len(logs_today) - entries_today
        refused_today = len([l for l in logs_today if not l["granted"]])

        st.markdown(f"""
        <div class="card" style="margin-top:10px">
            <div class="card-head"><div class="card-title">Légende</div></div>
            <div class="card-body">
                <div class="legend-grid">
                    <div class="legend-item"><div class="leg-dot" style="background:#0a7d52"></div>Accès autorisé</div>
                    <div class="legend-item"><div class="leg-dot" style="background:#a14b07"></div>Identification en cours</div>
                    <div class="legend-item"><div class="leg-dot" style="background:#b52a1e"></div>Accès refusé</div>
                    <div class="legend-item"><div class="leg-dot" style="background:#5b1fb5"></div>Spoofing détecté</div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-body">
                <div class="stat-row">
                    <div class="stat-chip">
                        <span class="stat-chip-label">Entrées</span>
                        <span class="stat-chip-val" style="color:var(--blue)">{entries_today}</span>
                    </div>
                    <div class="stat-chip">
                        <span class="stat-chip-label">Sorties</span>
                        <span class="stat-chip-val" style="color:var(--purple)">{exits_today}</span>
                    </div>
                    <div class="stat-chip">
                        <span class="stat-chip-label">Refusés</span>
                        <span class="stat-chip-val" style="color:var(--red)">{refused_today}</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Inscription
# ══════════════════════════════════════════════════════════════════════════════
elif selected_tab == "Inscription":

    col_form, col_guide = st.columns([1, 1])

    with col_form:
        st.markdown(
            '<div class="card"><div class="card-head"><div class="card-title">Formulaire d\'inscription</div></div>'
            '<div class="card-body">',
            unsafe_allow_html=True
        )
        with st.form("enrollment_form", clear_on_submit=True):
            name       = st.text_input("Nom complet *",      placeholder="Ex: Amine Ben Ali")
            student_id = st.text_input("Matricule / ID *",   placeholder="Ex: STU-2024-001")
            grade      = st.text_input("Classe ou Fonction", placeholder="Ex: 7A, Directeur pédagogique")
            category   = st.selectbox("Catégorie *", ["eleve", "prof", "admin"],
                                      format_func=lambda x: {"eleve": "Élève", "prof": "Professeur", "admin": "Administrateur"}[x])
            submitted  = st.form_submit_button("Démarrer l'inscription")
        st.markdown('</div></div>', unsafe_allow_html=True)

        if submitted:
            if name and student_id:
                with st.spinner(f"Enrôlement de {name} en cours…"):
                    from enroll import enroll_student
                    enroll_student(name, student_id, grade, category)
                st.success(f"Inscription de **{name}** terminée avec succès.")
                st.cache_data.clear()
            else:
                st.error("Veuillez remplir au moins le nom et le matricule.")

    with col_guide:
        steps = [
            ("1", "Remplissez le formulaire avec les informations correctes.", "#1a56db"),
            ("2", "Cliquez sur « Démarrer l'inscription ».",                   "#5b1fb5"),
            ("3", "Regardez la caméra — restez immobile.",                     "#5b1fb5"),
            ("4", "Le système capture plusieurs échantillons du visage.",       "#a14b07"),
            ("5", "L'enrôlement se termine automatiquement.",                  "#0a7d52"),
        ]
        steps_html = ""
        for num, text, color in steps:
            steps_html += (
                f'<div class="step-item" style="margin-bottom:8px">'
                f'<span class="step-num" style="background:{color}">{num}</span>'
                f'<span class="step-text">{text}</span>'
                f'</div>'
            )
        st.markdown(
            f'<div class="card"><div class="card-head"><div class="card-title">Guide d\'enrôlement</div></div>'
            f'<div class="card-body">{steps_html}</div></div>',
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Emplois du Temps
# ══════════════════════════════════════════════════════════════════════════════
elif selected_tab == "Emplois du Temps":

    classes  = sorted(set(
        s.get("grade") for s in students_raw
        if s.get("grade") and (s.get("category") or "").lower() == "eleve"
    ))
    profs    = sorted(s.get("name") for s in students_raw if (s.get("category") or "").lower() == "prof")
    subjects = [
        "Mathématiques", "Français", "Arabe", "Sciences", "Histoire-Géo",
        "Éducation physique", "Informatique", "Art plastique", "Musique", "Anglais"
    ]

    import json
    classes_js  = json.dumps(classes)
    profs_js    = json.dumps(profs)
    subjects_js = json.dumps(subjects)

    # ─── Timetable iframe ──────────────────────────────────────────────────────
    # The iframe uses its own self-contained CSS token system (light/dark).
    # Theme detection: polls parent body for .fg-dark class every 500ms.
    # This is the most reliable method because body.fg-dark is set by our JS above.

    calendar_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}

/* ══ LIGHT (default) ══════════════════════════════════════ */
:root{{
  --bg:        #f0f4f9;
  --surface:   #ffffff;
  --surface2:  #e8eef6;
  --border:    #ccd8eb;
  --border2:   #a8bdd6;
  --text:      #0a1628;
  --text2:     #2e4264;
  --text3:     #6b80a0;
  --blue:      #1a56db;
  --blue-lt:   #dce8fb;
  --green:     #0a7d52;
  --green-lt:  #ceeede;
  --amber:     #a14b07;
  --amber-lt:  #fde4c0;
  --red:       #b52a1e;
  --red-lt:    #fcd8d6;
  --purple:    #5b1fb5;
  --purple-lt: #e0d4fb;
}}

/* ══ DARK — toggled via html.dark ═══════════════════════ */
html.dark{{
  --bg:        #0f1117;
  --surface:   #1a1d27;
  --surface2:  #222636;
  --border:    #2e3347;
  --border2:   #3a4060;
  --text:      #e8ecf4;
  --text2:     #9aa3b8;
  --text3:     #5c6480;
  --blue:      #4f8ef7;
  --blue-lt:   #162240;
  --green:     #2fb87e;
  --green-lt:  #0c2419;
  --amber:     #f59e0b;
  --amber-lt:  #271a04;
  --red:       #f07171;
  --red-lt:    #280d0d;
  --purple:    #9f7af5;
  --purple-lt: #1a1038;
}}

body{{
  background:var(--bg);color:var(--text);
  font-family:'Sora',sans-serif;font-size:13px;
  padding:16px;
  transition:background .25s,color .25s;
}}

/* ── Toolbar ── */
.toolbar{{
  display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  margin-bottom:14px;
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:10px;
  padding:10px 16px;
  box-shadow:0 1px 4px rgba(10,22,40,.07);
}}
.tbar-label{{
  font-size:10px;font-weight:700;letter-spacing:1px;
  text-transform:uppercase;color:var(--text3);
  margin-right:4px;
}}
select{{
  height:34px;padding:0 12px;
  border:1px solid var(--border2);border-radius:7px;
  font-size:12px;font-family:'Sora',sans-serif;font-weight:500;
  background:var(--surface2);color:var(--text);
  outline:none;cursor:pointer;
  transition:border-color .12s,background .25s,color .25s;
  appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b80a0'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
  padding-right:28px;
}}
select:focus{{border-color:var(--blue);box-shadow:0 0 0 3px rgba(79,142,247,.15)}}
.sep{{width:1px;height:22px;background:var(--border);margin:0 2px;}}
.btn-save{{
  display:inline-flex;align-items:center;gap:6px;
  height:34px;padding:0 18px;border-radius:7px;border:none;
  font-size:12px;font-weight:700;font-family:'Sora',sans-serif;
  background:var(--blue);color:#fff;cursor:pointer;
  transition:opacity .12s,transform .1s;
  letter-spacing:.2px;
}}
.btn-save:hover{{opacity:.88;transform:translateY(-1px)}}

/* ── Info bar ── */
.info-bar{{
  font-size:11px;color:var(--text3);
  margin-bottom:12px;padding:8px 14px;
  background:var(--surface);
  border-radius:8px;
  border:1px solid var(--border);
  border-left:3px solid var(--blue);
}}

/* ── Legend chips ── */
.prof-legend{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}}
.p-chip{{
  font-size:10px;font-weight:600;
  padding:3px 11px;border-radius:20px;letter-spacing:.2px;
}}

/* ── Table wrapper ── */
.tbl-wrap{{
  overflow-x:auto;
  border-radius:12px;
  border:1px solid var(--border);
  box-shadow:0 2px 10px rgba(10,22,40,.07);
}}
table{{
  width:100%;border-collapse:collapse;
  font-size:11.5px;table-layout:fixed;
  background:var(--surface);
}}

/* ── Header ── */
thead th{{
  background:var(--surface2);color:var(--text3);
  font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;
  padding:11px 6px;text-align:center;
  border-bottom:2px solid var(--border);
  border-right:1px solid var(--border);
  position:sticky;top:0;z-index:3;
  transition:background .25s,color .25s;
}}
thead th:first-child{{
  text-align:left;padding-left:14px;
  width:100px;border-right:2px solid var(--border);
}}
thead th:last-child{{border-right:none}}

/* Colored day headers */
.dh-lun{{color:#1a56db!important}}
.dh-mar{{color:#5b1fb5!important}}
.dh-mer{{color:#0a7d52!important}}
.dh-jeu{{color:#a14b07!important}}
.dh-ven{{color:#b52a1e!important}}
.dh-sam{{color:#2e4264!important}}
html.dark .dh-lun{{color:#4f8ef7!important}}
html.dark .dh-mar{{color:#9f7af5!important}}
html.dark .dh-mer{{color:#2fb87e!important}}
html.dark .dh-jeu{{color:#f59e0b!important}}
html.dark .dh-ven{{color:#f07171!important}}
html.dark .dh-sam{{color:#9aa3b8!important}}

/* ── Body cell ── */
tbody td{{
  border-right:1px solid var(--border);
  border-bottom:1px solid var(--border);
  padding:0;height:64px;
  position:relative;vertical-align:top;
  transition:border-color .25s;
}}
tbody td:last-child{{border-right:none}}
tbody tr:last-child td{{border-bottom:none}}

/* ── Time cell ── */
td.td-time{{
  background:var(--surface2);
  vertical-align:middle;padding:6px 12px;
  cursor:default;
  border-right:2px solid var(--border);
  transition:background .25s;
}}
.time-main{{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:var(--text2);}}
.time-end {{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text3);margin-top:2px;}}

/* ── Lunch break row ── */
tr.break-row td{{height:36px;}}
td.td-break{{
  background:var(--surface2);opacity:.65;
  vertical-align:middle;text-align:center;cursor:default;
}}
.break-lbl{{font-size:10px;color:var(--text3);font-weight:600;letter-spacing:.3px;}}

/* ── Empty cell — click to add ── */
.cell-empty{{
  width:100%;height:100%;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;transition:background .1s;
}}
.cell-empty:hover{{background:var(--blue-lt)}}
.plus-glyph{{
  font-size:20px;color:var(--border2);font-weight:300;
  transition:color .1s,transform .12s;user-select:none;
}}
.cell-empty:hover .plus-glyph{{color:var(--blue);transform:scale(1.2)}}

/* ── Filled slot pill ── */
.cell-pill{{
  height:100%;padding:7px 10px;
  display:flex;flex-direction:column;
  justify-content:center;gap:2px;
  position:relative;cursor:default;
}}
.pill-subj{{font-size:11px;font-weight:700;line-height:1.2}}
.pill-prof{{font-size:10px;opacity:.7;line-height:1.2;font-weight:500}}
.pill-rm{{
  position:absolute;top:4px;right:5px;
  width:15px;height:15px;
  background:rgba(0,0,0,.18);border-radius:50%;
  border:none;cursor:pointer;display:none;
  align-items:center;justify-content:center;
  font-size:8px;color:inherit;font-weight:900;
  padding:0;line-height:1;
}}
.cell-pill:hover .pill-rm{{display:flex}}
.pill-rm:hover{{background:rgba(0,0,0,.35)!important}}

/* ── Prof availability checkbox ── */
.cell-avail{{
  width:100%;height:100%;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;transition:background .1s;
}}
.cell-avail:hover{{background:var(--green-lt)}}
.cell-avail input[type=checkbox]{{display:none}}
.av-box{{
  width:24px;height:24px;
  border:2px solid var(--border2);border-radius:6px;
  display:flex;align-items:center;justify-content:center;
  font-size:14px;color:#fff;font-weight:700;
  transition:all .12s;background:transparent;user-select:none;
}}
.cell-avail:hover .av-box{{border-color:var(--green)}}
.cell-avail input:checked+.av-box{{
  background:var(--green);border-color:var(--green);
}}

/* ── Modal ── */
.modal-bg{{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.55);z-index:99;
  align-items:center;justify-content:center;
  backdrop-filter:blur(4px);
}}
.modal-bg.open{{display:flex}}
.modal{{
  background:var(--surface);border-radius:14px;padding:24px;
  width:340px;border:1px solid var(--border);
  box-shadow:0 16px 48px rgba(0,0,0,.28);
  transition:background .25s,border-color .25s;
}}
.m-head{{margin-bottom:18px}}
.m-title{{font-size:15px;font-weight:700;color:var(--text)}}
.m-ctx{{font-size:11px;color:var(--text3);margin-top:3px;display:flex;align-items:center;gap:6px}}
.m-dot{{width:6px;height:6px;border-radius:50%;background:var(--blue);flex-shrink:0}}
.field{{margin-bottom:14px}}
.field-lbl{{
  display:block;font-size:10px;font-weight:700;
  color:var(--text3);text-transform:uppercase;letter-spacing:.9px;
  margin-bottom:5px;
}}
.modal select{{width:100%;}}
.m-btns{{display:flex;gap:8px;margin-top:18px}}
.m-btns button{{
  flex:1;height:36px;border-radius:8px;
  border:1px solid var(--border2);cursor:pointer;
  font-size:12px;font-weight:600;font-family:'Sora',sans-serif;
  background:var(--surface2);color:var(--text2);transition:all .12s;
}}
.m-btns button:hover{{background:var(--surface);color:var(--text)}}
.btn-ok{{
  background:var(--blue)!important;
  border-color:var(--blue)!important;color:#fff!important;
}}
.btn-ok:hover{{opacity:.88!important}}

/* ── Toast ── */
.toast{{
  display:none;position:fixed;bottom:18px;right:18px;
  background:var(--green);color:#fff;
  padding:10px 18px;border-radius:9px;
  font-size:12px;font-weight:700;z-index:200;
  align-items:center;gap:7px;
  box-shadow:0 4px 18px rgba(0,0,0,.28);letter-spacing:.2px;
}}
.toast.show{{display:flex;animation:su .22s ease}}
@keyframes su{{from{{transform:translateY(8px);opacity:0}}to{{transform:translateY(0);opacity:1}}}}
</style>
</head>
<body>

<div class="toolbar">
  <span class="tbar-label">Vue</span>
  <select id="vType" onchange="switchView()">
    <option value="classe">Emploi — Classe</option>
    <option value="prof">Disponibilités — Prof</option>
  </select>
  <select id="vTarget" onchange="renderGrid()"></select>
  <div class="sep"></div>
  <button class="btn-save" onclick="saveAll()">Enregistrer</button>
</div>

<div id="infoBar" class="info-bar"></div>
<div class="prof-legend" id="profLegend"></div>

<div class="tbl-wrap">
  <table>
    <thead id="thead"></thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

<!-- Modal -->
<div class="modal-bg" id="overlay">
  <div class="modal">
    <div class="m-head">
      <div class="m-title" id="mTitle"></div>
      <div class="m-ctx"><div class="m-dot"></div><span id="mCtx"></span></div>
    </div>
    <div class="field">
      <span class="field-lbl">Matière</span>
      <select id="sSubj"></select>
    </div>
    <div class="field">
      <span class="field-lbl">Professeur</span>
      <select id="sProf"></select>
    </div>
    <div class="m-btns">
      <button onclick="closeModal()">Annuler</button>
      <button class="btn-ok" onclick="confirmSlot()">Confirmer</button>
    </div>
  </div>
</div>

<div class="toast" id="toast">Emploi du temps enregistré</div>

<script>
/* ── Data injected from Python ── */
const JOURS    = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"];
const DAY_CLS  = ["dh-lun","dh-mar","dh-mer","dh-jeu","dh-ven","dh-sam"];
const CRENEAUX = [
  {{s:"08:00",e:"09:00"}},
  {{s:"09:00",e:"10:00"}},
  {{s:"10:00",e:"11:00"}},
  {{s:"11:00",e:"12:00"}},
  {{s:"s:PAUSE",e:""}},
  {{s:"13:00",e:"14:00"}},
  {{s:"14:00",e:"15:00"}},
  {{s:"15:00",e:"16:00"}}
];
const CLASSES  = {classes_js};
const PROFS    = {profs_js};
const SUBJECTS = {subjects_js};

/* ── Colour pairs: [lightBg, lightFg, darkBg, darkFg] ── */
const PILL_COLORS = [
  ["#dce8fb","#1a56db","#162240","#7baffe"],
  ["#e0d4fb","#5b1fb5","#1e1540","#c4b5fd"],
  ["#ceeede","#0a7d52","#0e2d1f","#6ee7b7"],
  ["#fde4c0","#a14b07","#2d1f06","#fcd34d"],
  ["#fcd8d6","#9a3412","#2d1010","#fca5a5"],
  ["#fce7f3","#9d174d","#2d0f21","#f9a8d4"],
  ["#d6f4d6","#166534","#14290f","#86efac"],
  ["#e8eef6","#2e4264","#1e293b","#94a3b8"]
];

let isDark    = false;
let slots     = {{}};  /* key → {{prof,subj,s,e,jour,tgt}} */
let profAvail = {{}};  /* key → bool */
let pending   = null;
let profIdx   = {{}};

function pColor(name) {{
  if (!(name in profIdx)) profIdx[name] = Object.keys(profIdx).length % PILL_COLORS.length;
  const [lb,lf,db,df] = PILL_COLORS[profIdx[name]];
  return isDark ? {{bg:db,fg:df}} : {{bg:lb,fg:lf}};
}}

/* ══ THEME ══════════════════════════════════════════════════════ */
function applyTheme(dark) {{
  if (isDark === dark) return;
  isDark = dark;
  document.documentElement.classList.toggle('dark', dark);
  renderGrid();
}}

/* postMessage from Streamlit */
window.addEventListener('message', e => {{
  if (!e.data) return;
  if (e.data.type === 'streamlit:theme') applyTheme(e.data.theme === 'dark');
  if (e.data.stTheme) applyTheme(e.data.stTheme.base === 'dark');
}});

/* Poll parent body.fg-dark — most reliable */
function pollTheme() {{
  try {{
    const pb = window.parent.document.body;
    if (pb.classList.contains('fg-dark')) {{ applyTheme(true); return; }}
    const app = window.parent.document.querySelector('[data-testid="stAppViewContainer"]')
              || window.parent.document.querySelector('.stApp');
    if (app) {{
      const attr = app.getAttribute('data-theme');
      if (attr) {{ applyTheme(attr === 'dark'); return; }}
      /* luminance fallback */
      const bg = getComputedStyle(app).backgroundColor;
      const m  = bg.match(/\\d+/g);
      if (m && m.length >= 3) {{
        const lum = (+m[0]*299 + +m[1]*587 + +m[2]*114) / 1000;
        applyTheme(lum < 128); return;
      }}
    }}
    applyTheme(window.matchMedia('(prefers-color-scheme:dark)').matches);
  }} catch(e) {{
    applyTheme(window.matchMedia('(prefers-color-scheme:dark)').matches);
  }}
}}
pollTheme();
setInterval(pollTheme, 500);

/* ══ GRID ═══════════════════════════════════════════════════════ */
function switchView() {{
  const vt  = document.getElementById('vType').value;
  const sel = document.getElementById('vTarget');
  sel.innerHTML = '';
  const list = vt === 'classe' ? CLASSES : PROFS;
  if (!list.length) {{
    const o = document.createElement('option');
    o.value=''; o.textContent = vt==='classe'?'— Aucune classe —':'— Aucun professeur —';
    sel.appendChild(o);
  }} else {{
    list.forEach(v => {{
      const o = document.createElement('option');
      o.value=v; o.textContent=v; sel.appendChild(o);
    }});
  }}
  renderGrid();
}}

function renderGrid() {{
  const vt   = document.getElementById('vType').value;
  const tgt  = document.getElementById('vTarget').value;
  const thead = document.getElementById('thead');
  const tbody = document.getElementById('tbody');
  thead.innerHTML=''; tbody.innerHTML='';

  document.getElementById('infoBar').textContent = vt === 'prof'
    ? 'Cochez les cases pour marquer les créneaux de disponibilité du professeur.'
    : 'Cliquez sur une case vide pour assigner une matière et un professeur.';

  /* Header row */
  const htr = document.createElement('tr');
  const th0 = document.createElement('th'); th0.textContent='Horaire'; htr.appendChild(th0);
  JOURS.forEach((j,i) => {{
    const th = document.createElement('th');
    th.textContent = j;
    th.className   = DAY_CLS[i];
    htr.appendChild(th);
  }});
  thead.appendChild(htr);

  /* Body rows */
  CRENEAUX.forEach(cr => {{
    const isPause = cr.s === 's:PAUSE';
    const row = document.createElement('tr');
    if (isPause) row.className = 'break-row';

    /* Time cell */
    const tc = document.createElement('td');
    if (isPause) {{
      tc.className = 'td-break';
      tc.colSpan = 1;
      tc.innerHTML = '<div class="break-lbl">12:00 – 13:00 &nbsp;·&nbsp; Pause déjeuner</div>';
    }} else {{
      tc.className = 'td-time';
      tc.innerHTML = '<div class="time-main">' + cr.s + '</div><div class="time-end">' + cr.e + '</div>';
    }}
    row.appendChild(tc);

    JOURS.forEach(jour => {{
      const td = document.createElement('td');
      if (isPause) {{
        td.className = 'td-break';
        td.innerHTML = '<span style="color:var(--border2);font-size:11px">—</span>';
        td.style.textAlign='center';td.style.verticalAlign='middle';
        row.appendChild(td); return;
      }}

      const key = tgt + '||' + jour + '||' + cr.s;

      if (vt === 'prof') {{
        /* Availability checkbox */
        const lbl = document.createElement('label');
        lbl.className = 'cell-avail';
        lbl.title = jour + ' · ' + cr.s + ' – ' + cr.e;
        const inp = document.createElement('input');
        inp.type='checkbox'; inp.checked=!!profAvail[key];
        const box = document.createElement('div');
        box.className='av-box'; box.textContent=inp.checked?'✓':'';
        inp.addEventListener('change', function() {{
          profAvail[key]=this.checked;
          box.textContent=this.checked?'✓':'';
        }});
        lbl.appendChild(inp); lbl.appendChild(box); td.appendChild(lbl);
      }} else {{
        const sl = slots[key];
        if (sl) {{
          /* Filled slot */
          const c = pColor(sl.prof);
          const pill = document.createElement('div');
          pill.className='cell-pill';
          pill.style.background=c.bg; pill.style.color=c.fg;
          const ms = document.createElement('span'); ms.className='pill-subj'; ms.textContent=sl.subj;
          const ps = document.createElement('span'); ps.className='pill-prof'; ps.textContent=sl.prof;
          const rm = document.createElement('button'); rm.className='pill-rm'; rm.textContent='✕';
          rm.style.color=c.fg;
          rm.addEventListener('click', e => {{ e.stopPropagation(); delete slots[key]; renderGrid(); }});
          pill.appendChild(ms); pill.appendChild(ps); pill.appendChild(rm);
          td.appendChild(pill);
        }} else {{
          /* Empty cell */
          const em = document.createElement('div');
          em.className='cell-empty'; em.title='Ajouter (' + jour + ' ' + cr.s + ')';
          const plus = document.createElement('span'); plus.className='plus-glyph'; plus.textContent='+';
          em.appendChild(plus);
          em.addEventListener('click', () => openModal(jour, cr.s, cr.e, tgt, key));
          td.appendChild(em);
        }}
      }}
      row.appendChild(td);
    }});
    tbody.appendChild(row);
  }});

  /* Prof color legend */
  const leg = document.getElementById('profLegend');
  leg.innerHTML='';
  if (vt==='classe' && PROFS.length) {{
    PROFS.forEach(p => {{
      const c = pColor(p);
      const chip = document.createElement('span');
      chip.className='p-chip';
      chip.style.background=c.bg; chip.style.color=c.fg;
      chip.textContent=p;
      leg.appendChild(chip);
    }});
  }}
}}

/* ══ MODAL ══════════════════════════════════════════════════════ */
function openModal(jour, s, e, tgt, key) {{
  pending={{jour,s,e,tgt,key}};
  document.getElementById('mTitle').textContent = s + ' – ' + e;
  document.getElementById('mCtx').textContent   = jour + '  ·  ' + (document.getElementById('vType').value==='classe'?'Classe ':'' ) + tgt;

  const sp=document.getElementById('sSubj'); sp.innerHTML='';
  SUBJECTS.forEach(sub => {{
    const o=document.createElement('option'); o.value=sub; o.textContent=sub; sp.appendChild(o);
  }});
  if (slots[key]) sp.value=slots[key].subj;

  const sr=document.getElementById('sProf'); sr.innerHTML='';
  PROFS.forEach(p => {{
    const o=document.createElement('option'); o.value=p; o.textContent=p; sr.appendChild(o);
  }});
  if (slots[key]) sr.value=slots[key].prof;

  document.getElementById('overlay').classList.add('open');
}}
function closeModal() {{
  document.getElementById('overlay').classList.remove('open'); pending=null;
}}
function confirmSlot() {{
  if (!pending) return;
  const {{jour,s,e,tgt,key}}=pending;
  const subj=document.getElementById('sSubj').value;
  const prof=document.getElementById('sProf').value;

  /* Conflict detection */
  const conflict=Object.entries(slots).find(([k,v]) => {{
    const [t,j,h]=k.split('||');
    return j===jour && h===s && v.prof===prof && t!==tgt;
  }});
  if (conflict) {{
    alert('Conflit : ' + prof + ' a déjà un cours à ' + s + ' le ' + jour + ' (classe ' + conflict[0].split('||')[0] + ').');
    return;
  }}
  slots[key]={{prof,subj,s,e,jour,tgt}};
  closeModal(); renderGrid();
}}

/* ══ SAVE ═══════════════════════════════════════════════════════ */
function saveAll() {{
  try {{
    window.parent.postMessage({{type:'streamlit:setComponentValue',value:Object.values(slots)}}, '*');
  }} catch(e){{}}
  const t=document.getElementById('toast');
  t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2600);
}}

document.getElementById('overlay').addEventListener('click', function(e) {{
  if (e.target===this) closeModal();
}});

switchView();
</script>
</body>
</html>"""

    components.html(calendar_html, height=720, scrolling=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — Suivi des Présences
# ══════════════════════════════════════════════════════════════════════════════
elif selected_tab == "Suivi Présences":
    render_tab7(students_raw, logs_raw)