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
        st.info("Sélectionnez une classe et un professeur. Vous pouvez ensuite modifier la grille ci-dessous et assigner des matières.")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            classe = st.selectbox("Classe", classes) if classes else st.text_input("Classe (ex: 6A)")
        with col_f2:
            prof = st.selectbox("Professeur", profs) if profs else st.text_input("Nom du professeur")

        if classe and prof:
            matiere_options = ["---"] + list(subject_map.keys())
            
            existing_slots = get_time_slots(class_name=classe, prof_name=prof)
            # Dictionnaire pour retrouver plus vite
            slot_dict = {(s["day"], s["start_time"]): s for s in existing_slots}

            df_data = []
            for s, e in CRENEAUX:
                row = {"Horaire": f"{s} - {e}"}
                for d in JOURS:
                    slot = slot_dict.get((d, s))
                    row[d] = slot["subject_name"] if (slot and slot["subject_name"]) else "---"
                df_data.append(row)
            
            df = pd.DataFrame(df_data)

            column_config = {
                "Horaire": st.column_config.TextColumn("Horaire", disabled=True),
            }
            for d in JOURS:
                column_config[d] = st.column_config.SelectboxColumn(d, options=matiere_options, required=True, default="---")

            with st.form("form_calendar_schedule", clear_on_submit=False):
                st.markdown("#### Calendrier - Cliquez sur les cases pour choisir la matière")
                edited_df = st.data_editor(df, column_config=column_config, use_container_width=True, hide_index=True)
                
                submitted = st.form_submit_button("💾 Sauvegarder la grille", use_container_width=True)
                if submitted:
                    errors = []
                    # Sauvegarder
                    for i, row in edited_df.iterrows():
                        horaire = row["Horaire"]
                        s, e = horaire.split(" - ")
                        for d in JOURS:
                            mat = row[d]
                            old_slot = slot_dict.get((d, s))
                            if mat != "---":
                                subject_id = subject_map.get(mat)
                                _, err = save_time_slot(d, s, e, classe, prof, subject_id)
                                if err: errors.append(err)
                            else:
                                if old_slot:
                                    delete_time_slot(old_slot["id"])
                    
                    if errors:
                        st.error("Certains conflits : " + ", ".join(errors))
                    else:
                        st.success(f"✅ Emploi du temps mis à jour pour la classe {classe} et le prof {prof}.")
                        st.rerun()

        st.markdown("---")
        st.markdown("**Pause automatique :** 🕒 12:00 - 13:00 (tout le monde)")

"""

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text[:start] + new_sub1 + text[end:])
print("Patch applied")