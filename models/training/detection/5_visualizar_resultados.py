#!/usr/bin/env python3
"""
Script para visualizar los resultados del modelo de detección de ransomware
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, roc_curve, auc, precision_recall_curve
import pandas as pd
from pathlib import Path

# ───────────────────────────────────────────────
# 1. Cargar datos
# ───────────────────────────────────────────────
print("📊 Cargando datos para visualización...")

# Obtener el directorio del script
script_dir = Path(__file__).parent
training_dir = script_dir.parent

# Cargar resultados de evaluación
with open(training_dir / 'evaluation_results.json', 'r') as f:
    results = json.load(f)

# Cargar predicciones
y_pred_proba = np.load(training_dir / 'y_pred_proba.npy')
y_pred = np.load(training_dir / 'y_pred.npy')
y_test = np.load(script_dir / 'y_test.npy')
y_true = np.argmax(y_test, axis=1)

# ───────────────────────────────────────────────
# 2. Configurar estilo de gráficos
# ───────────────────────────────────────────────
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
fig = plt.figure(figsize=(20, 15))

# ───────────────────────────────────────────────
# 3. Matriz de confusión (valores absolutos)
# ───────────────────────────────────────────────
plt.subplot(2, 3, 1)

# Usar los datos del JSON
tn = results['confusion_matrix']['true_negatives']
fp = results['confusion_matrix']['false_positives']
fn = results['confusion_matrix']['false_negatives']
tp = results['confusion_matrix']['true_positives']

# Crear matriz de confusión con el orden correcto
cm = np.array([[tn, fp], [fn, tp]])

# Crear heatmap con mejor formato
sns.heatmap(cm, fmt='d', cmap='Blues', 
            xticklabels=['Benigno', 'Ransomware'], 
            yticklabels=['Benigno', 'Ransomware'],
            cbar_kws={'label': 'Número de muestras'},
            linewidths=0.5, linecolor='white')

# Agregar texto adicional para claridad
plt.text(0.5, 0.5, f'TN\n{tn:,}', ha='center', va='center', fontsize=12, fontweight='bold')
plt.text(1.5, 0.5, f'FP\n{fp:,}', ha='center', va='center', fontsize=12, fontweight='bold')
plt.text(0.5, 1.5, f'FN\n{fn:,}', ha='center', va='center', fontsize=12, fontweight='bold')
plt.text(1.5, 1.5, f'TP\n{tp:,}', ha='center', va='center', fontsize=12, fontweight='bold')

plt.title('Matriz de Confusión\nDetector de Ransomware', fontsize=14, fontweight='bold')
plt.ylabel('Etiqueta Real')
plt.xlabel('Predicción')

# Agregar información adicional
print(f"📊 Matriz de Confusión:")
print(f"   Verdaderos Negativos (TN): {tn:,}")
print(f"   Falsos Positivos (FP): {fp:,}")
print(f"   Falsos Negativos (FN): {fn:,}")
print(f"   Verdaderos Positivos (TP): {tp:,}")

# ───────────────────────────────────────────────
# 4. Curva ROC
# ───────────────────────────────────────────────
plt.subplot(2, 3, 2)
fpr, tpr, _ = roc_curve(y_true, y_pred_proba[:, 1])
roc_auc = auc(fpr, tpr)

plt.plot(fpr, tpr, color='darkorange', lw=2, 
         label=f'ROC Curve (AUC = {roc_auc:.3f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('Tasa de Falsos Positivos')
plt.ylabel('Tasa de Verdaderos Positivos')
plt.title('Curva ROC\nDetección de Ransomware', fontsize=14, fontweight='bold')
plt.legend(loc="lower right")

# ───────────────────────────────────────────────
# 5. Curva Precision-Recall
# ───────────────────────────────────────────────
plt.subplot(2, 3, 3)
precision, recall, _ = precision_recall_curve(y_true, y_pred_proba[:, 1])
avg_precision = results['average_precision']

plt.plot(recall, precision, color='red', lw=2,
         label=f'PR Curve (AP = {avg_precision:.3f})')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Curva Precision-Recall\nDetección de Ransomware', fontsize=14, fontweight='bold')
plt.legend(loc="lower left")

# ───────────────────────────────────────────────
# 6. Distribución de probabilidades
# ───────────────────────────────────────────────
plt.subplot(2, 3, 4)
benign_probs = y_pred_proba[y_true == 0, 1]
ransomware_probs = y_pred_proba[y_true == 1, 1]

plt.hist(benign_probs, bins=30, alpha=0.7, label='Benigno', color='green')
plt.hist(ransomware_probs, bins=30, alpha=0.7, label='Ransomware', color='red')
plt.axvline(x=0.5, color='black', linestyle='--', label='Umbral (0.5)')
plt.xlabel('Probabilidad de Ransomware')
plt.ylabel('Frecuencia')
plt.title('Distribución de Probabilidades\npor Clase', fontsize=14, fontweight='bold')
plt.legend()

# ───────────────────────────────────────────────
# 3.1. Matriz de confusión normalizada
# ───────────────────────────────────────────────
plt.subplot(2, 3, 4)

# Normalizar la matriz
cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

# Crear heatmap normalizado
sns.heatmap(cm_normalized, annot=True, fmt='.3f', cmap='Greens', 
            xticklabels=['Benigno', 'Ransomware'], 
            yticklabels=['Benigno', 'Ransomware'],
            cbar_kws={'label': 'Proporción'},
            linewidths=0.5, linecolor='white')

plt.title('Matriz de Confusión Normalizada\n(Proporciones por fila)', fontsize=14, fontweight='bold')
plt.ylabel('Etiqueta Real')
plt.xlabel('Predicción')

# ───────────────────────────────────────────────
# 7. Métricas por clase
# ───────────────────────────────────────────────
plt.subplot(2, 3, 5)
metrics_data = {
    'Clase': ['Benigno', 'Ransomware'],
    'Precision': [
        results['classification_report']['Benigno']['precision'],
        results['classification_report']['Ransomware/Malware']['precision']
    ],
    'Recall': [
        results['classification_report']['Benigno']['recall'],
        results['classification_report']['Ransomware/Malware']['recall']
    ],
    'F1-Score': [
        results['classification_report']['Benigno']['f1-score'],
        results['classification_report']['Ransomware/Malware']['f1-score']
    ]
}

df_metrics = pd.DataFrame(metrics_data)
x = np.arange(len(df_metrics))
width = 0.25

plt.bar(x - width, df_metrics['Precision'], width, label='Precision', alpha=0.8)
plt.bar(x, df_metrics['Recall'], width, label='Recall', alpha=0.8)
plt.bar(x + width, df_metrics['F1-Score'], width, label='F1-Score', alpha=0.8)

plt.xlabel('Clase')
plt.ylabel('Score')
plt.title('Métricas por Clase\nDetector de Ransomware', fontsize=14, fontweight='bold')
plt.xticks(x, df_metrics['Clase'])
plt.legend()
plt.ylim(0, 1)

# ───────────────────────────────────────────────
# 8. Resumen de métricas principales
# ───────────────────────────────────────────────
plt.subplot(2, 3, 6)
plt.axis('off')

# Crear texto con métricas principales
metrics_text = f"""
🎯 MÉTRICAS PRINCIPALES

