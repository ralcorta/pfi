# 4_evaluar_modelo.py  ← PASO 4 (versión robusta con resolución de rutas + figuras)
import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tensorflow.keras.models import load_model
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_curve, auc,
    precision_recall_curve, average_precision_score
)

# ───────────────────────────────────────────────
# Utilidades
# ───────────────────────────────────────────────
def _savefig(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    print(f"   ↳ Figura guardada: {path.name}")

def _print_headline(text):
    print("\n" + "="*70)
    print(text)
    print("="*70)

def resolve_here_first(p: Path, script_dir: Path) -> Path:
    """
    Si p es absoluto y existe → p.
    Si p relativo existe respecto del CWD → p.
    Si no, prueba en la carpeta del script: script_dir / p.name.
    Devuelve el primero que exista; si ninguno existe, devuelve p tal cual.
    """
    if p.is_absolute() and p.exists():
        return p
    if p.exists():
        return p
    alt = script_dir / p.name
    if alt.exists():
        return alt
    return p  # se validará más abajo

# ───────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Evaluación de modelo detector de ransomware")
parser.add_argument("--model",  default="convlstm_model.keras", help="Ruta al modelo .keras")
parser.add_argument("--x",      default="X_test.npy",           help="Ruta a X de evaluación")
parser.add_argument("--y",      default="y_test.npy",           help="Ruta a y (one-hot)")
parser.add_argument("--tag",    default="base",                 help="Etiqueta para sufijos (base/attack/advtrain)")
parser.add_argument("--outdir", default=".",                    help="Directorio de salida para JSON/figuras/NPY")
args = parser.parse_args()

# ───────────────────────────────────────────────
# 1) Resolver rutas de forma robusta
# ───────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
out_dir = Path(args.outdir)
tag = args.tag

# Candidatos de modelo: primero el explícito, luego best, luego final en la carpeta del script
candidate_models = [
    Path(args.model),
    SCRIPT_DIR / "convlstm_model_best.keras",
    SCRIPT_DIR / "convlstm_model.keras",
]

model_path = None
for cand in candidate_models:
    cand_res = resolve_here_first(cand, SCRIPT_DIR)
    if cand_res.exists():
        model_path = cand_res
        break

if model_path is None:
    tried = ", ".join(str(resolve_here_first(c, SCRIPT_DIR)) for c in candidate_models)
    raise FileNotFoundError(f"No encontré un modelo .keras. Probé: {tried}")

x_path = resolve_here_first(Path(args.x), SCRIPT_DIR)
y_path = resolve_here_first(Path(args.y), SCRIPT_DIR)

if not x_path.exists() or not y_path.exists():
    raise FileNotFoundError(f"Faltan archivos de eval: {x_path} / {y_path}")

# ───────────────────────────────────────────────
# 2) Cargar modelo y datos
# ───────────────────────────────────────────────
_print_headline("🔍 Cargando modelo y datos de evaluación")
print(f"  - Modelo: {model_path}")
print(f"  - X_eval: {x_path}")
print(f"  - y_eval: {y_path}")

model = load_model(model_path)
X_eval = np.load(x_path)
y_eval = np.load(y_path)

print(f"  - X_eval shape: {X_eval.shape}")
print(f"  - y_eval shape: {y_eval.shape}")

# ───────────────────────────────────────────────
# 3) Evaluación básica
# ───────────────────────────────────────────────
_print_headline("🎯 Evaluando modelo")
loss, accuracy = model.evaluate(X_eval, y_eval, verbose=0)
print(f"  - Loss: {loss:.4f}")
print(f"  - Accuracy: {accuracy:.4f}")

# ───────────────────────────────────────────────
# 4) Predicciones y métricas
# ───────────────────────────────────────────────
print("\n🔮 Generando predicciones...")
y_pred_proba = model.predict(X_eval, verbose=0)          # (N, 2)
y_pred = np.argmax(y_pred_proba, axis=1)                 # (N,)
y_true = np.argmax(y_eval, axis=1)                       # (N,)

print("\n📊 Reporte de clasificación")
class_names = ["Benigno", "Ransomware/Malware"]
report = classification_report(y_true, y_pred, target_names=class_names, output_dict=True)
print(classification_report(y_true, y_pred, target_names=class_names))

# Métricas específicas para clase malware (1)
ransomware_metrics = {
    "precision": report["Ransomware/Malware"]["precision"],
    "recall":    report["Ransomware/Malware"]["recall"],
    "f1_score":  report["Ransomware/Malware"]["f1-score"],
    "support":   int(report["Ransomware/Malware"]["support"])
}

# Matriz de confusión + derivadas
cm = confusion_matrix(y_true, y_pred)
tn, fp, fn, tp = cm.ravel()
specificity = tn / (tn + fp) if (tn + fp) else 0.0
sensitivity = tp / (tp + fn) if (tp + fn) else 0.0

print("\n📈 Métricas adicionales")
print(f"  - TP={tp}  TN={tn}  FP={fp}  FN={fn}")
print(f"  - Sensitivity/Recall: {sensitivity:.4f}")
print(f"  - Specificity:        {specificity:.4f}")

# ───────────────────────────────────────────────
# 5) Curvas ROC y Precision–Recall
# ───────────────────────────────────────────────
print("\n📈 Curvas ROC y Precision–Recall")
fpr, tpr, _ = roc_curve(y_true, y_pred_proba[:, 1])
roc_auc = auc(fpr, tpr)

prec_curve, rec_curve, _ = precision_recall_curve(y_true, y_pred_proba[:, 1])
avg_precision = average_precision_score(y_true, y_pred_proba[:, 1])

print(f"  - ROC AUC:          {roc_auc:.4f}")
print(f"  - Average Precision {avg_precision:.4f}")

# ───────────────────────────────────────────────
# 6) Figuras: Confusion matrix, ROC, PR
# ───────────────────────────────────────────────
print("\n🖼️ Generando figuras...")
out_dir.mkdir(parents=True, exist_ok=True)

# Matriz de confusión
plt.figure()
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=class_names, yticklabels=class_names)
plt.xlabel('Predicho'); plt.ylabel('Real'); plt.title(f'Matriz de confusión ({tag})')
_savefig(out_dir / f'fig_confusion_matrix_{tag}.png')

