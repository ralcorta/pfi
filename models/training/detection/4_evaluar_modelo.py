import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tensorflow.keras.models import load_model
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_curve, auc,
    precision_recall_curve, average_precision_score
)
import joblib
import json
from datetime import datetime
from pathlib import Path

# ───────────────────────────────────────────────
# 1) Cargar modelo y datos
# ───────────────────────────────────────────────
print("🔍 Cargando modelo y datos de evaluación...")

ROOT = Path(__file__).parent
model = load_model(ROOT / 'convlstm_model.keras')

X_test = np.load(ROOT / 'X_test.npy')
y_test = np.load(ROOT / 'y_test.npy')

# Autodetección de features tabulares
feat_path = ROOT / 'X_ransomware_test.npy'
USE_FEATURES = feat_path.exists()
X_ransomware_test = np.load(feat_path) if USE_FEATURES else None

print("📊 Datos de test cargados:")
print(f"  - X_test: {X_test.shape}")
print(f"  - y_test: {y_test.shape}")
print(f"  - X_ransomware_test: {X_ransomware_test.shape if USE_FEATURES else '— (no encontrado)'}")

# Helper para armar input según corresponda
def build_input(X, Xfeat, use_features):
    return [X, Xfeat] if use_features else X

# ───────────────────────────────────────────────
# 2) Evaluación básica del modelo
# ───────────────────────────────────────────────
print("\n🎯 Evaluando modelo...")
loss, accuracy = model.evaluate(
    build_input(X_test, X_ransomware_test, USE_FEATURES),
    y_test,
    verbose=0
)
print("📈 Métricas básicas:")
print(f"  - Loss: {loss:.4f}")
print(f"  - Accuracy: {accuracy:.4f}")

# ───────────────────────────────────────────────
# 3) Predicciones detalladas
# ───────────────────────────────────────────────
print("\n🔮 Generando predicciones...")
y_pred_proba = model.predict(build_input(X_test, X_ransomware_test, USE_FEATURES), verbose=0)
y_pred = np.argmax(y_pred_proba, axis=1)
y_true = np.argmax(y_test, axis=1)

# ───────────────────────────────────────────────
# 4) Métricas específicas para ransomware
# ───────────────────────────────────────────────
print("\n🎯 Métricas específicas para ransomware:")
print("=" * 50)
class_names = ["Benigno", "Ransomware/Malware"]

report = classification_report(
    y_true, y_pred,
    target_names=class_names,
    output_dict=True,
    zero_division=0
)
print(classification_report(y_true, y_pred, target_names=class_names, zero_division=0))

ransomware_metrics = {
    'precision': report['Ransomware/Malware']['precision'],
    'recall': report['Ransomware/Malware']['recall'],
    'f1_score': report['Ransomware/Malware']['f1-score'],
    'support': int(report['Ransomware/Malware']['support'])
}
print("\n🎯 Métricas específicas para Ransomware/Malware:")
print(f"  - Precision: {ransomware_metrics['precision']:.4f}")
print(f"  - Recall: {ransomware_metrics['recall']:.4f}")
print(f"  - F1-Score: {ransomware_metrics['f1_score']:.4f}")
print(f"  - Support: {ransomware_metrics['support']}")

# ───────────────────────────────────────────────
# 5) Matriz de confusión + métricas adicionales
# ───────────────────────────────────────────────
print("\n📊 Generando matriz de confusión...")
cm = confusion_matrix(y_true, y_pred, labels=[0,1])
if cm.shape == (2,2):
    tn, fp, fn, tp = cm.ravel()
else:
    # Resguardo por si falta alguna clase en test
    tn = int(cm[0,0]) if cm.shape[0] > 0 and cm.shape[1] > 0 else 0
    fp = int(cm[0,1]) if cm.shape[0] > 0 and cm.shape[1] > 1 else 0
    fn = int(cm[1,0]) if cm.shape[0] > 1 and cm.shape[1] > 0 else 0
    tp = int(cm[1,1]) if cm.shape[0] > 1 and cm.shape[1] > 1 else 0

specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0

print("\n📈 Métricas adicionales:")
print(f"  - True Positives (TP): {tp}")
print(f"  - True Negatives (TN): {tn}")
print(f"  - False Positives (FP): {fp}")
print(f"  - False Negatives (FN): {fn}")
print(f"  - Sensitivity (Recall): {sensitivity:.4f}")
print(f"  - Specificity: {specificity:.4f}")

