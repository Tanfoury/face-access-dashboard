#!/bin/bash
# install_service.sh
# Lance ce script UNE SEULE FOIS pour installer le démarrage automatique
# Usage : sudo bash install_service.sh

set -e

SERVICE_NAME="face_access"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR="/home/pi/Desktop/rasp"

echo "======================================"
echo " Installation du service : $SERVICE_NAME"
echo "======================================"

# 1. Vérifier que le projet existe
if [ ! -f "$PROJECT_DIR/main.py" ]; then
    echo "[ERREUR] $PROJECT_DIR/main.py introuvable."
    echo "         Vérifie que le projet est bien dans $PROJECT_DIR"
    exit 1
fi

# 2. Copier le fichier service
echo "[1/4] Copie du fichier service..."
cp face_access.service "$SERVICE_FILE"

# 3. Recharger systemd
echo "[2/4] Rechargement de systemd..."
systemctl daemon-reload

# 4. Activer le service (démarre au boot)
echo "[3/4] Activation au démarrage..."
systemctl enable "$SERVICE_NAME"

# 5. Démarrer maintenant
echo "[4/4] Démarrage du service..."
systemctl start "$SERVICE_NAME"

echo ""
echo "======================================"
echo " Service installé avec succès !"
echo "======================================"
echo ""
echo "Commandes utiles :"
echo "  sudo systemctl status $SERVICE_NAME     -> état du service"
echo "  sudo systemctl stop $SERVICE_NAME       -> arrêter"
echo "  sudo systemctl restart $SERVICE_NAME    -> redémarrer"
echo "  sudo systemctl disable $SERVICE_NAME    -> désactiver au boot"
echo "  journalctl -u $SERVICE_NAME -f          -> voir les logs en direct"
echo ""
