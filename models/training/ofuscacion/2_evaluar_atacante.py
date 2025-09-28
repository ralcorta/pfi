# evaluate_attacker_with_logs.py
import os, time
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from sklearn.metrics import classification_report, confusion_matrix

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

DATA_DIR = Path(".")
DETECTOR_PATH = DATA_DIR / "models/training/detection/convlstm_model.keras"
ATTACKER_PATH = DATA_DIR / "attacker_model.keras"

EPSILON = 0.05   # Debe coincidir con el usado en entrenamiento/evaluación
TARGET_CLASS = 0
BATCH = 256
PRINT_EVERY = 10

# -------------------------
# Carga de modelos y datos
# -------------------------
if not DETECTOR_PATH.exists():
    raise FileNotFoundError(f"No se encontró el detector en: {DETECTOR_PATH}")
if not ATTACKER_PATH.exists():
    raise FileNotFoundError(f"No se encontró el atacante en: {ATTACKER_PATH}")

detector = load_model(DETECTOR_PATH)
attacker = load_model(ATTACKER_PATH)

X_test = np.load(DATA_DIR / "X_test.npy", mmap_mode="r")
y_test = np.load(DATA_DIR / "y_test.npy")
n_total = X_test.shape[0]

# Features tabulares opcionales
Xf_test_path = DATA_DIR / "X_ransomware_test.npy"
HAS_FEATURES = Xf_test_path.exists()
Xf_test = np.load(Xf_test_path, mmap_mode="r") if HAS_FEATURES else None
if HAS_FEATURES:
    print(f"🧩 X_ransomware_test detectado: {Xf_test.shape}", flush=True)
else:
    print("ℹ️ Sin features tabulares en test — evaluación solo con payloads.", flush=True)

def build_input(x_payload, x_feats):
    """Devuelve input en el formato correcto para el detector."""
    return [x_payload, x_feats] if x_feats is not None else x_payload

def batched_predict(model, X_memmap, batch_size=256, Xf_memmap=None):
    """Predicción por lotes; soporta input único o dual (payload + features)."""
    out = []
    n = X_memmap.shape[0]
    for s in range(0, n, batch_size):
        e = min(s + batch_size, n)
        xb = X_memmap[s:e].astype(np.float32)
        if Xf_memmap is not None:
            xfb = Xf_memmap[s:e].astype(np.float32)
            out.append(model.predict([xb, xfb], verbose=0))
        else:
            out.append(model.predict(xb, verbose=0))
    return np.vstack(out)

# -------------------------
# Baseline
# -------------------------
print("=== Baseline ===", flush=True)
proba_base = batched_predict(detector, X_test, batch_size=BATCH, Xf_memmap=Xf_test if HAS_FEATURES else None)
y_true = np.argmax(y_test, axis=1)
y_pred_base = np.argmax(proba_base, axis=1)

# evaluate() también con input correcto
if HAS_FEATURES:
    loss_base, acc_base = detector.evaluate([X_test[:].astype(np.float32),
                                             Xf_test[:].astype(np.float32)], y_test, verbose=0)
else:
    loss_base, acc_base = detector.evaluate(X_test[:].astype(np.float32), y_test, verbose=0)

print(f"Loss: {loss_base:.4f} | Acc: {acc_base:.4f}", flush=True)

# -------------------------
# Generación de X_adv por bloques
# Guardamos:
# - X_adv
# - delta_actual = x_adv - x (post-clip)
# - delta_intent = eps * tanh(attacker(x))  (pre-clip, el que limita por ε)
#   (Las features NO se modifican)
# -------------------------
adv_path = DATA_DIR / "X_adv_eval_temp.npy"
delta_path = DATA_DIR / "delta_eval_temp.npy"
delta_intent_path = DATA_DIR / "delta_intent_eval_temp.npy"

X_adv_mm = np.lib.format.open_memmap(adv_path, mode="w+", dtype=np.float32, shape=X_test.shape)
delta_mm = np.lib.format.open_memmap(delta_path, mode="w+", dtype=np.float32, shape=X_test.shape)
delta_intent_mm = np.lib.format.open_memmap(delta_intent_path, mode="w+", dtype=np.float32, shape=X_test.shape)

print("\n=== Generando X_adv ===", flush=True)
for i, s in enumerate(range(0, n_total, BATCH), 1):
    e = min(s + BATCH, n_total)
    xb = X_test[s:e].astype(np.float32)
    xb_tf = tf.convert_to_tensor(xb, dtype=tf.float32)

    # salida lineal del atacante -> tanh -> escalado por ε (== entrenamiento del atacante)
    d_hat = attacker(xb_tf, training=False)
    delta_intent = EPSILON * tf.tanh(d_hat)             # en [-ε, +ε]
    x_adv = tf.clip_by_value(xb_tf + delta_intent, 0.0, 1.0)

    X_adv_mm[s:e] = x_adv.numpy()
    delta_mm[s:e] = (x_adv.numpy() - xb)                # delta_actual post-clip
    delta_intent_mm[s:e] = delta_intent.numpy()         # delta intencional (pre-clip)

    if i % PRINT_EVERY == 0 or e == n_total:
        print(f"  batch {i}: [{s}-{e}) {100*e/n_total:.2f}%", flush=True)

