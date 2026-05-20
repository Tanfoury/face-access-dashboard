import os
import shutil
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database1 import Student, AccessLog, Base
from face_db import load_vectors, save_vectors, build_index

def delete_person(name):
    # 1. Delete from SQLite database
    engine = create_engine("sqlite:///school_access.db")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    student = session.query(Student).filter(Student.name.ilike(name)).first()
    if student:
        session.delete(student)
        # Optionally, delete their access logs too
        session.query(AccessLog).filter(AccessLog.name.ilike(name)).delete()
        session.commit()
        print(f"[SQLite] '{name}' successfully deleted from database.")
    else:
        print(f"[SQLite] Person '{name}' not found in database.")
    
    session.close()

    # 2. Delete from FAISS face vectors (pkl)
    vectors = load_vectors()
    found_vector = False
    
    # Needs case-insensitive match
    for key in list(vectors.keys()):
        if key.lower() == name.lower():
            del vectors[key]
            found_vector = True
            
    if found_vector:
        save_vectors(vectors)
        build_index()
        print(f"[FAISS] Vector for '{name}' deleted from face_vectors.pkl.")
    else:
        print(f"[FAISS] No vector found for '{name}'.")

    # 3. Delete their photos folder
    students_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students_db")
    for folder in os.listdir(students_dir):
        if folder.lower() == name.lower():
            folder_path = os.path.join(students_dir, folder)
            if os.path.isdir(folder_path):
                shutil.rmtree(folder_path)
                print(f"[FILES] Photo directory '{folder_path}' deleted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a person from the database.")
    parser.add_argument("name", type=str, help="Name of the person to delete")
    args = parser.parse_args()
    
    delete_person(args.name)