# ROC
plt.figure()
plt.plot(fpr, tpr, label=f'AUC={roc_auc:.3f}')
plt.plot([0,1], [0,1], '--')
plt.xlabel('FPR'); plt.ylabel('TPR'); plt.title(f'ROC ({tag})'); plt.legend()
_savefig(out_dir / f'fig_roc_{tag}.png')

# Precision–Recall
plt.figure()
plt.plot(rec_curve, prec_curve, label=f'AP={avg_precision:.3f}')
plt.xlabel('Recall'); plt.ylabel('Precision'); plt.title(f'Precision–Recall ({tag})'); plt.legend()
_savefig(out_dir / f'fig_pr_{tag}.png')

# ───────────────────────────────────────────────
# 7) (Opcional) nombres de features
# ───────────────────────────────────────────────
feature_names = []
feat_names_path = resolve_here_first(Path('ransomware_feature_names.txt'), SCRIPT_DIR)
if feat_names_path.exists():
    try:
        with open(feat_names_path, 'r', encoding='utf-8') as f:
            feature_names = [line.strip() for line in f if line.strip()]
        print(f"\n🔍 Nombres de features ({len(feature_names)}):")
        for i, name in enumerate(feature_names[:10]):
            print(f"  {i+1:2d}. {name}")
        if len(feature_names) > 10:
            print(f"  ... (+{len(feature_names)-10} más)")
    except Exception as e:
        print(f"[WARN] No pude leer {feat_names_path.name}: {e}")
else:
    print("\n[INFO] No se encontró ransomware_feature_names.txt (ok si no usaste esas features).")

# ───────────────────────────────────────────────
# 8) Guardar resultados y predicciones
# ───────────────────────────────────────────────
print("\n💾 Guardando artefactos de evaluación...")

results = {
    "timestamp": datetime.now().isoformat(),
    "tag": tag,
    "model_name": model_path.name,
    "basic_metrics": {
        "loss": float(loss),
        "accuracy": float(accuracy)
    },
    "ransomware_specific_metrics": ransomware_metrics,
    "confusion_matrix": {
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity)
    },
    "roc_auc": float(roc_auc),
    "average_precision": float(avg_precision),
    "classification_report": report,
    "feature_names": feature_names
}

out_json = out_dir / f"evaluation_results_{tag}.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

np.save(out_dir / f"y_pred_proba_{tag}.npy", y_pred_proba)
np.save(out_dir / f"y_pred_{tag}.npy", y_pred)
np.save(out_dir / f"y_true_{tag}.npy", y_true)

print("✅ Guardado:")
print(f"  - {out_json.name}")
print(f"  - y_pred_proba_{tag}.npy")
print(f"  - y_pred_{tag}.npy")
print(f"  - y_true_{tag}.npy")
print(f"  - fig_confusion_matrix_{tag}.png")
print(f"  - fig_roc_{tag}.png")
print(f"  - fig_pr_{tag}.png")

# ───────────────────────────────────────────────
# 9) Resumen final
# ───────────────────────────────────────────────
_print_headline("🎯 RESUMEN DE EVALUACIÓN – DETECTOR DE RANSOMWARE")
print(f"Accuracy (global):           {accuracy:.4f}")
print(f"Precision (Malware):         {ransomware_metrics['precision']:.4f}")
print(f"Recall/Sensitivity (Malware):{ransomware_metrics['recall']:.4f}")
print(f"F1-Score (Malware):          {ransomware_metrics['f1_score']:.4f}")
print(f"ROC AUC:                     {roc_auc:.4f}")
print(f"Average Precision (PR AUC):  {avg_precision:.4f}")
print(f"TP/TN/FP/FN:                 {tp}/{tn}/{fp}/{fn}")
print(f"Specificity:                 {specificity:.4f}")
print("="*70)

# Semáforo rápido por F1 (Malware)
f1 = ransomware_metrics['f1_score']
if f1 > 0.8:
    print("✅ EXCELENTE: Alta capacidad de detección de ransomware")
elif f1 > 0.7:
    print("✅ BUENO: Buena capacidad de detección de ransomware")
elif f1 > 0.6:
    print("⚠️ REGULAR: Capacidad moderada de detección")
else:
    print("❌ MEJORABLE: Capacidad baja; revisar datos/arquitectura/umbral")