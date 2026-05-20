import sys

filepath = 'C:/Users/tanfo/OneDrive/Bureau/rasp/tabs_emploi_du_temps.py'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('    with sub1:')
end = text.find('    with sub2:')

if start == -1 or end == -1:
    print("Could not find blocks")
    sys.exit(1)

new_sub1 = """    with sub1:
        st.subheader("Planifier l'emploi du temps")
        
        mode_planification = st.radio("Planifier par :", ["Par Classe", "Par Professeur"], horizontal=True)

        if mode_planification == "Par Classe":
            st.info("Sélectionnez une classe, puis assignez un professeur et une matière pour chaque créneau horaire.")
            target_class = st.selectbox("Sélectionnez la Classe", classes) if classes else st.text_input("Classe (ex: 6A)")
            target_prof = None
        else:
            st.info("Sélectionnez un professeur, puis assignez une classe et une matière pour chaque créneau horaire.")
            target_class = None
            target_prof = st.selectbox("Sélectionnez le Professeur", profs) if profs else st.text_input("Nom du professeur")

        if (mode_planification == "Par Classe" and target_class) or (mode_planification == "Par Professeur" and target_prof):
            # Construction des options pour la grille
            if mode_planification == "Par Classe":
                # Choix = Prof | Matière
                options = ["---"]
                if profs and subject_map:
                    for p in profs:
                        for m in subject_map.keys():
                            options.append(f"{p} | {m}")
            else:
                # Choix = Classe | Matière
                options = ["---"]
                if classes and subject_map:
                    for c in classes:
                        for m in subject_map.keys():
                            options.append(f"{c} | {m}")

            if not options or len(options) == 1:
                st.warning("⚠️ Il manque des professeurs/classes ou des matières dans la BD pour générer les choix.")
            
            existing_slots = get_time_slots(class_name=target_class, prof_name=target_prof)
            # Dictionnaire pour retrouver plus vite
            slot_dict = {(s["day"], s["start_time"]): s for s in existing_slots}

            df_data = []
            for s, e in CRENEAUX:
                row = {"Horaire": f"{s} - {e}"}
                for d in JOURS:
                    slot = slot_dict.get((d, s))
                    if slot:
                        if mode_planification == "Par Classe":
                            row[d] = f"{slot['prof_name']} | {slot['subject_name']}" if slot.get('subject_name') else f"{slot['prof_name']} | ?"
                        else:
                            row[d] = f"{slot['class_name']} | {slot['subject_name']}" if slot.get('subject_name') else f"{slot['class_name']} | ?"
                    else:
                        row[d] = "---"
                df_data.append(row)
            
            df = pd.DataFrame(df_data)

            column_config = {
                "Horaire": st.column_config.TextColumn("Horaire", disabled=True),
            }
            # Pour éviter que la grille plante avant que les options soient toutes valides (ex. données non nettoyées ?)
            for d in JOURS:
                column_config[d] = st.column_config.SelectboxColumn(d, options=options, required=True, default="---")

            with st.form("form_calendar_schedule", clear_on_submit=False):
                st.markdown("#### Calendrier - Cliquez sur une case pour choisir")
                edited_df = st.data_editor(df, column_config=column_config, use_container_width=True, hide_index=True)
                
                submitted = st.form_submit_button("💾 Sauvegarder la grille", use_container_width=True)
                if submitted:
                    errors = []
                    # Sauvegarder
                    for i, row in edited_df.iterrows():
                        horaire = row["Horaire"]
                        s, e = horaire.split(" - ")
                        for d in JOURS:
                            val = row[d]
                            old_slot = slot_dict.get((d, s))
                            if val and val != "---" and " | " in val:
                                part1, part2 = val.split(" | ", 1)
                                
                                if mode_planification == "Par Classe":
                                    p_name = part1
                                    c_name = target_class
                                    s_name = part2
                                else:
                                    p_name = target_prof
                                    c_name = part1
                                    s_name = part2
                                    
                                subject_id = subject_map.get(s_name)
                                _, err = save_time_slot(d, s, e, c_name, p_name, subject_id)
                                if err: errors.append(err)
                            else:
                                # "---" -> supprimer si existant
                                if old_slot:
                                    delete_time_slot(old_slot["id"])
                    
                    if errors:
                        st.error("Certains conflits : " + ", ".join(errors))
                    else:
                        if mode_planification == "Par Classe":
                            st.success(f"✅ Emploi du temps mis à jour pour la classe {target_class}.")
                        else:
                            st.success(f"✅ Emploi du temps mis à jour pour le prof {target_prof}.")
                        st.rerun()

        st.markdown("---")
        st.markdown("**Pause automatique :** 🕒 12:00 - 13:00 (tout le monde)")

"""

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text[:start] + new_sub1 + text[end:])
print("Patch applied")