import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os

# Importation de vos scripts existants
from database1 import init_db
from enroll import enroll_student, enroll_from_folder

class PrintLogger:
    """ Redirige les print() vers l'interface graphique de façon sécurisée (Thread-Safe) """
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, text):
        self.textbox.after(0, self.append_text, text)

    def append_text(self, text):
        self.textbox.config(state=tk.NORMAL)
        self.textbox.insert(tk.END, text)
        self.textbox.see(tk.END)
        self.textbox.config(state=tk.DISABLED)

    def flush(self):
        pass

class EnrollmentDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Système d'Inscription - Dashboard")
        self.root.geometry("700x600")
        self.root.configure(padx=20, pady=20)
        
        # Initialisation BD
        init_db()

        # Styles
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 11))
        style.configure("TButton", font=("Arial", 10, "bold"), padding=5)

        # -- TITRE --
        title = ttk.Label(root, text="👤 Ajouter un Nouveau Membre", font=("Arial", 16, "bold"))
        title.pack(pady=(0, 20))

        # -- FORMULAIRE --
        frame_form = ttk.Frame(root)
        frame_form.pack(fill=tk.X, pady=10)

        ttk.Label(frame_form, text="Nom Complet :").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_name = ttk.Entry(frame_form, width=40, font=("Arial", 11))
        self.entry_name.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(frame_form, text="ID Étudiant :").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_id = ttk.Entry(frame_form, width=40, font=("Arial", 11))
        self.entry_id.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(frame_form, text="Classe / Grade :").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.entry_grade = ttk.Entry(frame_form, width=40, font=("Arial", 11))
        self.entry_grade.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(frame_form, text="Catégorie :").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.combo_category = ttk.Combobox(frame_form, values=["eleve", "prof", "admin"], state="readonly", width=38, font=("Arial", 11))
        self.combo_category.current(0)  # Ouvre avec "eleve" sélectionné par défaut
        self.combo_category.grid(row=3, column=1, padx=10, pady=5)

        # -- BOUTONS D'ACTION --
        frame_buttons = ttk.Frame(root)
        frame_buttons.pack(fill=tk.X, pady=20)

        self.btn_camera = tk.Button(frame_buttons, text="📸 Inscription Caméra (25 photos)", 
                                    bg="#007ACC", fg="white", font=("Arial", 11, "bold"), 
                                    command=self.run_camera_enroll)
        self.btn_camera.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.btn_folder = tk.Button(frame_buttons, text="📁 Importer depuis Dossier", 
                                    bg="#28A745", fg="white", font=("Arial", 11, "bold"), 
                                    command=self.run_folder_enroll)
        self.btn_folder.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # -- AFFICHAGE DES LOGS --
        ttk.Label(root, text="Logs du Système :", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        self.log_area = tk.Text(root, height=15, bg="#1E1E1E", fg="#00FF00", font=("Consolas", 10), state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)

        # Rediriger la sortie console vers la zone de texte
        sys.stdout = PrintLogger(self.log_area)
        sys.stderr = PrintLogger(self.log_area)

        print("[DASHBOARD] Prêt. Remplissez le formulaire et choisissez une méthode d'inscription.")

    def get_form_data(self):
        name = self.entry_name.get().strip().title()
        student_id = self.entry_id.get().strip()
        grade = self.entry_grade.get().strip()
        category = self.combo_category.get().strip()
        
        if not name or not student_id:
            messagebox.showwarning("Attention", "Le Nom et l'ID sont obligatoires !")
            return None
        return name, student_id, grade, category

    def run_folder_enroll(self):
        data = self.get_form_data()
        if not data: return
        name, student_id, grade, category = data

        # Ouvrir l'explorateur de fichiers pour sélectionner le dossier
        folder_path = filedialog.askdirectory(title="Sélectionner le dossier des photos")
        if not folder_path:
            return

        # Désactiver les boutons pendant le traitement
        self.btn_folder.config(state=tk.DISABLED)
        self.btn_camera.config(state=tk.DISABLED)

        # Lancer le traitement en arrière-plan pour ne pas geler l'interface
        def worker():
            print(f"\n--- DÉMARRAGE IMPORTATION POUR {name} ---")
            enroll_from_folder(name, student_id, grade, category, folder_path)
            self.btn_folder.config(state=tk.NORMAL)
            self.btn_camera.config(state=tk.NORMAL)
            messagebox.showinfo("Succès", f"Inscription de {name} terminée !")

        threading.Thread(target=worker, daemon=True).start()

    def run_camera_enroll(self):
        data = self.get_form_data()
        if not data: return
        name, student_id, grade, category = data

        self.btn_folder.config(state=tk.DISABLED)
        self.btn_camera.config(state=tk.DISABLED)

        def worker():
            print(f"\n--- DÉMARRAGE CAMÉRA POUR {name} ---")
            enroll_student(name, student_id, grade, category)
            self.btn_folder.config(state=tk.NORMAL)
            self.btn_camera.config(state=tk.NORMAL)
            messagebox.showinfo("Succès", f"Inscription de {name} par caméra terminée !")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = EnrollmentDashboard(root)
    root.mainloop()