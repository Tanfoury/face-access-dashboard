# -*- coding: utf-8 -*-
# anti_spoof.py
import cv2
import time
import math
import numpy as np
import sys
import os

# --- OPENCV BLINK DETECTION (100% COMPATIBLE RASPBERRY PI - NO MEDIAPIPE NEEDED) ---
# Utilisation du modèle en cascade de base fourni avec OpenCV (Très Rapide !)
cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'

if not os.path.exists(cascade_path):
    cascade_path = '/usr/share/opencv4/haarcascades/haarcascade_eye.xml'

eye_cascade = cv2.CascadeClassifier(cascade_path)
if eye_cascade.empty():
    print("[SPOOF] ALERTE CRITIQUE : Le fichier HaarCascade pour les yeux est introuvable !")

BLINK_TIME_THRESH = 6.0     # On vous donne 6 secondes pour un test plus large
POSITION_TOLERANCE = 80
EYE_LOST_FRAMES_REQ = 1     # Sensibilité extrême : un seul frame d'absence = Clignement !


_face_info = {}
# Structure: { face_key: {"blinked": False, "start_time": time.time(), "eyes_lost_count": 0, "has_seen_eyes": False} }

def check_real_face(frame, bbox):
    """
    Vérifie si l'utilisateur cligne des yeux (Blink Detection) via OpenCV Haar Cascades
    100% natif, fonctionne sur tout Raspberry Pi (32-bit ou 64-bit) hyper rapidement !
    """
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    key_x = (center_x // POSITION_TOLERANCE) * POSITION_TOLERANCE
    key_y = (center_y // POSITION_TOLERANCE) * POSITION_TOLERANCE
    face_key = (key_x, key_y)
    now = time.time()

    if face_key not in _face_info:
        _face_info[face_key] = {
            'blinked': False, 
            'start_time': now, 
            'eyes_lost_count': 0, 
            'has_seen_eyes': False
        }
    info = _face_info[face_key]

    if info['blinked']:
        return True, 1.0

    # On se concentre uniquement sur la moitié haute du visage (là où il y a les yeux)
    w, h = x2 - x1, y2 - y1
    y_crop_mid = y1 + int(h * 0.6)  # 60% du visage en partant du haut
    
    face_roi_eyes = frame[y1:y_crop_mid, x1:x2]
    if face_roi_eyes.size == 0: 
        return False, 0.0

    # Convertir en noir et blanc pour augmenter drastiquement la vitesse + contraste (Equalize)
    gray_roi = cv2.cvtColor(face_roi_eyes, cv2.COLOR_BGR2GRAY)
    gray_roi = cv2.equalizeHist(gray_roi)
    
    # Chercher les yeux dans la ROI
    eyes = eye_cascade.detectMultiScale(
        gray_roi, 
        scaleFactor=1.1, 
        minNeighbors=3, 
        minSize=(15, 15)
    )

    # LOGIQUE DU CLIGNEMENT :
    # 1. On doit d'abord VOIR les yeux (has_seen_eyes = True)
    # 2. Ensuite, si on ne voit PLUS les yeux brièvement (eyes_lost_count monte)
    # 3. Alors c'est un clignement !
    
    if len(eyes) >= 1:
        # Au moins un oeil repéré ! La personne a les yeux ouverts
        if not info['has_seen_eyes']:
            info['has_seen_eyes'] = True
        
        # S'il avait disparu juste une fraction de seconde avant de revenir, c'était un clignement validé !
        if info['eyes_lost_count'] >= EYE_LOST_FRAMES_REQ:
            info['blinked'] = True
            return True, 1.0
            
        # Il a les yeux ouverts de façon stable, on reset le compteur de "fermeture"
        info['eyes_lost_count'] = 0
            
    else:
        # Aucun oeil détecté !! (Les yeux sont fermés... ou la personne regarde trop bas)
        if info['has_seen_eyes']:
            info['eyes_lost_count'] += 1
            if info['eyes_lost_count'] >= EYE_LOST_FRAMES_REQ:
                # Oeil perdu suffisamment longtemps = Clignement !!
                info['blinked'] = True
                return True, 1.0


    # Timeout : N'a jamais cligné pendant X secondes
    if now - info['start_time'] > BLINK_TIME_THRESH:
        return False, 0.0  # FAKE (Une photo fixe aura toujours "les yeux ouverts" selon OpenCV)

    # En attente d'un clignement
    return False, 0.5
