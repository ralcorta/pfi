# train_attacker.py
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import time
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.models import load_model

# -------------------------
# Config
# -------------------------
DATA_DIR = Path(".")
DETECTOR_PATH = DATA_DIR / "models/training/detection/convlstm_model.keras"

TARGET_CLASS = 0  # Benigno

# Curriculum de epsilon
EPS_START = 0.02
EPS_MAX   = 0.05
EPS_STEP  = 0.003

# Regularización (reducidas 10x respecto al script original)
L1_LAMBDA = 2e-5
TV_LAMBDA = 2e-5

# Pérdida combinada
UNTARGETED_LAMBDA = 0.5   # resta CE(y_true, y_pred)

BATCH_SIZE = 64
EPOCHS = 20
LR = 1e-3

# Warm start FGSM (extendido y ligeramente más fuerte)
WARM_START_EPOCHS = 5
FGSM_STEP = 0.02

# Logging
PRINT_EVERY = 50
DEBUG_SUBSET = None          # ej. 1024

# --- EARLY STOPPING (a ε fijo) ---
EARLY_STOP = True
PATIENCE = 3
MIN_DELTA = 1e-3
EVAL_EPS = EPS_MAX          # evaluar siempre al tope
START_ES_AT_EPSMAX = True   # no activar hasta llegar al tope

# --- DEBUG GRADS POR VARIABLE ---
GRAD_DEBUG = True
GRAD_DEBUG_EVERY = 200       # cada N batches
GRAD_DEBUG_LAYERS = 6        # cuántas variables listar (kernels/biases)

# -------------------------
# Utilidades
# -------------------------
def device_info():
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            details = [tf.config.experimental.get_device_details(g)['device_name'] for g in gpus]
        except Exception:
            details = ["GPU"]
        return f"GPU(s) detectadas: {details}"
    return "Sin GPU (CPU)"

def eps_for_epoch(e):  # 1-indexed
    return np.float32(min(EPS_MAX, EPS_START + EPS_STEP*e))

def tv_loss(delta):
    # diferencia temporal (delta shape: [B, T, H, W, C])
    dt = delta[:, 1:, ...] - delta[:, :-1, ...]
    return tf.reduce_mean(tf.abs(dt))

def has_bad(x):
    x = tf.convert_to_tensor(x)
    return bool(tf.math.reduce_any(tf.math.is_nan(x)).numpy() or
                tf.math.reduce_any(tf.math.is_inf(x)).numpy())

# Straight-through estimator para el clip en [lo,hi]
def clip_ste(z, lo=0.0, hi=1.0):
    z_clip = tf.clip_by_value(z, lo, hi)
    # forward: z_clip, backward: grad pasa como si no hubiera clip
    return z + tf.stop_gradient(z_clip - z)

# -------------------------
# Chequeos / modelos
# -------------------------
print(f"DATA_DIR = {DATA_DIR.resolve()}", flush=True)
print(f"DETECTOR_PATH = {DETECTOR_PATH.resolve()}", flush=True)
print(device_info(), flush=True)
if not DETECTOR_PATH.exists():
    raise FileNotFoundError(f"Detector no encontrado: {DETECTOR_PATH}")

print("Cargando detector ...", flush=True)
t0 = time.time()
detector = load_model(DETECTOR_PATH)
detector.trainable = False
print(f"Detector cargado en {time.time()-t0:.2f}s", flush=True)

# -------------------------
# Datos
# -------------------------
X_train_path = DATA_DIR / "X_train.npy"
y_train_path = DATA_DIR / "y_train.npy"
X_test_path  = DATA_DIR / "X_test.npy"
y_test_path  = DATA_DIR / "y_test.npy"
for p in (X_train_path, y_train_path, X_test_path, y_test_path):
    if not p.exists():
        raise FileNotFoundError(f"Falta archivo: {p}")

X_train_mm = np.load(X_train_path, mmap_mode="r")
y_train_mm = np.load(y_train_path, mmap_mode="r")
T, H, W, C = X_train_mm.shape[1:]
print(f"Shapes -> X_train: {X_train_mm.shape}, y_train: {y_train_mm.shape}, input: ({T},{H},{W},{C})", flush=True)

