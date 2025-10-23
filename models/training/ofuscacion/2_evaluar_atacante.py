#!/usr/bin/env python3
# evaluate_attacker_with_logs.py  ← evidencia completa (JSON + figuras + NPY)

import os, json, time
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# ─────────────────────────────────────────────────────────────────────────────
# Utils de rutas/figuras
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent

def resolve_here_first(p: Path) -> Path:
    if p.is_absolute() and p.exists(): return p
    if p.exists(): return p
    alt = SCRIPT_DIR / p.name
    return alt if alt.exists() else p

def _savefig(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    print(f"   ↳ Figura guardada: {path}")

# ─────────────────────────────────────────────────────────────────────────────
# Parámetros (pueden modificarse rápido aquí o con CLI si querés)
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR      = resolve_here_first(Path("."))  # carpeta de trabajo
DETECTOR_PATH = resolve_here_first(Path("models/training/detection/convlstm_model_best.keras"))
if not DETECTOR_PATH.exists():
    # fallback al final si no existe el "best"
    DETECTOR_PATH = resolve_here_first(Path("models/training/detection/convlstm_model.keras"))

ATTACKER_PATH = resolve_here_first(Path("attacker_model.keras"))

# Debe coincidir con el usado al entrenar el atacante
EPSILON      = 0.05
TARGET_CLASS = 0
BATCH        = 256
PRINT_EVERY  = 10

OUTDIR = SCRIPT_DIR  # podés cambiarlo si querés otro destino

# ─────────────────────────────────────────────────────────────────────────────
# Carga de modelos y datos
# ─────────────────────────────────────────────────────────────────────────────
if not DETECTOR_PATH.exists():
    raise FileNotFoundError(f"No se encontró el detector en: {DETECTOR_PATH}")
if not ATTACKER_PATH.exists():
    raise FileNotFoundError(f"No se encontró el atacante en: {ATTACKER_PATH}")

detector = load_model(DETECTOR_PATH)
attacker = load_model(ATTACKER_PATH)

X_test = np.load(resolve_here_first(Path("X_test.npy")), mmap_mode="r")
y_test = np.load(resolve_here_first(Path("y_test.npy")))
y_true = np.argmax(y_test, axis=1)
n_total = X_test.shape[0]

def batched_predict(model, memmap, batch_size=256):
    out = []
    for s in range(0, memmap.shape[0], batch_size):
        e = min(s + batch_size, memmap.shape[0])
        out.append(model.predict(memmap[s:e].astype(np.float32), verbose=0))
    return np.vstack(out)

# ─────────────────────────────────────────────────────────────────────────────
# Baseline
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== BASELINE (detector sobre X_test) ===")
proba_base = batched_predict(detector, X_test, BATCH)
y_pred_base = np.argmax(proba_base, axis=1)
loss_base, acc_base = detector.evaluate(X_test[:].astype(np.float32), y_test, verbose=0)
print(f"Loss: {loss_base:.4f} | Acc: {acc_base:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# Generación de X_adv por bloques (guardamos X_adv y deltas)
# ─────────────────────────────────────────────────────────────────────────────
adv_path_tmp         = OUTDIR / "X_adv_eval_temp.npy"
delta_path_tmp       = OUTDIR / "delta_eval_temp.npy"
delta_intent_path_tmp= OUTDIR / "delta_intent_eval_temp.npy"

X_adv_mm        = np.lib.format.open_memmap(adv_path_tmp, mode="w+", dtype=np.float32, shape=X_test.shape)
delta_mm        = np.lib.format.open_memmap(delta_path_tmp, mode="w+", dtype=np.float32, shape=X_test.shape)
delta_intent_mm = np.lib.format.open_memmap(delta_intent_path_tmp, mode="w+", dtype=np.float32, shape=X_test.shape)

print("\n=== Generando X_adv (usando atacante) ===")
for i, s in enumerate(range(0, n_total, BATCH), 1):
    e  = min(s + BATCH, n_total)
    xb = X_test[s:e].astype(np.float32)
    xb_tf = tf.convert_to_tensor(xb, dtype=tf.float32)

    d_hat = attacker(xb_tf, training=False)         # salida lineal
    delta_intent = EPSILON * tf.tanh(d_hat)         # en [-ε, +ε] (igual que train)
    x_adv = tf.clip_by_value(xb_tf + delta_intent, 0.0, 1.0)

    X_adv_mm[s:e]        = x_adv.numpy()
    delta_mm[s:e]        = (x_adv.numpy() - xb)          # delta post-clip
    delta_intent_mm[s:e] = delta_intent.numpy()          # delta intencional (pre-clip)

    if i % PRINT_EVERY == 0 or e == n_total:
        print(f"  batch {i}: [{s}-{e}) {100*e/n_total:.2f}%")

del X_adv_mm, delta_mm, delta_intent_mm
os.replace(adv_path_tmp,          OUTDIR / "X_adv_eval.npy")
os.replace(delta_path_tmp,        OUTDIR / "delta_eval.npy")
os.replace(delta_intent_path_tmp, OUTDIR / "delta_intent_eval.npy")

X_adv            = np.load(OUTDIR / "X_adv_eval.npy", mmap_mode="r")
delta_all        = np.load(OUTDIR / "delta_eval.npy", mmap_mode="r")
delta_intent_all = np.load(OUTDIR / "delta_intent_eval.npy", mmap_mode="r")

# ─────────────────────────────────────────────────────────────────────────────
# Detector en X_adv
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== DETECTOR en X_adv ===")
proba_adv  = batched_predict(detector, X_adv, BATCH)
y_pred_adv = np.argmax(proba_adv, axis=1)
loss_adv, acc_adv = detector.evaluate(X_adv[:].astype(np.float32), y_test, verbose=0)
print(f"Loss: {loss_adv:.4f} | Acc: {acc_adv:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# Métricas de efectividad y stealth
# ─────────────────────────────────────────────────────────────────────────────
MAL = (y_true == 1)
mal_count = int(MAL.sum())

asr = 100.0 * (y_pred_adv[MAL] == TARGET_CLASS).mean() if mal_count > 0 else 0.0
conf_target_mean = float(
    proba_adv[MAL, TARGET_CLASS][y_pred_adv[MAL] == TARGET_CLASS].mean()
) if mal_count > 0 and (y_pred_adv[MAL] == TARGET_CLASS).any() else 0.0

linf_actual_global = float(np.max(np.abs(delta_all)))
linf_actual_mean   = float(np.mean(np.max(np.abs(delta_all).reshape(n_total, -1), axis=1)))
l1_mean            = float(np.mean(np.mean(np.abs(delta_all).reshape(n_total, -1), axis=1)))
if delta_all.shape[1] > 1:
    tv_mean = float(np.mean(np.abs(delta_all[:, 1:, ...] - delta_all[:, :-1, ...])))
else:
    tv_mean = 0.0

linf_intent_global = float(np.max(np.abs(delta_intent_all)))
linf_intent_mean   = float(np.mean(np.max(np.abs(delta_intent_all).reshape(n_total, -1), axis=1)))

# ─────────────────────────────────────────────────────────────────────────────
# Figuras: CM baseline/adv, barras de accuracy, histograma Linf por muestra
# ─────────────────────────────────────────────────────────────────────────────
class_names = ["Benigno", "Malware"]

# Baseline CM
cm_base = confusion_matrix(y_true, y_pred_base, labels=[0,1])
plt.figure()
sns.heatmap(cm_base, annot=True, fmt='d', cmap='Blues',
            xticklabels=class_names, yticklabels=class_names)
plt.xlabel("Predicho"); plt.ylabel("Real"); plt.title("CM – Baseline")
_savefig(OUTDIR / "fig_cm_baseline_attack.png")

# Adv CM
cm_adv = confusion_matrix(y_true, y_pred_adv, labels=[0,1])
plt.figure()
sns.heatmap(cm_adv, annot=True, fmt='d', cmap='Oranges',
            xticklabels=class_names, yticklabels=class_names)
plt.xlabel("Predicho"); plt.ylabel("Real"); plt.title("CM – Adversarial")
_savefig(OUTDIR / "fig_cm_adversarial_attack.png")

# Barras: accuracy baseline vs adv
plt.figure()
plt.bar(["Baseline","Adversarial"], [acc_base, acc_adv])
plt.ylim(0,1); plt.ylabel("Accuracy"); plt.title("Accuracy del detector")
_savefig(OUTDIR / "fig_acc_base_vs_adv.png")

# Histograma L∞ ACTUAL por muestra
linf_per_sample = np.max(np.abs(delta_all).reshape(n_total, -1), axis=1)
plt.figure()
plt.hist(linf_per_sample, bins=40)
plt.axvline(EPSILON, color='r', linestyle='--', label=f'ε={EPSILON}')
plt.legend()
plt.xlabel("‖δ‖∞ por muestra (post-clip)"); plt.ylabel("Frecuencia")
plt.title("Distribución de ‖δ‖∞ (post-clip)")
_savefig(OUTDIR / "fig_hist_linf_postclip.png")

# ─────────────────────────────────────────────────────────────────────────────
# JSON de evidencia
# ─────────────────────────────────────────────────────────────────────────────
results = {
    "timestamp": datetime.now().isoformat(),
    "detector_model": DETECTOR_PATH.name,
    "attacker_model": ATTACKER_PATH.name,
    "epsilon": float(EPSILON),
    "target_class": int(TARGET_CLASS),
    "baseline": {
        "loss": float(loss_base),
        "accuracy": float(acc_base),
        "classification_report": classification_report(
            y_true, y_pred_base, target_names=class_names, output_dict=True, zero_division=0),
        "confusion_matrix": cm_base.tolist()
    },
    "adversarial": {
        "loss": float(loss_adv),
        "accuracy": float(acc_adv),
        "classification_report": classification_report(
            y_true, y_pred_adv, target_names=class_names, output_dict=True, zero_division=0),
        "confusion_matrix": cm_adv.tolist()
    },
    "effectiveness": {
        "malware_samples": mal_count,
        "ASR_targeted_to_benign_pct": float(asr),
        "benign_confidence_mean_on_success": float(conf_target_mean)
    },
    "stealth": {
        "linf_intent_global": float(linf_intent_global),
        "linf_intent_mean": float(linf_intent_mean),
        "linf_actual_global": float(linf_actual_global),
        "linf_actual_mean": float(linf_actual_mean),
        "l1_mean_postclip": float(l1_mean),
        "tv_temporal_postclip": float(tv_mean)
    }
}

json_path = OUTDIR / "evaluation_results_attack.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n✅ Guardado JSON: {json_path}")

# NPY auxiliares (útiles para reproducibilidad/evidencia)
np.save(OUTDIR / "y_true_attack.npy", y_true)
np.save(OUTDIR / "y_pred_base_attack.npy", y_pred_base)
np.save(OUTDIR / "y_pred_adv_attack.npy",  y_pred_adv)
print("✅ Guardado: y_true_attack.npy, y_pred_base_attack.npy, y_pred_adv_attack.npy")

print("\n===== RESUMEN =====")
print(f"Baseline Acc: {acc_base:.4f} | Adversarial Acc: {acc_adv:.4f}")
print(f"ASR targeted→Benigno (solo malware): {asr:.2f}%")
print(f"‖δ‖∞ INTENT (global): {linf_intent_global:.6f}  (ε={EPSILON})")
print(f"‖δ‖∞ ACTUAL (global): {linf_actual_global:.6f}")
print("Figuras: fig_cm_baseline_attack.png, fig_cm_adversarial_attack.png, fig_acc_base_vs_adv.png, fig_hist_linf_postclip.png")
