import os
import cv2
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
from enroll import enroll_student
import streamlit.components.v1 as components

init_db()

st.set_page_config(
    page_title="FaceGuard — Sécurité & Présence",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CSS 0000000000000000000000000 ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* Reset & base */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* Page background */
.stApp { background: #0d1117; }
.main .block-container { padding: 1.5rem 2rem 2rem; max-width: 1400px; }

/* Header brand bar */
.brand-bar {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 0 1.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 1.5rem;
}
.brand-logo {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
}
.brand-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 22px; font-weight: 700;
    color: #f0f6ff; letter-spacing: -0.3px;
}
.brand-sub { font-size: 12px; color: #6b7a99; margin-top: 2px; }
.brand-pill {
    margin-left: auto;
    background: rgba(34,197,94,0.12);
    border: 1px solid rgba(34,197,94,0.3);
    color: #4ade80;
    font-size: 11px; font-weight: 500;
    padding: 4px 10px; border-radius: 20px;
    display: flex; align-items: center; gap: 5px;
}
.brand-pill::before {
    content: '';
    width: 6px; height: 6px;
    background: #4ade80;
    border-radius: 50%;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

/* Metric cards */
.metric-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 24px; }
.metric-card {
    background: #161b26;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 20px 22px;
    position: relative; overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
}
.metric-card.blue::before  { background: linear-gradient(90deg,#3b82f6,#60a5fa); }
.metric-card.purple::before{ background: linear-gradient(90deg,#8b5cf6,#a78bfa); }
.metric-card.green::before { background: linear-gradient(90deg,#22c55e,#4ade80); }
.metric-card.amber::before { background: linear-gradient(90deg,#f59e0b,#fbbf24); }
.metric-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #6b7a99; margin-bottom: 8px; }
.metric-value { font-family: 'Space Grotesk', sans-serif; font-size: 32px; font-weight: 700; color: #f0f6ff; line-height: 1; }
.metric-icon { position: absolute; right: 18px; top: 18px; font-size: 22px; opacity: 0.2; }
.metric-delta { font-size: 11px; color: #6b7a99; margin-top: 6px; }

/* Hide default Streamlit metrics */
div[data-testid="metric-container"] { display: none !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: #161b26;
    border-radius: 12px;
    padding: 4px;
    border: 1px solid rgba(255,255,255,0.06);
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #6b7a99;
    font-size: 13px; font-weight: 500;
    padding: 8px 16px;
    border: none;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: #1e2535 !important;
    color: #93c5fd !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* Section headers */
.section-header {
    display: flex; align-items: center; gap: 10px;
    margin: 0 0 18px;
}
.section-header h2 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 17px; font-weight: 600;
    color: #e2e8f0; margin: 0;
}
.section-badge {
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.3);
    color: #93c5fd;
    font-size: 10px; font-weight: 600;
    padding: 2px 8px; border-radius: 20px;
    letter-spacing: 0.5px; text-transform: uppercase;
}

/* Tables */
.stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.07) !important; }
.stDataFrame [data-testid="stDataFrameResizable"] { background: #161b26; }
thead tr th {
    background: #1a2035 !important;
    color: #6b7a99 !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.6px !important;
    font-weight: 600 !important;
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
}

/* Forms */
.stTextInput input, .stSelectbox > div > div {
    background: #1a2035 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-size: 14px !important;
}
.stTextInput input:focus, .stSelectbox > div > div:focus-within {
    border-color: rgba(59,130,246,0.5) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}
label { color: #9aa5b8 !important; font-size: 13px !important; }

/* Buttons */
.stButton button {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    color: white !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 10px 20px !important;
    transition: all 0.2s !important;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3) !important;
}
.stButton button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(59,130,246,0.4) !important;
}

/* Form submit button */
.stFormSubmitButton button {
    width: 100% !important;
    margin-top: 8px !important;
}

/* Info / warning / success */
.stAlert {
    background: #161b26 !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #9aa5b8 !important;
}

/* Checkbox */
.stCheckbox label { color: #9aa5b8 !important; }

/* Camera card */
.cam-container {
    background: #161b26;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    overflow: hidden;
}
.cam-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    font-size: 12px; color: #6b7a99;
}
.cam-live-dot {
    display: inline-block;
    width: 7px; height: 7px;
    background: #ef4444;
    border-radius: 50%;
    animation: pulse 1.5s infinite;
}

/* Legend pills */
.legend-grid { display: flex; flex-direction: column; gap: 8px; }
.legend-item {
    display: flex; align-items: center; gap: 10px;
    background: #1a2035;
    border-radius: 8px; padding: 10px 12px;
    font-size: 13px; color: #9aa5b8;
}
.leg-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* Stat row for tab7 */
.stat-row {
    display: flex; gap: 10px; margin-bottom: 18px; flex-wrap: wrap;
}
.stat-chip {
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px; font-weight: 600;
    display: flex; align-items: center; gap: 6px;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.06) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ─── Auto-refresh ──────────────────────────────────────────────────────────────
count = st_autorefresh(interval=2000, limit=None, key="dashboard_autorefresh")

# ─── Brand Header ──────────────────────────────────────────────────────────────
now_str = datetime.now().strftime("%A %d %B %Y — %H:%M:%S")
st.markdown(f"""
<div class="brand-bar">
    <div class="brand-logo">🔐</div>
    <div>
        <div class="brand-title">FaceGuard</div>
        <div class="brand-sub">Système de reconnaissance faciale — Raspberry Pi</div>
    </div>
    <div class="brand-pill">Système actif</div>
</div>
""", unsafe_allow_html=True)

# ─── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def get_data():
    session = Session()
    students = session.query(Student).all()
    logs = session.query(AccessLog).order_by(AccessLog.timestamp.desc()).all()
    # Detach from session
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

today = date.today()
logs_today = [l for l in logs_raw if l["timestamp"].date() == today]
students_inside = [s for s in students_raw if s["inside"]]
profs_inside = [s for s in students_inside if s["category"] and s["category"].lower() == "prof"]
admin_inside = [s for s in students_inside if s["category"] and s["category"].lower() == "admin"]
eleves_inside = [s for s in students_inside if s["category"] and s["category"].lower() == "eleve"]

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📊  Vue d'ensemble",
    "📋  Historique",
    "👥  Annuaire",
    "📷  Supervision Live",
    "➕  Inscription",
    "🗓️  Emplois du Temps",
    "✅  Suivi Présences"
])
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = tabs

# ══════════════════════════════════════════════════════════════
# TAB 1 — Vue d'ensemble
# ══════════════════════════════════════════════════════════════
with tab1:
    # KPI cards via HTML
    total_alerts_today = len([l for l in logs_today if not l["granted"]])
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card blue">
            <div class="metric-icon">🎓</div>
            <div class="metric-label">Total Inscrits</div>
            <div class="metric-value">{len(students_raw)}</div>
            <div class="metric-delta">Membres enregistrés</div>
        </div>
        <div class="metric-card green">
            <div class="metric-icon">🟢</div>
            <div class="metric-label">À l'intérieur</div>
            <div class="metric-value">{len(students_inside)}</div>
            <div class="metric-delta">{len(eleves_inside)} élèves · {len(profs_inside)} profs</div>
        </div>
        <div class="metric-card purple">
            <div class="metric-icon">👔</div>
            <div class="metric-label">Personnel présent</div>
            <div class="metric-value">{len(profs_inside) + len(admin_inside)}</div>
            <div class="metric-delta">{len(admin_inside)} admins · {len(profs_inside)} enseignants</div>
        </div>
        <div class="metric-card amber">
            <div class="metric-icon">🔔</div>
            <div class="metric-label">Événements du jour</div>
            <div class="metric-value">{len(logs_today)}</div>
            <div class="metric-delta">{total_alerts_today} accès refusés</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Activity timeline (last 10 logs)
    st.markdown('<div class="section-header"><h2>Activité Récente</h2><span class="section-badge">Temps réel</span></div>', unsafe_allow_html=True)

    if logs_raw:
        recent = logs_raw[:10]
        tl_html = '<div style="display:flex;flex-direction:column;gap:6px;">'
        for l in recent:
            is_in = l["action"] and l["action"].lower() in ["in", "entrée", "enter", "entry"]
            granted = l["granted"]
            icon = "🟢" if (granted and is_in) else ("🔴" if not granted else "🔵")
            action_label = "Entrée" if is_in else "Sortie"
            color = "#4ade80" if granted else "#f87171"
            ts = l["timestamp"].strftime("%H:%M:%S")
            tl_html += f"""
            <div style="display:flex;align-items:center;gap:12px;background:#161b26;
                        border:1px solid rgba(255,255,255,0.06);border-radius:10px;
                        padding:10px 14px;">
                <span style="font-size:16px">{icon}</span>
                <span style="font-size:12px;color:#6b7a99;min-width:70px;font-variant-numeric:tabular-nums">{ts}</span>
                <span style="color:#e2e8f0;font-size:13px;font-weight:500;flex:1">{l['name']}</span>
                <span style="font-size:12px;color:{color};font-weight:600">{action_label}</span>
                <span style="font-size:11px;color:#4b5568;background:#1a2035;padding:2px 8px;border-radius:5px">
                    {'✓ Autorisé' if granted else '✗ Refusé'}
                </span>
            </div>"""
        tl_html += "</div>"
        st.markdown(tl_html, unsafe_allow_html=True)
    else:
        st.info("Aucune activité enregistrée.")

    # Category breakdown
    st.markdown('<br><div class="section-header"><h2>Répartition par Catégorie</h2></div>', unsafe_allow_html=True)
    cats = {"eleve": 0, "prof": 0, "admin": 0}
    for s in students_raw:
        c = (s["category"] or "eleve").lower()
        if c in cats:
            cats[c] += 1

    col_a, col_b, col_c = st.columns(3)
    for col, (cat, cnt) in zip([col_a, col_b, col_c], cats.items()):
        icons = {"eleve": "🎓", "prof": "📚", "admin": "⚙️"}
        labels = {"eleve": "Élèves", "prof": "Professeurs", "admin": "Administration"}
        pct = round(cnt / max(len(students_raw), 1) * 100)
        col.markdown(f"""
        <div style="background:#161b26;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px 18px;text-align:center;">
            <div style="font-size:28px;margin-bottom:6px">{icons[cat]}</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:26px;font-weight:700;color:#f0f6ff">{cnt}</div>
            <div style="font-size:12px;color:#6b7a99;margin-top:2px">{labels[cat]}</div>
            <div style="margin-top:10px;background:#1a2035;border-radius:6px;height:4px;overflow:hidden;">
                <div style="background:linear-gradient(90deg,#3b82f6,#8b5cf6);height:100%;width:{pct}%;transition:width 0.5s;"></div>
            </div>
            <div style="font-size:11px;color:#4b5568;margin-top:4px">{pct}%</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 2 — Historique
# ══════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header"><h2>Historique des Accès</h2><span class="section-badge">200 derniers</span></div>', unsafe_allow_html=True)

    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        search_name = st.text_input("🔍 Rechercher par nom", placeholder="Nom de la personne…", key="log_search")
    with col_f2:
        filter_action = st.selectbox("Action", ["Tous", "Entrée", "Sortie"], key="log_action")
    with col_f3:
        filter_granted = st.selectbox("Statut", ["Tous", "Autorisé", "Refusé"], key="log_granted")

    if logs_raw:
        log_data = []
        for l in logs_raw[:200]:
            is_in = l["action"] and l["action"].lower() in ["in", "entrée", "enter", "entry"]
            action_str = "Entrée" if is_in else "Sortie"
            granted_str = "✓ Autorisé" if l["granted"] else "✗ Refusé"
            log_data.append({
                "Date / Heure": l["timestamp"].strftime("%d/%m/%Y %H:%M:%S"),
                "Nom": l["name"],
                "Action": action_str,
                "Accès": granted_str
            })

        df_logs = pd.DataFrame(log_data)

        # Apply filters
        if search_name:
            df_logs = df_logs[df_logs["Nom"].str.contains(search_name, case=False, na=False)]
        if filter_action != "Tous":
            df_logs = df_logs[df_logs["Action"] == filter_action]
        if filter_granted == "Autorisé":
            df_logs = df_logs[df_logs["Accès"].str.startswith("✓")]
        elif filter_granted == "Refusé":
            df_logs = df_logs[df_logs["Accès"].str.startswith("✗")]

        def style_access(val):
            if val.startswith("✓"):
                return "color: #4ade80; font-weight: 600"
            return "color: #f87171; font-weight: 600"

        def style_action(val):
            if val == "Entrée":
                return "color: #60a5fa"
            return "color: #c084fc"

        styled = df_logs.style.map(style_access, subset=["Accès"]).map(style_action, subset=["Action"])
        st.dataframe(styled, use_container_width=True, height=520)
        st.caption(f"{len(df_logs)} enregistrement(s) affiché(s)")
    else:
        st.info("Aucun historique trouvé.")


# ══════════════════════════════════════════════════════════════
# TAB 3 — Annuaire
# ══════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header"><h2>Annuaire — Personnels & Élèves</h2></div>', unsafe_allow_html=True)

    # Search + filter
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search_annuaire = st.text_input("🔍 Rechercher", placeholder="Nom ou classe…", key="ann_search")
    with col_s2:
        cat_filter = st.selectbox("Catégorie", ["Tous", "Eleve", "Prof", "Admin"], key="ann_cat")

    if students_raw:
        student_data = []
        for s in students_raw:
            cat = s["category"] or "eleve"
            cat_label = {"eleve": "🎓 Élève", "prof": "📚 Prof", "admin": "⚙️ Admin"}.get(cat.lower(), cat.capitalize())
            status = "🟢 Présent" if s["inside"] else "⚫ Absent"
            student_data.append({
                "Nom": s["name"],
                "Catégorie": cat_label,
                "Classe / Poste": s["grade"] or "—",
                "Enrôlé": "✓ Oui" if s["enrolled"] else "✗ Non",
                "Statut": status
            })

        df_stu = pd.DataFrame(student_data)

        # Filters
        if search_annuaire:
            mask = df_stu["Nom"].str.contains(search_annuaire, case=False, na=False) | \
                   df_stu["Classe / Poste"].str.contains(search_annuaire, case=False, na=False)
            df_stu = df_stu[mask]
        if cat_filter != "Tous":
            df_stu = df_stu[df_stu["Catégorie"].str.contains(cat_filter, case=False)]

        def style_status_ann(val):
            if "Présent" in val:
                return "color: #4ade80; font-weight: 600"
            return "color: #6b7a99"

        def style_enrolled(val):
            if val.startswith("✓"):
                return "color: #4ade80"
            return "color: #f87171"

        styled_stu = df_stu.style.map(style_status_ann, subset=["Statut"]).map(style_enrolled, subset=["Enrôlé"])
        st.dataframe(styled_stu, use_container_width=True, height=520)
        st.caption(f"{len(df_stu)} personne(s)")
    else:
        st.info("Aucune personne inscrite dans la base de données.")


# ══════════════════════════════════════════════════════════════
# TAB 4 — Supervision Live
# ══════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header"><h2>Supervision Caméra</h2><span class="section-badge">Temps réel</span></div>', unsafe_allow_html=True)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(BASE_DIR, "supervision.jpg")

    col_cam, col_info = st.columns([3, 1])

    with col_cam:
        st.markdown(f"""
        <div class="cam-container">
            <div class="cam-header">
                <span><span class="cam-live-dot"></span> &nbsp;CAM-01 — Entrée principale</span>
                <span>{datetime.now().strftime("%H:%M:%S")}</span>
            </div>
        """, unsafe_allow_html=True)

        if os.path.exists(image_path):
            try:
                frame = cv2.imread(image_path)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                st.image(frame, channels="RGB", use_container_width=True, clamp=True)
            except Exception:
                st.error("Erreur de chargement du flux vidéo.")
        else:
            st.markdown("""
            <div style="background:#0d1117;padding:60px 20px;text-align:center;border-radius:0 0 12px 12px;">
                <div style="font-size:48px;margin-bottom:12px">📷</div>
                <p style="color:#6b7a99;font-size:14px">Flux vidéo indisponible</p>
                <p style="color:#4b5568;font-size:12px">Lancez <code style="background:#1a2035;padding:2px 6px;border-radius:4px">main3.py</code> pour démarrer la caméra</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with col_info:
        st.markdown("""
        <div style="background:#161b26;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px;">
            <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.8px;color:#6b7a99;margin-bottom:12px;font-weight:600;">Légende</div>
            <div class="legend-grid">
                <div class="legend-item"><div class="leg-dot" style="background:#22c55e"></div>Accès autorisé</div>
                <div class="legend-item"><div class="leg-dot" style="background:#f59e0b"></div>Identification...</div>
                <div class="legend-item"><div class="leg-dot" style="background:#ef4444"></div>Accès refusé</div>
                <div class="legend-item"><div class="leg-dot" style="background:#8b5cf6"></div>Spoofing détecté</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick stats for cam
        entries_today = len([l for l in logs_today if l["action"] and l["action"].lower() in ["in","entrée","enter","entry"]])
        exits_today = len(logs_today) - entries_today
        refused_today = len([l for l in logs_today if not l["granted"]])

        for label, val, color in [
            ("Entrées aujourd'hui", entries_today, "#3b82f6"),
            ("Sorties aujourd'hui", exits_today, "#8b5cf6"),
            ("Accès refusés", refused_today, "#ef4444")
        ]:
            st.markdown(f"""
            <div style="background:#161b26;border:1px solid rgba(255,255,255,0.07);border-radius:10px;
                        padding:12px 14px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
                <span style="font-size:12px;color:#6b7a99">{label}</span>
                <span style="font-family:'Space Grotesk',sans-serif;font-size:20px;font-weight:700;color:{color}">{val}</span>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 5 — Inscription
# ══════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-header"><h2>Nouvelle Inscription</h2></div>', unsafe_allow_html=True)

    col_form, col_guide = st.columns([1, 1])

    with col_form:
        st.markdown("""
        <div style="background:#161b26;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:22px 24px;margin-bottom:4px;">
            <div style="font-size:13px;color:#6b7a99;margin-bottom:16px;">
                Remplissez le formulaire, puis l'enrôlement biométrique démarrera automatiquement via la caméra.
            </div>
        """, unsafe_allow_html=True)

        with st.form("enrollment_form", clear_on_submit=True):
            name = st.text_input("Nom Complet *", placeholder="Ex: Amine Ben Ali")
            student_id = st.text_input("Matricule / ID *", placeholder="Ex: STU-2024-001")
            grade = st.text_input("Classe ou Fonction", placeholder="Ex: 7A, Directeur pédagogique")
            category = st.selectbox("Catégorie *", ["eleve", "prof", "admin"],
                                    format_func=lambda x: {"eleve": "🎓 Élève", "prof": "📚 Professeur", "admin": "⚙️ Administrateur"}[x])
            submitted = st.form_submit_button("🎥  Démarrer l'Inscription")

        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            if name and student_id:
                with st.spinner(f"Enrôlement de {name} en cours..."):
                    enroll_student(name, student_id, grade, category)
                st.success(f"✅ Inscription de **{name}** terminée avec succès !")
                st.cache_data.clear()
            else:
                st.error("Veuillez remplir au moins le nom et le matricule.")

    with col_guide:
        st.markdown("""
        <div style="background:#161b26;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:22px 24px;">
            <div style="font-size:13px;font-weight:600;color:#e2e8f0;margin-bottom:14px;">📋 Guide d'enrôlement</div>
            <div style="display:flex;flex-direction:column;gap:10px;">
        """, unsafe_allow_html=True)

        steps = [
            ("1", "Remplissez le formulaire avec les informations correctes.", "#3b82f6"),
            ("2", "Cliquez sur « Démarrer l'Inscription ».", "#6366f1"),
            ("3", "Regardez la caméra — restez immobile.", "#8b5cf6"),
            ("4", "Le système capture plusieurs échantillons du visage.", "#a78bfa"),
            ("5", "L'enrôlement est terminé automatiquement.", "#22c55e"),
        ]
        steps_html = ""
        for num, text, color in steps:
            steps_html += f"""
            <div style="display:flex;align-items:flex-start;gap:10px;background:#1a2035;border-radius:8px;padding:10px 12px;">
                <span style="background:{color}22;color:{color};font-size:11px;font-weight:700;
                             padding:2px 7px;border-radius:5px;flex-shrink:0">{num}</span>
                <span style="font-size:12px;color:#9aa5b8;line-height:1.5">{text}</span>
            </div>"""

        st.markdown(steps_html + "</div></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 6 — Emplois du Temps
# ══════════════════════════════════════════════════════════════
with tab6:
    st.header("Emplois du Temps")
    
    classes = sorted(set(s.get("grade") for s in students_raw if s.get("grade") and s.get("category") == "eleve"))
    profs   = sorted(s.get("name") for s in students_raw if s.get("category") == "prof")
    subjects = ["Mathématiques","Français","Arabe","Sciences","Histoire-Géo","Éducation physique","Art plastique"]
    
    classes_js  = str(classes).replace("'", '"')
    profs_js    = str(profs).replace("'", '"')
    subjects_js = str(subjects).replace("'", '"')

    calendar_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
    <style>
    *{{box-sizing:border-box;margin:0;padding:0;font-family:sans-serif}}
    body{{background:#fff;color:#111;padding:12px}}
    .toolbar{{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}}
    select,input{{height:34px;padding:0 10px;border:1px solid #ddd;border-radius:8px;font-size:13px;background:#fff;color:#111}}
    button{{height:34px;padding:0 14px;border:1px solid #ddd;border-radius:8px;font-size:13px;background:#fff;cursor:pointer}}
    button:hover{{background:#f5f5f5}}
    button.primary{{background:#e6f1fb;border-color:#378add;color:#185fa5}}
    table{{width:100%;border-collapse:collapse;font-size:12px}}
    th{{padding:8px 5px;text-align:center;background:#f8f8f8;border:1px solid #e8e8e8;font-weight:500;color:#666}}
    th.time-col{{text-align:left;padding-left:10px;width:100px}}
    td{{border:1px solid #e8e8e8;vertical-align:top;padding:3px;height:62px;position:relative;cursor:pointer}}
    td:hover:not(.time-cell):not(.pause-cell){{background:#f0f7ff}}
    td.time-cell{{background:#f8f8f8;cursor:default;vertical-align:middle;padding:6px 10px;color:#888;font-size:11px}}
    td.pause-cell{{background:#fafafa;cursor:default;text-align:center;vertical-align:middle;color:#bbb;font-size:11px}}
    .pill{{border-radius:6px;padding:3px 6px;height:100%;display:flex;flex-direction:column;justify-content:center;gap:1px;position:relative;min-height:52px}}
    .pill .del{{position:absolute;top:3px;right:3px;width:15px;height:15px;border-radius:50%;background:rgba(0,0,0,.15);border:none;cursor:pointer;display:none;font-size:10px;line-height:15px;text-align:center;padding:0}}
    .pill:hover .del{{display:block}}
    .overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:99;align-items:center;justify-content:center}}
    .overlay.open{{display:flex}}
    .modal{{background:#fff;border-radius:12px;padding:1.5rem;width:340px;border:1px solid #ddd}}
    .modal h3{{font-size:15px;font-weight:500;margin-bottom:4px}}
    .modal .ctx{{font-size:12px;color:#888;margin-bottom:12px}}
    .modal label{{display:block;font-size:12px;color:#666;margin-top:10px;margin-bottom:3px}}
    .modal select{{width:100%}}
    .modal-btns{{display:flex;gap:8px;margin-top:14px}}
    .modal-btns button{{flex:1;height:36px;border-radius:8px;border:1px solid #ddd;cursor:pointer;font-size:13px}}
    .modal-btns .ok{{background:#e8f5e9;border-color:#4caf50;color:#2e7d32}}
    .legend{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}}
    .leg-chip{{font-size:11px;padding:2px 10px;border-radius:20px;font-weight:500}}
    .save-banner{{display:none;margin-top:10px;padding:10px 14px;background:#e8f5e9;border:1px solid #4caf50;border-radius:8px;font-size:13px;color:#2e7d32}}
    </style>
    </head>
    <body>

    <div class="toolbar">
      <span style="font-size:13px;color:#666">Voir par :</span>
      <select id="vType" onchange="switchView()">
        <option value="classe">Classe</option>
        <option value="prof">Professeur</option>
      </select>
      <select id="vTarget" onchange="renderGrid()"></select>
      <button class="primary" onclick="saveAll()">&#10003; Enregistrer tout</button>
    </div>

    <div class="legend" id="legend"></div>

    <table><thead id="thead"></thead><tbody id="tbody"></tbody></table>

    <div class="save-banner" id="saveBanner">Emploi du temps enregistré avec succès !</div>

    <div class="overlay" id="overlay">
    <div class="modal">
      <h3 id="mTitle">Assigner un créneau</h3>
      <p class="ctx" id="mCtx"></p>
      <label id="lProf">Professeur</label>
      <select id="sProf"></select>
      <label>Matière</label>
      <select id="sSubj"></select>
      <div class="modal-btns">
        <button onclick="closeModal()">Annuler</button>
        <button class="ok" onclick="confirmSlot()">Confirmer</button>
      </div>
    </div>
    </div>

    <script>
    const JOURS   = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"];
    const CRENEAUX= [["08:00","09:00"],["09:00","10:00"],["10:00","11:00"],["11:00","12:00"],["13:00","14:00"],["14:00","15:00"]];
    const CLASSES  = {classes_js};
    const PROFS    = {profs_js};
    const SUBJECTS = {subjects_js};
    const COLORS   = ["#378ADD","#1D9E75","#D85A30","#D4537E","#639922","#BA7517","#534AB7"];
    const COLORS_BG= ["#E6F1FB","#E1F5EE","#FAECE7","#FBEAF0","#EAF3DE","#FAEEDA","#EEEDFE"];
    let slots = {{}};
    let pending = null;
    let profIdx = {{}};

    function pColor(p,bg=false){{
      if(!(p in profIdx)) profIdx[p]=Object.keys(profIdx).length % COLORS.length;
      return bg ? COLORS_BG[profIdx[p]] : COLORS[profIdx[p]];
    }}

    function switchView(){{
      const t = document.getElementById('vType').value;
      const sel = document.getElementById('vTarget');
      sel.innerHTML='';
      (t==='classe'?CLASSES:PROFS).forEach(v=>{{
        const o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o);
      }});
      renderGrid();
    }}

    function renderGrid(){{
      const vt=document.getElementById('vType').value;
      const tgt=document.getElementById('vTarget').value;
      const thead=document.getElementById('thead');
      const tbody=document.getElementById('tbody');
      thead.innerHTML=''; tbody.innerHTML='';
      let tr=document.createElement('tr');
      let th0=document.createElement('th'); th0.className='time-col'; th0.textContent='Horaire'; tr.appendChild(th0);
      JOURS.forEach(j=>{{ const th=document.createElement('th');th.textContent=j;tr.appendChild(th); }});
      thead.appendChild(tr);

      const allC=[["08:00","09:00"],["09:00","10:00"],["10:00","11:00"],["11:00","12:00"],["PAUSE",""],["13:00","14:00"],["14:00","15:00"]];
      allC.forEach(([s,e])=>{{
        const row=document.createElement('tr');
        const tc=document.createElement('td'); tc.className='time-cell';
        if(s==='PAUSE'){{ tc.textContent='12:00 – 13:00'; }}
        else {{ tc.innerHTML='<strong>'+s+'</strong><br><span style="opacity:.6">'+e+'</span>'; }}
        row.appendChild(tc);
        JOURS.forEach(jour=>{{
          const td=document.createElement('td');
          if(s==='PAUSE'){{ td.className='pause-cell'; td.textContent='Pause déjeuner'; row.appendChild(td); return; }}
          const key=tgt+'||'+jour+'||'+s;
          const sl=slots[key];
          if(sl){{
            const pill=document.createElement('div'); pill.className='pill';
            const c=vt==='classe'?pColor(sl.prof):pColor(sl.classe);
            const bg=vt==='classe'?pColor(sl.prof,true):pColor(sl.classe,true);
            pill.style.background=bg; pill.style.color=c;
            const lbl=vt==='classe'?sl.prof:sl.classe;
            pill.innerHTML='<span style="font-weight:500">'+lbl+'</span><span style="font-size:10px;opacity:.75">'+sl.subj+'</span><button class="del" onclick="delSlot(event,\\''+key+'\\')">×</button>';
            td.appendChild(pill);
          }} else {{
            td.innerHTML='<span style="position:absolute;bottom:4px;right:6px;font-size:18px;color:#ddd;line-height:1">+</span>';
            td.onclick=()=>openModal(jour,s,e,tgt,vt,key);
          }}
          row.appendChild(td);
        }});
        tbody.appendChild(row);
      }});
      renderLegend(vt);
    }}

    function renderLegend(vt){{
      const row=document.getElementById('legend'); row.innerHTML='';
      if(vt!=='classe') return;
      PROFS.forEach(p=>{{
        const c=document.createElement('span'); c.className='leg-chip';
        c.style.background=pColor(p,true); c.style.color=pColor(p);
        c.textContent=p; row.appendChild(c);
      }});
    }}

    function openModal(jour,s,e,tgt,vt,key){{
      pending={{jour,s,e,tgt,vt,key}};
      document.getElementById('mTitle').textContent=s+' – '+e;
      document.getElementById('mCtx').textContent=jour+' · '+(vt==='classe'?'Classe '+tgt:tgt);
      const sProf=document.getElementById('sProf');
      const sSubj=document.getElementById('sSubj');
      sProf.innerHTML=''; sSubj.innerHTML='';
      const list=vt==='classe'?PROFS:CLASSES;
      list.forEach(v=>{{ const o=document.createElement('option');o.value=v;o.textContent=v;sProf.appendChild(o); }});
      document.getElementById('lProf').textContent=vt==='classe'?'Professeur':'Classe';
      SUBJECTS.forEach(s=>{{ const o=document.createElement('option');o.value=s;o.textContent=s;sSubj.appendChild(o); }});
      document.getElementById('overlay').classList.add('open');
    }}

    function closeModal(){{ document.getElementById('overlay').classList.remove('open'); pending=null; }}

    function confirmSlot(){{
      if(!pending) return;
      const {{jour,s,e,tgt,vt,key}}=pending;
      const prof=vt==='classe'?document.getElementById('sProf').value:tgt;
      const classe=vt==='classe'?tgt:document.getElementById('sProf').value;
      const subj=document.getElementById('sSubj').value;
      const conflict=Object.entries(slots).find(([k,v])=>{{
        const [t,j,h]=k.split('||');
        return j===jour && h===s && v.prof===prof && t!==tgt;
      }});
      if(conflict){{ alert('Conflit : '+prof+' a déjà un cours à '+s+' le '+jour+' (classe '+conflict[1].classe+')'); return; }}
      slots[key]={{prof,classe,subj,start:s,end:e,jour}};
      closeModal(); renderGrid();
    }}

    function delSlot(e,key){{ e.stopPropagation(); delete slots[key]; renderGrid(); }}

    function saveAll(){{
      const data=Object.values(slots);
      // Envoyer les données à Streamlit via query params
      const encoded=encodeURIComponent(JSON.stringify(data));
      window.parent.postMessage({{type:'streamlit:setComponentValue', value:data}}, '*');
      document.getElementById('saveBanner').style.display='block';
      setTimeout(()=>document.getElementById('saveBanner').style.display='none', 3000);itchView();
    </script>
    </body>
    </html>
    """
    
    result = components.html(calendar_html, height=620, scrolling=True)
# ══════════════════════════════════════════════════════════════
# TAB 7 — Suivi des Présences
# ══════════════════════════════════════════════════════════════
with tab7:
    render_tab7(students_raw, logs_raw)