📊 Accuracy: {results['basic_metrics']['accuracy']:.4f}
🎯 Precision Ransomware: {results['ransomware_specific_metrics']['precision']:.4f}
🎯 Recall Ransomware: {results['ransomware_specific_metrics']['recall']:.4f}
🎯 F1-Score Ransomware: {results['ransomware_specific_metrics']['f1_score']:.4f}

📈 ROC AUC: {results['roc_auc']:.4f}
📈 Average Precision: {results['average_precision']:.4f}

🔍 Detección: {results['confusion_matrix']['sensitivity']:.1%}
🛡️ Especificidad: {results['confusion_matrix']['specificity']:.1%}

📋 Muestras de Test: {len(y_true)}
✅ Verdaderos Positivos: {results['confusion_matrix']['true_positives']}
❌ Falsos Positivos: {results['confusion_matrix']['false_positives']}
❌ Falsos Negativos: {results['confusion_matrix']['false_negatives']}
✅ Verdaderos Negativos: {results['confusion_matrix']['true_negatives']}
"""

plt.text(0.1, 0.9, metrics_text, transform=plt.gca().transAxes, 
         fontsize=12, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))

plt.title('Resumen de Evaluación\nDetector de Ransomware', fontsize=14, fontweight='bold')

# ───────────────────────────────────────────────
# 9. Guardar visualizaciones
# ───────────────────────────────────────────────
print(" Guardando visualizaciones...")

# Guardar como PNG
plt.savefig(training_dir / 'evaluation_visualization.png', 
            dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ PNG guardado: {training_dir / 'evaluation_visualization.png'}")

# Guardar como PDF
plt.savefig(training_dir / 'evaluation_visualization.pdf', 
            bbox_inches='tight', facecolor='white')
print(f"✅ PDF guardado: {training_dir / 'evaluation_visualization.pdf'}")

# Mostrar el gráfico
plt.show()

print("🎉 Visualización completada exitosamente!")

# ───────────────────────────────────────────────
# 10. Análisis de features de ransomware
# ───────────────────────────────────────────────
if 'feature_names' in results and len(results['feature_names']) > 0:
    print(f"\n🔍 Features de ransomware analizadas ({len(results['feature_names'])}):")
    for i, feature in enumerate(results['feature_names'], 1):
        print(f"  {i:2d}. {feature}")

# ───────────────────────────────────────────────
# 11. Recomendaciones basadas en resultados
# ───────────────────────────────────────────────
# print("\n" + "="*60)
# print("💡 RECOMENDACIONES BASADAS EN LOS RESULTADOS")
# print("="*60)

# f1_score = results['ransomware_specific_metrics']['f1_score']
# precision = results['ransomware_specific_metrics']['precision']
# recall = results['ransomware_specific_metrics']['recall']

# if f1_score > 0.8:
#     print("✅ EXCELENTE rendimiento del modelo")
#     print("   - El modelo está listo para producción")
#     print("   - Considera implementar en tiempo real")
# elif f1_score > 0.7:
#     print("✅ BUENO rendimiento del modelo")
#     print("   - El modelo es funcional para detección")
#     print("   - Considera fine-tuning adicional")
# elif f1_score > 0.6:
#     print("⚠️ RENDIMIENTO MODERADO")
#     print("   - Considera más datos de entrenamiento")
#     print("   - Revisa el balance de clases")
# else:
#     print("❌ RENDIMIENTO BAJO")
#     print("   - Necesita más datos de ransomware")
#     print("   - Considera arquitectura diferente")

# if precision < 0.7:
#     print("⚠️ Alta tasa de falsos positivos")
#     print("   - Considera ajustar el umbral de decisión")
#     print("   - Revisa features que puedan causar confusión")

# if recall < 0.7:
#     print("⚠️ Alta tasa de falsos negativos")
#     print("   - Necesita más ejemplos de ransomware")
#     print("   - Considera data augmentation")

print("="*60)
