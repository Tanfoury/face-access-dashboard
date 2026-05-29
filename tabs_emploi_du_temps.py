"""
tabs_emploi_du_temps.py
=======================
Remplace tab6 et tab7 dans dash.py

Copie ces deux blocs dans ton dashboard.py en remplacement des anciens tab6 et tab7.
Assure-toi d'importer depuis database_schedule.py :

    from database_schedule import (
        init_db, get_all_subjects, add_subject,
        save_time_slot, delete_time_slot,
        get_time_slots, get_schedule_grid,
        CRENEAUX, JOURS
    )
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from database1 import (
    get_all_subjects, add_subject,
    save_time_slot, delete_time_slot,
    get_time_slots, get_schedule_grid,
    CRENEAUX, JOURS, Session, Student, AccessLog
)

# ============================================================
# TAB 6 — Gestion des Emplois du Temps
# ============================================================

def render_tab6(students):
    st.header("📅 Gestion des Emplois du Temps")

    # ── Extraire classes et profs depuis la BDD ──────────────
    classes = sorted(set(s.get("grade") for s in students if s.get("grade") and s.get("category") == "eleve"))
    profs   = sorted(s.get("name") for s in students if s.get("category") == "prof")
    subjects = get_all_subjects()
    subject_map = {s.name: s.id for s in subjects}

    # ── Sous-onglets ─────────────────────────────────────────
    sub1, sub2, sub3 = st.tabs(["➕ Ajouter un créneau", "📋 Voir l'emploi du temps", "🔧 Gérer les matières"])

    # ────────────────────────────────────────────────────────
    # Sous-onglet 1 : Ajouter un créneau
    # ────────────────────────────────────────────────────────
    with sub1:
        st.subheader("Assigner un prof à une classe sur un créneau")
        st.info("ℹ️ Les administrateurs **n'ont pas besoin** d'emploi du temps : ils sont présents tous les jours de **8h à 15h** (pause 12h-13h) automatiquement.")

        col_f1, col_f2 = st.columns(2)

        with col_f1:
            with st.form("form_add_slot", clear_on_submit=True):
                st.markdown("#### Nouveau créneau")

                jour = st.selectbox("Jour", JOURS)

                # Créneaux disponibles formatés
                creneaux_labels = [f"{s} → {e}" for s, e in CRENEAUX]
                creneau_idx = st.selectbox("Créneau horaire", range(len(creneaux_labels)),
                                           format_func=lambda i: creneaux_labels[i])
                start_time, end_time = CRENEAUX[creneau_idx]

                if classes:
                    classe = st.selectbox("Classe", classes)
                else:
                    classe = st.text_input("Classe (ex: 6A)")

                if profs:
                    prof = st.selectbox("Professeur", profs)
                else:
                    prof = st.text_input("Nom du professeur")

                # Matière (optionnel)
                matiere_options = ["— Aucune matière —"] + list(subject_map.keys())
                matiere_choice  = st.selectbox("Matière", matiere_options)
                subject_id = subject_map.get(matiere_choice) if matiere_choice != "— Aucune matière —" else None

                submitted = st.form_submit_button("✅ Enregistrer le créneau", use_container_width=True)

                if submitted:
                    if not classe or not prof:
                        st.error("Veuillez remplir la classe et le professeur.")
                    else:
                        slot, err = save_time_slot(jour, start_time, end_time, classe, prof, subject_id)
                        if err:
                            st.error(err)
                        else:
                            st.success(f"✅ Créneau enregistré : {jour} {start_time}-{end_time} | {classe} | {prof}")
                            st.rerun()

        with col_f2:
            st.markdown("#### Récapitulatif rapide")
            st.markdown("**Règle des admins (automatique) :**")
            admin_data = []
            for cren_s, cren_e in CRENEAUX:
                admin_data.append({"Créneau": f"{cren_s} - {cren_e}", "Statut": "✅ Présent"})
            df_admin = pd.DataFrame(admin_data)
            st.dataframe(df_admin, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("**Pause automatique :** 🕛 12:00 - 13:00 (tout le monde)")

    # ────────────────────────────────────────────────────────
    # Sous-onglet 2 : Voir l'emploi du temps
    # ────────────────────────────────────────────────────────
    with sub2:
        st.subheader("Consulter un emploi du temps")

        view_type = st.radio("Voir par :", ["Classe", "Professeur"], horizontal=True)

        if view_type == "Classe":
            if classes:
                selected = st.selectbox("Choisir la classe", classes, key="view_class")
                grid = get_schedule_grid(class_name=selected)
            else:
                st.warning("Aucune classe trouvée.")
                grid = {}
        else:
            if profs:
                selected = st.selectbox("Choisir le professeur", profs, key="view_prof")
                grid = get_schedule_grid(prof_name=selected)
            else:
                st.warning("Aucun professeur trouvé.")
                grid = {}

        if grid:
            # Construire tableau HTML visuel
            creneaux_labels = [f"{s}-{e}" for s, e in CRENEAUX]
            rows = []
            for start, end in CRENEAUX:
                row = {"Horaire": f"🕐 {start} - {end}"}
                for jour in JOURS:
                    slot = grid.get(jour, {}).get(start)
                    if start == "12:00":
                        row[jour] = "🍽️ Pause"
                    elif slot:
                        matiere = f" ({slot['subject']})" if slot['subject'] != '-' else ""
                        if view_type == "Classe":
                            row[jour] = f"👨‍🏫 {slot['prof_name']}{matiere}"
                        else:
                            row[jour] = f"🏫 {slot['class_name']}{matiere}"
                    else:
                        row[jour] = "—"
                rows.append(row)

            df_grid = pd.DataFrame(rows)
            st.dataframe(df_grid.set_index("Horaire"), use_container_width=True, height=320)

            # Bouton suppression
            st.markdown("---")
            st.markdown("#### Supprimer un créneau")
            all_slots = get_time_slots(
                class_name=selected if view_type == "Classe" else None,
                prof_name=selected if view_type == "Professeur" else None
            )
            if all_slots:
                slot_labels = {
                    f"{s['day']} {s['start_time']}-{s['end_time']} | {s['class_name']} | {s['prof_name']}": s['id']
                    for s in all_slots
                }
                to_delete = st.selectbox("Sélectionner le créneau à supprimer", list(slot_labels.keys()))
                if st.button("🗑️ Supprimer ce créneau", type="secondary"):
                    delete_time_slot(slot_labels[to_delete])
                    st.success("Créneau supprimé.")
                    st.rerun()
            else:
                st.info("Aucun créneau défini pour cette sélection.")

    # ────────────────────────────────────────────────────────
    # Sous-onglet 3 : Gérer les matières
    # ────────────────────────────────────────────────────────
    with sub3:
        st.subheader("Catalogue des matières")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            with st.form("form_add_subject", clear_on_submit=True):
                st.markdown("#### Ajouter une matière")
                sub_name = st.text_input("Nom complet", placeholder="ex: Mathématiques")
                sub_code = st.text_input("Code court", placeholder="ex: MATH")
                if st.form_submit_button("➕ Ajouter", use_container_width=True):
                    if sub_name and sub_code:
                        _, created = add_subject(sub_name, sub_code)
                        if created:
                            st.success(f"Matière '{sub_name}' ajoutée.")
                            st.rerun()
                        else:
                            st.warning(f"Le code '{sub_code.upper()}' existe déjà.")
                    else:
                        st.error("Remplissez le nom et le code.")

        with col_m2:
            st.markdown("#### Matières enregistrées")
            subjects_list = get_all_subjects()
            if subjects_list:
                df_sub = pd.DataFrame([{"Nom": s.name, "Code": s.code} for s in subjects_list])
                st.dataframe(df_sub, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune matière enregistrée. Ajoutez-en à gauche.")


# ============================================================
# TAB 7 — Suivi Intelligent des Présences
# ============================================================

def render_tab7(students, logs):
    st.header("✅ Suivi Intelligent des Présences")

    jour_actuel_index = datetime.now().weekday()
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    today = date.today()

    if jour_actuel_index >= 6:
        st.info("🌅 Aujourd'hui c'est Dimanche — aucun emploi du temps à analyser.")
        return

    jour_texte = jours_semaine[jour_actuel_index]
    logs_today = [l for l in logs if l["timestamp"].date() == today]

    st.write(f"**Journée analysée :** {jour_texte} — {today.strftime('%d/%m/%Y')}")

    # Heure actuelle pour savoir quels créneaux sont passés
    now_hour = datetime.now().hour
    now_min  = datetime.now().minute

    def creneau_passe(start_time: str) -> bool:
        h, m = map(int, start_time.split(":"))
        return (now_hour, now_min) > (h, m)

    # Récupérer tous les créneaux du jour
    slots_today = get_time_slots(day=jour_texte)

    suivi_data = []

    for s in students:
        s_logs = [l for l in logs_today if l.get("name") == s.get("name") or l.get("student_id") == s.get("student_id")]
        a_vu_cam = len(s_logs) > 0

        # ── ADMIN : règle automatique ────────────────────────
        if s.get("category") and s.get("category").lower() == "admin":
            if a_vu_cam and s.get("inside"):
                etat = "✅ Présent"
            elif a_vu_cam and not s.get("inside"):
                etat = "🟠 Est venu, reparti"
            else:
                etat = "🔴 Absent"
            suivi_data.append({
                "Nom": s.get("name"),
                "Catégorie": "Admin",
                "Classe / Rôle": s.get("grade") or "Admin",
                "Horaire Attendu": "08:00 - 15:00 (pause 12h-13h)",
                "Créneaux Couverts": "6/6",
                "Statut": etat
            })
            continue

        # ── PROF : vérifier ses créneaux du jour ────────────
        if s.get("category") and s.get("category").lower() == "prof":
            prof_slots = [sl for sl in slots_today if sl["prof_name"] == s.get("name")]
            if not prof_slots:
                suivi_data.append({
                    "Nom": s.get("name"),
                    "Catégorie": "Prof",
                    "Classe / Rôle": "—",
                    "Horaire Attendu": "Pas de cours",
                    "Créneaux Couverts": "0",
                    "Statut": "😴 Repos"
                })
                continue

            horaires = ", ".join(f"{sl['start_time']}-{sl['end_time']} ({sl['class_name']})" for sl in prof_slots)
            nb_slots  = len(prof_slots)
            nb_passe  = sum(1 for sl in prof_slots if creneau_passe(sl["start_time"]))

            if nb_passe == 0:
                etat = "⏳ Cours à venir"
            elif a_vu_cam and s.get("inside"):
                etat = "✅ Présent"
            elif a_vu_cam and not s.get("inside"):
                etat = "🟠 Est venu, reparti"
            else:
                etat = "🔴 Absent"

            suivi_data.append({
                "Nom": s.get("name"),
                "Catégorie": "Prof",
                "Classe / Rôle": ", ".join(set(sl["class_name"] for sl in prof_slots)),
                "Horaire Attendu": horaires,
                "Créneaux Couverts": f"{nb_passe}/{nb_slots}",
                "Statut": etat
            })
            continue

        # ── ÉLÈVE : vérifier si sa classe a cours ────────────
        if s.get("category") and s.get("category").lower() == "eleve":
            class_slots = [sl for sl in slots_today if sl["class_name"] == s.get("grade")]
            if not class_slots:
                suivi_data.append({
                    "Nom": s.get("name"),
                    "Catégorie": "Élève",
                    "Classe / Rôle": s.get("grade") or "—",
                    "Horaire Attendu": "Pas de cours",
                    "Créneaux Couverts": "0",
                    "Statut": "😴 Repos"
                })
                continue

            horaires  = f"{class_slots[0]['start_time']} → {class_slots[-1]['end_time']}"
            nb_slots  = len(class_slots)
            nb_passe  = sum(1 for sl in class_slots if creneau_passe(sl["start_time"]))

            if nb_passe == 0:
                etat = "⏳ Cours à venir"
            elif a_vu_cam and s.get("inside"):
                etat = "✅ Présent"
            elif a_vu_cam and not s.get("inside"):
                etat = "🟠 Est venu, reparti"
            else:
                etat = "🔴 Absent"

            suivi_data.append({
                "Nom": s.get("name"),
                "Catégorie": "Élève",
                "Classe / Rôle": s.get("grade"),
                "Horaire Attendu": horaires,
                "Créneaux Couverts": f"{nb_passe}/{nb_slots}",
                "Statut": etat
            })

    # ── Affichage ──────────────────────────────────────────
    if suivi_data:
        df = pd.DataFrame(suivi_data)

        # Métriques rapides
        c1, c2, c3, c4 = st.columns(4)
        total   = len(df)
        present = len(df[df["Statut"].str.contains("✅")])
        absent  = len(df[df["Statut"].str.contains("🔴")])
        repos   = len(df[df["Statut"].str.contains("😴|⏳")])

        c1.metric("Total personnes", total)
        c2.metric("✅ Présents", present)
        c3.metric("🔴 Absents", absent)
        c4.metric("😴 Repos / À venir", repos)

        st.markdown("---")

        # Filtres
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtre_cat = st.multiselect("Filtrer par catégorie",
                                        ["Admin", "Prof", "Élève"],
                                        default=["Admin", "Prof", "Élève"])
        with col_f2:
            filtre_etat = st.multiselect("Filtrer par statut",
                                         ["✅ Présent", "🔴 Absent", "🟠 Est venu, reparti", "😴 Repos", "⏳ Cours à venir"],
                                         default=["✅ Présent", "🔴 Absent", "🟠 Est venu, reparti", "😴 Repos", "⏳ Cours à venir"])

        df_filtered = df[df["Catégorie"].isin(filtre_cat) & df["Statut"].isin(filtre_etat)]

        def couleur_statut(val):
            if "✅" in val:   return "color: #4CAF50; font-weight: bold"
            if "🔴" in val:   return "color: #F44336; font-weight: bold"
            if "🟠" in val:   return "color: #FF9800; font-weight: bold"
            if "😴" in val:   return "color: #9E9E9E"
            if "⏳" in val:   return "color: #2196F3"
            return ""

        try:
            st.dataframe(
                df_filtered.style.map(couleur_statut, subset=["Statut"]),
                use_container_width=True, height=550, hide_index=True
            )
        except AttributeError:
            st.dataframe(
                df_filtered.style.applymap(couleur_statut, subset=["Statut"]),
                use_container_width=True, height=550, hide_index=True
            )
    else:
        st.info("Aucune donnée à afficher.")
