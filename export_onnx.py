import sys
import os
import torch

# Chemins pour Silent-Face
sys.path.insert(0, "Silent-Face-Anti-Spoofing-master")
sys.path.insert(0, os.path.join("Silent-Face-Anti-Spoofing-master", "src"))
from src.anti_spoof_predict import AntiSpoofPredict

print("Chargement du modèle PyTorch...")
app = AntiSpoofPredict(0) # CPU
model_path = "Silent-Face-Anti-Spoofing-master/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth"
app._load_model(model_path)
app.model.eval()

print("Conversion en cours (ONNX)...")
# Le format d'image est 1 image, 3 canaux (RGB), 80x80 pixels
dummy_input = torch.randn(1, 3, 80, 80).to(app.device)

torch.onnx.export(
    app.model, 
    dummy_input, 
    "anti_spoof.onnx", 
    opset_version=11, 
    input_names=['input'], 
    output_names=['output']
)

print("SUCCÈS ! Le fichier 'anti_spoof.onnx' vient d'être créé.")