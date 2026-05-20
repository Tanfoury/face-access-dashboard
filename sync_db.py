import os
from config import BASE_DIR
from face_db import enroll_face

def sync_all_students():
    print("=== DÉMARRAGE DE LA SYNCHRONISATION ===")
    students_dir = os.path.join(BASE_DIR, "students_db")
    
    if not os.path.exists(students_dir):
        print(f"Erreur : Le dossier {students_dir} n'existe pas.")
        return

    count_success = 0
    count_fail = 0

    # Parcourir tous les dossiers dans students_db
    for item in os.listdir(students_dir):
        item_path = os.path.join(students_dir, item)
        
        # Ignorer les fichiers (comme les .pkl ou .db)
        if os.path.isdir(item_path):
            print(f"\n-> Enrôlement de l'étudiant : '{item}'")
            success = enroll_face(item, item_path)
            
            if success:
                count_success += 1
            else:
                count_fail += 1

    print("\n=== RÉSUMÉ DE LA SYNCHRONISATION ===")
    print(f"Étudiants synchronisés avec succès : {count_success}")
    print(f"Échecs (pas de visages détectés, etc.) : {count_fail}")
    print("La base de données faciale (face_vectors.pkl) est à jour !")

if __name__ == "__main__":
    sync_all_students()
