#!/usr/bin/env python3
"""Synchronise les dossiers de `students_db/` avec la table `students` de Supabase.

Usage: python3 sync_missing_students.py
"""
import os
import uuid
from pathlib import Path

from database import init_db, get_student_by_name, add_student


def normalize_candidates(folder_name: str):
    # Génère quelques variantes de nom à tester dans la table Supabase
    variants = [folder_name, folder_name.replace("_", " ")]
    variants.append(folder_name.title())
    variants.append(folder_name.capitalize())
    # Dédupliquer en conservant l'ordre
    seen = set()
    out = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def main():
    init_db()
    base = Path(__file__).parent / "students_db"
    if not base.exists():
        print(f"Erreur: dossier students_db introuvable: {base}")
        return

    folders = [p.name for p in base.iterdir() if p.is_dir()]
    if not folders:
        print("Aucun dossier d'élève trouvé dans students_db/")
        return

    created = 0
    for fname in sorted(folders):
        candidates = normalize_candidates(fname)
        exists = False
        for name in candidates:
            try:
                if get_student_by_name(name):
                    exists = True
                    break
            except Exception:
                # Ne pas bloquer la synchronisation sur une erreur réseau
                pass

        if exists:
            print(f"[SKIP] {fname} déjà présent dans Supabase")
            continue

        # Ajouter une entrée minimale
        sid = str(uuid.uuid4())
        chosen_name = candidates[0]
        try:
            add_student(sid, chosen_name, grade="", category="eleve")
            print(f"[SUPABASE] ajouté {chosen_name} id={sid}")
            created += 1
        except Exception as e:
            print(f"[ERROR] impossible d'ajouter {chosen_name}: {e}")

    print(f"Terminé. {created} nouvel(le)(s) inscrit(s) ajouté(s) dans Supabase.")


if __name__ == "__main__":
    main()
