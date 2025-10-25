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

# ───────────────────────────────────────────────
# 1. Cargar modelo y datos
# ───────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # Ajustar según la profundidad

print("🔍 Cargando modelo y datos de evaluación...")

# Cargar modelo
model = load_model(PROJECT_ROOT / 'models' / 'training' / 'detection' / 'convlstm_model.keras')

# Cargar datos de test
X_test = np.load(PROJECT_ROOT / 'models' / 'training' / 'detection' / 'X_test.npy')
y_test = np.load(PROJECT_ROOT / 'models' / 'training' / 'detection' / 'y_test.npy')
# X_ransomware_test = np.load('X_ransomware_test.npy')  # Comentar esta línea

print(f"📊 Datos de test cargados:")
print(f"  - X_test: {X_test.shape}")
print(f"  - y_test: {y_test.shape}")
# print(f"  - X_ransomware_test: {X_ransomware_test.shape}")  # Comentar esta línea

# ───────────────────────────────────────────────
# 2. Evaluación básica del modelo
# ───────────────────────────────────────────────
print("\n🎯 Evaluando modelo...")
loss, accuracy = model.evaluate(
    X_test, y_test, verbose=0  # Solo usar X_test, no [X_test, X_ransomware_test]
)

print(f"📈 Métricas básicas:")
print(f"  - Loss: {loss:.4f}")
print(f"  - Accuracy: {accuracy:.4f}")

# ───────────────────────────────────────────────
# 3. Predicciones detalladas
# ───────────────────────────────────────────────
print("\n🔮 Generando predicciones...")
y_pred_proba = model.predict(X_test)  # Solo usar X_test
y_pred = np.argmax(y_pred_proba, axis=1)
y_true = np.argmax(y_test, axis=1)

# ───────────────────────────────────────────────
# 4. Métricas específicas para ransomware
# ───────────────────────────────────────────────
print("\n🎯 Métricas específicas para ransomware:")
print("=" * 50)

# Reporte de clasificación detallado
class_names = ["Benigno", "Ransomware/Malware"]
report = classification_report(
    y_true, y_pred, 
    target_names=class_names,
    output_dict=True
)

print(classification_report(y_true, y_pred, target_names=class_names))

# Métricas específicas para ransomware (clase 1)
ransomware_metrics = {
    'precision': report['Ransomware/Malware']['precision'],
    'recall': report['Ransomware/Malware']['recall'],
    'f1_score': report['Ransomware/Malware']['f1-score'],
    'support': report['Ransomware/Malware']['support']
}

print(f"\n🎯 Métricas específicas para Ransomware/Malware:")
print(f"  - Precision: {ransomware_metrics['precision']:.4f}")
print(f"  - Recall: {ransomware_metrics['recall']:.4f}")
print(f"  - F1-Score: {ransomware_metrics['f1_score']:.4f}")
print(f"  - Support: {ransomware_metrics['support']}")

# ───────────────────────────────────────────────
# 5. Matriz de confusión
# ───────────────────────────────────────────────
print("\n📊 Generando matriz de confusión...")
cm = confusion_matrix(y_true, y_pred)

# Calcular métricas adicionales
tn, fp, fn, tp = cm.ravel()
specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0

print(f"\n📈 Métricas adicionales:")
print(f"  - True Positives (TP): {tp}")
print(f"  - True Negatives (TN): {tn}")
print(f"  - False Positives (FP): {fp}")
print(f"  - False Negatives (FN): {fn}")
print(f"  - Sensitivity (Recall): {sensitivity:.4f}")
print(f"  - Specificity: {specificity:.4f}")

# ───────────────────────────────────────────────
# 6. Curvas ROC y Precision-Recall
# ───────────────────────────────────────────────
print("\n📈 Generando curvas de evaluación...")

# ROC Curve
fpr, tpr, _ = roc_curve(y_true, y_pred_proba[:, 1])
roc_auc = auc(fpr, tpr)

# Precision-Recall Curve
precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_pred_proba[:, 1])
avg_precision = average_precision_score(y_true, y_pred_proba[:, 1])

print(f"  - ROC AUC: {roc_auc:.4f}")
print(f"  - Average Precision: {avg_precision:.4f}")

# ───────────────────────────────────────────────
# 7. Análisis de features de ransomware
# ───────────────────────────────────────────────
print("\n🔍 Analizando importancia de features de ransomware...")

# Cargar nombres de features
try:
    with open(PROJECT_ROOT / 'models' / 'training' / 'detection' / 'ransomware_feature_names.txt', 'r') as f:
        feature_names = [line.strip() for line in f.readlines()]
    
    print(f"📋 Features analizadas ({len(feature_names)}):")
    for i, name in enumerate(feature_names):
        print(f"  {i+1:2d}. {name}")
        
except FileNotFoundError:
    print("⚠️ No se encontró el archivo de nombres de features")
    # feature_names = [f"feature_{i}" for i in range(X_ransomware_test.shape[1])]  # Comentar esta línea
    feature_names = []  # Lista vacía ya que no usamos estas features

# ───────────────────────────────────────────────
# 8. Guardar resultados
# ───────────────────────────────────────────────
print("\n💾 Guardando resultados...")

# Crear diccionario con todas las métricas
results = {
    'timestamp': datetime.now().isoformat(),
    'model_name': 'convlstm_model.keras',
    'basic_metrics': {
        'loss': float(loss),
        'accuracy': float(accuracy)
    },
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

# Guardar resultados en JSON
with open(PROJECT_ROOT / 'models' / 'training' / 'evaluation_results.json', 'w') as f:
    json.dump(results, f, indent=2)

# Guardar predicciones
np.save(PROJECT_ROOT / 'models' / 'training' / 'y_pred_proba.npy', y_pred_proba)
np.save(PROJECT_ROOT / 'models' / 'training' / 'y_pred.npy', y_pred)

print("✅ Resultados guardados:")
print(f"  - evaluation_results.json: Métricas completas")
print(f"  - y_pred_proba.npy: Probabilidades de predicción")
print(f"  - y_pred.npy: Predicciones finales")

# ───────────────────────────────────────────────
# 9. Resumen final
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