# -------------------------
# Modelo atacante (más capaz)
# -------------------------
def build_attacker():
    x_in = layers.Input(shape=(T, H, W, C))
    z = layers.TimeDistributed(layers.Conv2D(16, (3,3), padding="same", activation="relu"))(x_in)
    z = layers.TimeDistributed(layers.Conv2D(32, (3,3), padding="same", activation="relu"))(z)
    z = layers.TimeDistributed(layers.GlobalAveragePooling2D())(z)
    z = layers.LSTM(64, return_sequences=True)(z)
    z = layers.TimeDistributed(layers.Dense(H*W, activation="linear"))(z)
    z = layers.Reshape((T, H, W, 1))(z)
    z = layers.TimeDistributed(layers.Conv2D(16, (3,3), padding="same", activation="relu"))(z)
    # SALIDA LINEAL (antes: activation="tanh")
    delta_hat = layers.TimeDistributed(layers.Conv2D(1, (1,1), padding="same", activation="linear"))(z)
    return models.Model(x_in, delta_hat, name="AttackerNet")

print("Construyendo atacante ...", flush=True)
attacker = build_attacker()
# Optimizer con clipnorm para estabilidad
optimizer = tf.keras.optimizers.Adam(LR, clipnorm=1.0)
ce = tf.keras.losses.CategoricalCrossentropy(from_logits=False)
print("Atacante listo. Parámetros:", attacker.count_params(), flush=True)

# -------------------------
# Datasets: SOLO MALWARE
# -------------------------
def make_dataset_malware_only(X_path, y_path, batch, shuffle=True, debug_subset=None):
    X = np.load(X_path, mmap_mode="r")
    Y = np.load(y_path, mmap_mode="r")
    y_lab = np.argmax(Y, axis=1)
    idx = np.where(y_lab == 1)[0]   # 1 = malware
    if debug_subset: idx = idx[:int(debug_subset)]
    n = len(idx)
    if shuffle: np.random.shuffle(idx)
    X_sel = X[idx]
    Y_sel = Y[idx]
    ds = tf.data.Dataset.from_tensor_slices((X_sel, Y_sel))
    if shuffle: ds = ds.shuffle(min(n, 10000))
    ds = ds.batch(batch).prefetch(tf.data.AUTOTUNE)
    return ds, n

print("Creando datasets malware-only ...", flush=True)
train_ds, n_train_mal = make_dataset_malware_only(X_train_path, y_train_path, BATCH_SIZE, shuffle=True,  debug_subset=DEBUG_SUBSET)
val_ds,   n_val_mal   = make_dataset_malware_only(X_test_path,  y_test_path,  BATCH_SIZE, shuffle=False, debug_subset=DEBUG_SUBSET)
steps_per_epoch = int(np.ceil(n_train_mal / BATCH_SIZE))
val_steps       = int(np.ceil(n_val_mal   / BATCH_SIZE))
print(f"Dataset malware-only: {n_train_mal} train muestras ({steps_per_epoch} batches/epoch)", flush=True)
print(f"Dataset malware-only: {n_val_mal} val muestras ({val_steps} batches/val)", flush=True)

# Mini probe para ASR en entrenamiento
probe_xb, probe_yb = next(iter(val_ds.unbatch().batch(min(512, max(BATCH_SIZE, 256)))))
print(f"Probe de validación: {probe_xb.shape[0]} muestras", flush=True)

# -------------------------
# Paso de entrenamiento (con grad-norm)
# -------------------------
@tf.function
def train_step(x, y_true, eps):
    # construimos target benigno
    y_tgt = tf.one_hot(tf.fill((tf.shape(y_true)[0],), TARGET_CLASS), depth=y_true.shape[1])
    with tf.GradientTape() as tape:
        delta_hat = attacker(x, training=True)      # salida LINEAL
        # limitamos delta_hat en [-1,1] y lo escalamos por eps
        delta = eps * tf.clip_by_value(delta_hat, -1.0, 1.0)
        # usamos clip_ste para que la operación de clip no anule gradientes
        x_adv = clip_ste(x + delta, 0.0, 1.0)
        y_pred = detector(x_adv, training=False)

        loss_target = ce(y_tgt, y_pred)             # targeted
        loss_true   = ce(y_true, y_pred)            # acercamiento a la real
        loss_l1 = tf.reduce_mean(tf.abs(delta))
        loss_tv = tv_loss(delta)
        loss = loss_target - UNTARGETED_LAMBDA*loss_true + L1_LAMBDA*loss_l1 + TV_LAMBDA*loss_tv

    grads = tape.gradient(loss, attacker.trainable_variables)
    gnorm = tf.linalg.global_norm([g for g in grads if g is not None])
    optimizer.apply_gradients(zip(grads, attacker.trainable_variables))
    return loss, loss_target, loss_true, loss_l1, loss_tv, gnorm

