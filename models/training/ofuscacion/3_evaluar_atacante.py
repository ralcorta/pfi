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

EPSILON = 0.05   # igual que en generación
TARGET_CLASS = 0
BATCH = 256
PRINT_EVERY = 10

detector = load_model(DETECTOR_PATH)
attacker = load_model(ATTACKER_PATH)

X_test = np.load(DATA_DIR / "X_test.npy", mmap_mode="r")
y_test = np.load(DATA_DIR / "y_test.npy")
n_total = X_test.shape[0]

def batched_predict(model, memmap, batch_size=256):
    out = []
    for s in range(0, memmap.shape[0], batch_size):
        e = min(s+batch_size, memmap.shape[0])
        out.append(model.predict(memmap[s:e].astype(np.float32), verbose=0))
    return np.vstack(out)

print("=== Baseline ===", flush=True)
proba_base = batched_predict(detector, X_test, BATCH)
y_true = np.argmax(y_test, axis=1)
y_pred_base = np.argmax(proba_base, axis=1)
loss_base, acc_base = detector.evaluate(X_test[:].astype(np.float32), y_test, verbose=0)
print(f"Loss: {loss_base:.4f} | Acc: {acc_base:.4f}", flush=True)

# Generar X_adv y delta por bloques
adv_path = DATA_DIR / "X_adv_eval_temp.npy"
delta_path = DATA_DIR / "delta_eval_temp.npy"
X_adv_mm = np.lib.format.open_memmap(adv_path, mode="w+", dtype=np.float32,
                                     shape=X_test.shape)
delta_mm = np.lib.format.open_memmap(delta_path, mode="w+", dtype=np.float32,
                                     shape=X_test.shape)

print("\n=== Generando X_adv ===", flush=True)
for i, s in enumerate(range(0, n_total, BATCH), 1):
    e = min(s+BATCH, n_total)
    xb = X_test[s:e].astype(np.float32)
    xb_tf = tf.convert_to_tensor(xb, dtype=tf.float32)
    delta = EPSILON * attacker(xb_tf, training=False)
    x_adv = tf.clip_by_value(xb_tf + delta, 0.0, 1.0).numpy()
    X_adv_mm[s:e] = x_adv
    delta_mm[s:e] = (x_adv - xb)
    if i % PRINT_EVERY == 0 or e == n_total:
        print(f"  batch {i}: [{s}-{e}) {100*e/n_total:.2f}%", flush=True)

del X_adv_mm; del delta_mm
os.replace(adv_path, DATA_DIR / "X_adv_eval.npy")
os.replace(delta_path, DATA_DIR / "delta_eval.npy")
X_adv = np.load(DATA_DIR / "X_adv_eval.npy", mmap_mode="r")
delta_all = np.load(DATA_DIR / "delta_eval.npy", mmap_mode="r")

print("\n=== Detector en X_adv ===", flush=True)
proba_adv = batched_predict(detector, X_adv, BATCH)
y_pred_adv = np.argmax(proba_adv, axis=1)
loss_adv, acc_adv = detector.evaluate(X_adv[:].astype(np.float32), y_test, verbose=0)
print(f"Loss: {loss_adv:.4f} | Acc: {acc_adv:.4f}", flush=True)

# Métricas
MAL = (y_true == 1)
mal_count = int(MAL.sum())
asr = 100.0 * (y_pred_adv[MAL] == TARGET_CLASS).mean() if mal_count>0 else 0.0
conf_target_mean = float(proba_adv[MAL, TARGET_CLASS][y_pred_adv[MAL]==TARGET_CLASS].mean()) if mal_count>0 and (y_pred_adv[MAL]==TARGET_CLASS).any() else 0.0

linf_global = float(np.max(np.abs(delta_all)))
linf_mean = float(np.mean(np.max(np.abs(delta_all).reshape(n_total, -1), axis=1)))
l1_mean = float(np.mean(np.mean(np.abs(delta_all).reshape(n_total, -1), axis=1)))
if delta_all.shape[1] > 1:
    tv_mean = float(np.mean(np.abs(delta_all[:,1:,...] - delta_all[:,:-1,...])))
else:
    tv_mean = 0.0

print("\n===== BASELINE =====", flush=True)
print(f"Accuracy: {acc_base:.4f}")
print("Reporte:\n", classification_report(y_true, y_pred_base, target_names=["Benigno","Malware"]), flush=True)
print("CM:\n", confusion_matrix(y_true, y_pred_base, labels=[0,1]), flush=True)

print("\n===== ADVERSARIAL =====", flush=True)
print(f"Accuracy: {acc_adv:.4f}")
print("Reporte:\n", classification_report(y_true, y_pred_adv, target_names=["Benigno","Malware"]), flush=True)
print("CM:\n", confusion_matrix(y_true, y_pred_adv, labels=[0,1]), flush=True)

print("\n===== EFECTIVIDAD =====", flush=True)
print(f"Muestras malware: {mal_count}", flush=True)
print(f"ASR: {asr:.2f}% | Conf(Benigno | éxitos): {conf_target_mean:.4f}", flush=True)

print("\n===== STEALTH =====", flush=True)
print(f"L∞ global: {linf_global:.6f} (ε={EPSILON}) | L∞ promedio: {linf_mean:.6f}", flush=True)
print(f"L1 promedio: {l1_mean:.8f} | TV temporal: {tv_mean:.8f}", flush=True)

ok_asr = asr >= 40.0
ok_drop = (acc_adv <= acc_base - 0.10)
ok_linf = linf_global <= EPSILON + 1e-6
print("\n===== CHECK =====", flush=True)
print(f"ASR>=40%? {'SI' if ok_asr else 'NO'}", flush=True)
print(f"Accuracy cae ≥10pp? {'SI' if ok_drop else 'NO'}", flush=True)
print(f"Respeta ε? {'SI' if ok_linf else 'NO'}", flush=True)