# ───────────────────────────────────────────────
# 6) Curvas ROC y Precision-Recall
# ───────────────────────────────────────────────
print("\n📈 Generando curvas de evaluación...")
fpr, tpr, _ = roc_curve(y_true, y_pred_proba[:, 1])
roc_auc = auc(fpr, tpr)

precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_pred_proba[:, 1])
avg_precision = average_precision_score(y_true, y_pred_proba[:, 1])

print(f"  - ROC AUC: {roc_auc:.4f}")
print(f"  - Average Precision: {avg_precision:.4f}")

# (Opcional) si querés plots, descomentá:
# plt.figure(); plt.plot(fpr, tpr); plt.xlabel("FPR"); plt.ylabel("TPR"); plt.title(f"ROC AUC={roc_auc:.3f}"); plt.show()
# plt.figure(); plt.plot(recall_curve, precision_curve); plt.xlabel("Recall"); plt.ylabel("Precision"); plt.title(f"PR AUC={avg_precision:.3f}"); plt.show()

# ───────────────────────────────────────────────
# 7) Nombres de features (si existen)
# ───────────────────────────────────────────────
print("\n🔍 Analizando nombres de features de ransomware...")
feature_names = []
try:
    with open(ROOT / 'ransomware_feature_names.txt', 'r') as f:
        feature_names = [line.strip() for line in f.readlines()]
        print(f"📋 Features analizadas ({len(feature_names)}):")
        for i, name in enumerate(feature_names):
            print(f"  {i+1:2d}. {name}")
except FileNotFoundError:
    print("⚠️ No se encontró ransomware_feature_names.txt (continuo sin nombres)")

# ───────────────────────────────────────────────
# 8) Guardar resultados
# ───────────────────────────────────────────────
print("\n💾 Guardando resultados...")

results = {
    'timestamp': datetime.now().isoformat(),
    'used_features': USE_FEATURES,
    'model_name': 'convlstm_model.keras',
    'basic_metrics': {'loss': float(loss), 'accuracy': float(accuracy)},
    'ransomware_specific_metrics': ransomware_metrics,
    'confusion_matrix': {
        'true_positives': int(tp),
        'true_negatives': int(tn),
        'false_positives': int(fp),
        'false_negatives': int(fn),
        'sensitivity': float(sensitivity),
        'specificity': float(specificity)
    },
    'roc_auc': float(roc_auc),
    'average_precision': float(avg_precision),
    'classification_report': report,
    'feature_names': feature_names
}

with open(ROOT.parent / 'evaluation_results.json', 'w') as f:
    json.dump(results, f, indent=2)

np.save(ROOT.parent / 'y_pred_proba.npy', y_pred_proba)
np.save(ROOT.parent / 'y_pred.npy', y_pred)

print("✅ Resultados guardados:")
print("  - evaluation_results.json")
print("  - y_pred_proba.npy")
print("  - y_pred.npy")

# ───────────────────────────────────────────────
# 9) Resumen final
# ───────────────────────────────────────────────
print("\n" + "="*60)
print("🎯 RESUMEN DE EVALUACIÓN - DETECTOR DE RANSOMWARE")
print("="*60)
print(f"📊 Accuracy General: {accuracy:.4f}")
print(f"🎯 Precision Ransomware: {ransomware_metrics['precision']:.4f}")
print(f"🎯 Recall Ransomware: {ransomware_metrics['recall']:.4f}")
print(f"🎯 F1-Score Ransomware: {ransomware_metrics['f1_score']:.4f}")
print(f"📈 ROC AUC: {roc_auc:.4f}")
print(f"📈 Average Precision: {avg_precision:.4f}")
print(f"🔍 Detección de Ransomware: {tp}/{tp+fn} ({sensitivity:.1%})")
print(f"🛡️ Especificidad: {specificity:.1%}")
print("="*60)

if ransomware_metrics['f1_score'] > 0.8:
    print("✅ EXCELENTE: Modelo con alta capacidad de detección de ransomware")
elif ransomware_metrics['f1_score'] > 0.7:
    print("✅ BUENO: Modelo con buena capacidad de detección de ransomware")
elif ransomware_metrics['f1_score'] > 0.6:
    print("⚠️ REGULAR: Modelo con capacidad moderada de detección de ransomware")
else:
    print("❌ NECESITA MEJORAS: Modelo con baja capacidad de detección de ransomware")