# --- DEBUG: grad-norms por variable (solo lectura, fuera de tf.function) ---
def debug_grad_norms(x, y_true, eps, max_vars=GRAD_DEBUG_LAYERS):
    y_tgt = tf.one_hot(tf.fill((tf.shape(y_true)[0],), TARGET_CLASS), depth=y_true.shape[1])
    with tf.GradientTape() as tape:
        delta_hat = attacker(x, training=True)
        delta = eps * tf.clip_by_value(delta_hat, -1.0, 1.0)
        x_adv = clip_ste(x + delta, 0.0, 1.0)
        y_pred = detector(x_adv, training=False)
        loss_target = ce(y_tgt, y_pred)
        loss_true   = ce(y_true, y_pred)
        loss_l1 = tf.reduce_mean(tf.abs(delta))
        loss_tv = tv_loss(delta)
        loss = loss_target - UNTARGETED_LAMBDA*loss_true + L1_LAMBDA*loss_l1 + TV_LAMBDA*loss_tv
    grads = tape.gradient(loss, attacker.trainable_variables)
    print("   ↳ Grad norms por variable (primeros):", flush=True)
    shown = 0
    for v, g in zip(attacker.trainable_variables, grads):
        if g is None: continue
        try:
            nrm = float(tf.linalg.norm(g).numpy())
        except Exception:
            continue
        print(f"     - {v.name:40s} ||g||={nrm:.6f}", flush=True)
        shown += 1
        if shown >= max_vars: break

# -------------------------
# Helpers de validación
# -------------------------
ce_loss = tf.keras.losses.CategoricalCrossentropy(from_logits=False)
def eval_val_fixed_eps(attacker_model, detector_model, val_dataset, eps_fixed):
    vals = []
    for xb, yb in val_dataset:
        d_hat = attacker_model(xb, training=False)
        d_clipped = tf.clip_by_value(d_hat, -1.0, 1.0)
        x_adv = tf.clip_by_value(xb + eps_fixed * d_clipped, 0.0, 1.0)
        y_tgt = tf.one_hot(tf.fill((tf.shape(yb)[0],), TARGET_CLASS), depth=yb.shape[1])
        y_pred = detector_model(x_adv, training=False)
        vals.append(ce_loss(y_tgt, y_pred).numpy())
    return float(np.mean(vals))

# -------------------------
# Entrenamiento
# -------------------------
print("Iniciando entrenamiento ...", flush=True)
best_val = 1e9
best_fixed = np.inf
no_improve = 0

t_start_all = time.time()
ema_bt = None  # media móvil del tiempo por batch