# Cerrar/volcar mmaps y mover a destino final
del X_adv_mm; del delta_mm; del delta_intent_mm
os.replace(adv_path, DATA_DIR / "X_adv_eval.npy")
os.replace(delta_path, DATA_DIR / "delta_eval.npy")
os.replace(delta_intent_path, DATA_DIR / "delta_intent_eval.npy")

X_adv = np.load(DATA_DIR / "X_adv_eval.npy", mmap_mode="r")
delta_all = np.load(DATA_DIR / "delta_eval.npy", mmap_mode="r")
delta_intent_all = np.load(DATA_DIR / "delta_intent_eval.npy", mmap_mode="r")

# -------------------------
# Evaluación del detector en X_adv
# -------------------------
print("\n=== Detector en X_adv ===", flush=True)
proba_adv = batched_predict(detector, X_adv, batch_size=BATCH, Xf_memmap=Xf_test if HAS_FEATURES else None)
y_pred_adv = np.argmax(proba_adv, axis=1)

if HAS_FEATURES:
    loss_adv, acc_adv = detector.evaluate([X_adv[:].astype(np.float32),
                                           Xf_test[:].astype(np.float32)], y_test, verbose=0)
else:
    loss_adv, acc_adv = detector.evaluate(X_adv[:].astype(np.float32), y_test, verbose=0)

print(f"Loss: {loss_adv:.4f} | Acc: {acc_adv:.4f}", flush=True)

# -------------------------
# Métricas
# -------------------------
MAL = (y_true == 1)
mal_count = int(MAL.sum())

# Éxito del ataque (targeted a Benigno) SOLO sobre muestras malware
asr = 100.0 * (y_pred_adv[MAL] == TARGET_CLASS).mean() if mal_count > 0 else 0.0
conf_target_mean = float(
    proba_adv[MAL, TARGET_CLASS][y_pred_adv[MAL] == TARGET_CLASS].mean()
) if mal_count > 0 and (y_pred_adv[MAL] == TARGET_CLASS).any() else 0.0

# Normas (delta_actual post-clip) — lo que realmente se aplicó a x
linf_actual_global = float(np.max(np.abs(delta_all)))
linf_actual_mean = float(np.mean(np.max(np.abs(delta_all).reshape(n_total, -1), axis=1)))
l1_mean = float(np.mean(np.mean(np.abs(delta_all).reshape(n_total, -1), axis=1)))
if delta_all.shape[1] > 1:
    tv_mean = float(np.mean(np.abs(delta_all[:, 1:, ...] - delta_all[:, :-1, ...])))
else:
    tv_mean = 0.0

# L∞ del delta intencional (pre-clip), que es el que debe respetar ε
linf_intent_global = float(np.max(np.abs(delta_intent_all)))
linf_intent_mean = float(np.mean(np.max(np.abs(delta_intent_all).reshape(n_total, -1), axis=1)))

print("\n===== BASELINE =====", flush=True)
print(f"Accuracy: {acc_base:.4f}")
print("Reporte:\n", classification_report(y_true, y_pred_base, target_names=["Benigno","Malware"], zero_division=0), flush=True)
print("CM:\n", confusion_matrix(y_true, y_pred_base, labels=[0, 1]), flush=True)

print("\n===== ADVERSARIAL =====", flush=True)
print(f"Accuracy: {acc_adv:.4f}")
print("Reporte:\n", classification_report(y_true, y_pred_adv, target_names=["Benigno","Malware"], zero_division=0), flush=True)
print("CM:\n", confusion_matrix(y_true, y_pred_adv, labels=[0, 1]), flush=True)

print("\n===== EFECTIVIDAD =====", flush=True)
print(f"Muestras malware: {mal_count}", flush=True)
print(f"ASR: {asr:.2f}% | Conf(Benigno | éxitos): {conf_target_mean:.4f}", flush=True)

print("\n===== STEALTH =====", flush=True)
print(f"L∞ INTENT global (pre-clip): {linf_intent_global:.6f} (ε={EPSILON}) | L∞ INTENT promedio: {linf_intent_mean:.6f}", flush=True)
print(f"L∞ ACTUAL global (post-clip): {linf_actual_global:.6f} | L∞ ACTUAL promedio: {linf_actual_mean:.6f}", flush=True)
print(f"L1 promedio (post-clip): {l1_mean:.8f} | TV temporal (post-clip): {tv_mean:.8f}", flush=True)

# Checks
ok_asr = asr >= 40.0
ok_drop = (acc_adv <= acc_base - 0.10)
ok_linf = linf_intent_global <= EPSILON + 1e-6  # chequeo sobre delta_intent (lo que debe respetar ε)

print("\n===== CHECK =====", flush=True)
print(f"ASR>=40%? {'SI' if ok_asr else 'NO'}", flush=True)
print(f"Accuracy cae ≥10pp? {'SI' if ok_drop else 'NO'}", flush=True)
print(f"Respeta ε (INTENT)? {'SI' if ok_linf else 'NO'}", flush=True)
