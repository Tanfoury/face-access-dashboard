import os
import shutil
from face_db import enroll_face
from database1 import add_student

def enroll_from_single_photo(name, image_path, student_id="9999", grade="Test"):
    # 1. Vérifier que la photo existe
    if not os.path.exists(image_path):
        print(f"❌ Erreur : La photo '{image_path}' est introuvable !")
        return

    # 2. Créer le dossier pour l'IA dans students_db
    folder_name = name.replace(" ", "_").lower()
    folder_path = os.path.join("students_db", folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # 3. Copier la photo unique dans le dossier de l'élève
    dest_path = os.path.join(folder_path, "photo_unique.jpg")
    shutil.copy2(image_path, dest_path)
    print(f"✅ Photo copiée dans : {dest_path}")

    # 4. Inscrire la photo dans la mémoire de l'IA (le fichier .pkl)
    print(f"⏳ Création de l'empreinte faciale pour {name}...")
    success = enroll_face(name, folder_path)
    
    if success:
        # 5. Ajouter l'étudiant dans la base de données SQLite
        add_student(
            name=name, 
            student_id=student_id, 
            grade=grade, 
            photo_dir=folder_path, 
            category="eleve"
        )
        print(f"🎉 SUCCÈS ! L'élève '{name}' est maintenant enregistré dans le système !")
    else:
        print("❌ Échec : Aucun visage détecté sur cette photo. Essayez une autre photo.")

if __name__ == "__main__":
    print("=== SCRIPT D'INSCRIPTION RAPIDE (1 PHOTO) ===")
    
    nom = input("👉 Entrez le prénom/nom de la personne : ")
    matricule = input("👉 Entrez son matricule (ex: 1234) : ")
    photo_path = input("👉 Entrez le nom du fichier image (ex: photo1.jpg) : ")
    
    print("\n-------------------------------------------")
    enroll_from_single_photo(nom, photo_path, student_id=matricule)