for epoch in range(1, EPOCHS+1):
    epoch_start = time.time()
    eps = eps_for_epoch(epoch)
    print(f"\n🚀 Epoch {epoch}/{EPOCHS} | ε={eps:.3f} | steps={steps_per_epoch}", flush=True)

    tl, tgt_l, tru_l, l1_l, tv_l, gn_l = [], [], [], [], [], []
    batch_idx = 0

    for xb, yb in train_ds:
        b0 = time.time()

        # Warm-start FGSM
        if epoch <= WARM_START_EPOCHS:
            with tf.GradientTape() as tape_pgd:
                tape_pgd.watch(xb)
                y_tgt0 = tf.one_hot(tf.fill((tf.shape(yb)[0],), TARGET_CLASS), depth=yb.shape[1])
                pred0 = detector(xb, training=False)
                loss_to_benign = ce(y_tgt0, pred0)
            grad0 = tape_pgd.gradient(loss_to_benign, xb)
            x_seed = tf.clip_by_value(xb + FGSM_STEP * tf.sign(grad0), 0.0, 1.0)
        else:
            x_seed = xb

        loss, lt, ltrue, l1, ltv, gnorm = train_step(x_seed, yb, tf.constant(eps))
        if has_bad(loss) or has_bad(gnorm):
            print("❌ NaN/Inf detectado en loss o grad_norm. Abortando.", flush=True)
            raise RuntimeError("NaN/Inf en entrenamiento")

        tl.append(loss.numpy()); tgt_l.append(lt.numpy()); tru_l.append(ltrue.numpy())
        l1_l.append(l1.numpy()); tv_l.append(ltv.numpy()); gn_l.append(gnorm.numpy())

        # calcular sat_ratio y asr_probe solo cada PRINT_EVERY (para no frenar)
        sat_ratio = None
        asr_probe = None

        batch_idx += 1
        bt = time.time() - b0
        ema_bt = bt if ema_bt is None else 0.9*ema_bt + 0.1*bt
        eta_min = (steps_per_epoch - batch_idx) * (ema_bt or bt) / 60.0

        if batch_idx % PRINT_EVERY == 0 or batch_idx == steps_per_epoch:
            try:
                d_hat_batch = attacker(xb, training=False)
                d_clipped_batch = tf.clip_by_value(d_hat_batch, -1.0, 1.0)
                x_adv_sample = clip_ste(xb + eps * d_clipped_batch, 0.0, 1.0)
                sat_ratio = float(tf.reduce_mean(tf.cast((x_adv_sample <= 0.0) | (x_adv_sample >= 1.0), tf.float32)).numpy())
            except Exception:
                sat_ratio = float(0.0)

            with tf.device('/CPU:0'):
                d_hat = attacker(probe_xb, training=False)
                d_clipped = tf.clip_by_value(d_hat, -1.0, 1.0)
                xa = tf.clip_by_value(probe_xb + eps * d_clipped, 0.0, 1.0)
                yp = detector(xa, training=False)
                y_pred = tf.argmax(yp, axis=1)
                asr_probe = float(tf.reduce_mean(tf.cast(y_pred == TARGET_CLASS, tf.float32)).numpy())

        # Debug de grads por variable
        if GRAD_DEBUG and (batch_idx % GRAD_DEBUG_EVERY == 0):
            debug_grad_norms(xb[:min(8, xb.shape[0])], yb[:min(8, yb.shape[0])], eps)

        if batch_idx % PRINT_EVERY == 0 or batch_idx == steps_per_epoch:
            print(f"  🔄 Epoch {epoch}, batch {batch_idx}/{steps_per_epoch}: "
                  f"loss={np.mean(tl):.4f} | tgt={np.mean(tgt_l):.4f} | untgt={np.mean(tru_l):.4f} | "
                  f"L1={np.mean(l1_l):.5f} | TV={np.mean(tv_l):.5f} | gnorm={np.mean(gn_l):.6f} | "
                  f"asr_probe={asr_probe if asr_probe is not None else '—'} | sat={sat_ratio if sat_ratio is not None else float('nan'):.4f} | "
                  f"bt={bt:.2f}s | ETA≈{eta_min:.1f} min",
                  flush=True)

    # Validación (malware-only) al ε actual (para logging y best_val)
    vt = []
    for xb, yb in val_ds:
        delta_hat = attacker(xb, training=False)
        delta = eps * tf.clip_by_value(delta_hat, -1.0, 1.0)
        x_adv = tf.clip_by_value(xb + delta, 0.0, 1.0)
        y_tgt = tf.one_hot(tf.fill((tf.shape(yb)[0],), TARGET_CLASS), depth=yb.shape[1])
        y_pred = detector(x_adv, training=False)
        vt.append(ce(y_tgt, y_pred).numpy())

    e_time = time.time() - epoch_start
    print(f"[Epoch {epoch:02d}] loss={np.mean(tl):.4f} | tgt={np.mean(tgt_l):.4f} | "
          f"untgt={np.mean(tru_l):.4f} | L1={np.mean(l1_l):.5f} | TV={np.mean(tv_l):.5f} | "
          f"gnorm={np.mean(gn_l):.6f} | val_target={np.mean(vt):.4f} | epoch_time={e_time:.2f}s",
          flush=True)

    # Guardado por métrica a ε actual
    cur_val = float(np.mean(vt))
    if cur_val < best_val:
        best_val = cur_val
        attacker.save(DATA_DIR / "attacker_model.keras")
        print(f"  ✅ Guardado mejor atacante (val_target={best_val:.4f})", flush=True)

    # ---------- EARLY STOPPING a ε fijo ----------
    if EARLY_STOP and (not START_ES_AT_EPSMAX or eps >= EPS_MAX - 1e-12):
        val_fixed = eval_val_fixed_eps(attacker, detector, val_ds, EVAL_EPS)
        print(f"🧪 val_target @ ε={EVAL_EPS:.3f}: {val_fixed:.4f}", flush=True)
        if val_fixed < best_fixed - MIN_DELTA:
            best_fixed = val_fixed
            no_improve = 0
            attacker.save(DATA_DIR / "attacker_model.keras")
            print("  ✅ Mejoró a ε fijo — guardado", flush=True)
        else:
            no_improve += 1
            print(f"  ⚠️ Sin mejora a ε fijo ({no_improve}/{PATIENCE})", flush=True)
            if no_improve >= PATIENCE:
                print("⏸️ Early stopping: sin mejora a ε fijo", flush=True)
                break
    # --------------------------------------------

print(f"\n✔ Entrenamiento finalizado en {time.time()-t_start_all:.2f}s (E={EPOCHS})", flush=True)
