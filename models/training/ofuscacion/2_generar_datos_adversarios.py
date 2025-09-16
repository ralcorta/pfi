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

# Objetivo del ataque: clase 0 (Benigno)
TARGET_CLASS = 0

# Presupuesto base (usaremos curriculum por epoch)
EPS_START = 0.02
EPS_MAX   = 0.05
EPS_STEP  = 0.003   # incremento por epoch hasta EPS_MAX

# Regularización (arrancamos suave)
L1_LAMBDA = 2e-4
TV_LAMBDA = 2e-4

# Pérdida combinada
UNTARGETED_LAMBDA = 0.5  # resta CE(y_true, y_pred)

BATCH_SIZE = 64
EPOCHS = 20
LR = 1e-3

# Warm start FGSM
WARM_START_EPOCHS = 3
FGSM_STEP = 0.01

# Logging / debug
PRINT_EVERY = 50
DEBUG_SUBSET = None  # ej. 1024 para pruebas rápidas

# -------------------------
# Chequear paths
# -------------------------
print(f"DATA_DIR = {DATA_DIR.resolve()}", flush=True)
print(f"DETECTOR_PATH = {DETECTOR_PATH.resolve()}", flush=True)
if not DETECTOR_PATH.exists():
    raise FileNotFoundError(f"Detector no encontrado en: {DETECTOR_PATH.resolve()}")

# -------------------------
# Cargar detector (congelado)
# -------------------------
print("Cargando detector ...", flush=True)
t0 = time.time()
detector = load_model(DETECTOR_PATH)
detector.trainable = False
print(f"Detector cargado en {time.time()-t0:.2f}s", flush=True)

# -------------------------
# Cargar info de datos
# -------------------------
X_train_path = DATA_DIR / "X_train.npy"
y_train_path = DATA_DIR / "y_train.npy"
X_test_path  = DATA_DIR / "X_test.npy"
y_test_path  = DATA_DIR / "y_test.npy"

for p in (X_train_path, y_train_path, X_test_path, y_test_path):
    if not p.exists(): raise FileNotFoundError(f"Falta archivo: {p}")

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
    delta_hat = layers.TimeDistributed(layers.Conv2D(1, (1,1), padding="same", activation="tanh"))(z)
    return models.Model(x_in, delta_hat, name="AttackerNet")

print("Construyendo atacante ...", flush=True)
attacker = build_attacker()
optimizer = tf.keras.optimizers.Adam(LR)
ce = tf.keras.losses.CategoricalCrossentropy(from_logits=False)
print("Atacante listo. Parámetros:", attacker.count_params(), flush=True)

# -------------------------
# Utilidades de pérdida
# -------------------------
def tv_loss(delta):
    dt = delta[:,1:,...] - delta[:,:-1,...]
    return tf.reduce_mean(tf.abs(dt))

@tf.function
def train_step(x, y_true, eps):
    # one-hot de la clase objetivo
    y_tgt = tf.one_hot(tf.fill((tf.shape(y_true)[0],), TARGET_CLASS), depth=y_true.shape[1])

    with tf.GradientTape() as tape:
        delta_hat = attacker(x, training=True)      # [-1,1]
        delta = eps * delta_hat                     # [-eps, +eps]
        x_adv = tf.clip_by_value(x + delta, 0.0, 1.0)

        y_pred = detector(x_adv, training=False)

        # pérdidas
        loss_target = ce(y_tgt, y_pred)             # targeted -> Benigno
        loss_true   = ce(y_true, y_pred)            # ajusta a su etiqueta real
        loss_l1 = tf.reduce_mean(tf.abs(delta))
        loss_tv = tv_loss(delta)

        # combinación: minimizar targeted y alejar de la real
        loss = loss_target - UNTARGETED_LAMBDA*loss_true + L1_LAMBDA*loss_l1 + TV_LAMBDA*loss_tv

    grads = tape.gradient(loss, attacker.trainable_variables)
    optimizer.apply_gradients(zip(grads, attacker.trainable_variables))
    return loss, loss_target, loss_true, loss_l1, loss_tv

# -------------------------
# Datasets: SOLO MALWARE para entrenar/validar
# -------------------------
def make_dataset_malware_only(X_path, y_path, batch, shuffle=True, debug_subset=None):
    X = np.load(X_path, mmap_mode="r")
    Y = np.load(y_path, mmap_mode="r")
    y_lab = np.argmax(Y, axis=1)
    idx = np.where(y_lab == 1)[0]   # clase 1 = malware
    if debug_subset: idx = idx[:int(debug_subset)]
    if shuffle: np.random.shuffle(idx)
    X_sel = X[idx]
    Y_sel = Y[idx]
    print(f"Dataset malware-only: {len(idx)} muestras", flush=True)
    ds = tf.data.Dataset.from_tensor_slices((X_sel, Y_sel))
    if shuffle: ds = ds.shuffle(min(len(idx), 10000))
    ds = ds.batch(batch).prefetch(tf.data.AUTOTUNE)
    return ds

print("Creando datasets malware-only ...", flush=True)
train_ds = make_dataset_malware_only(X_train_path, y_train_path, BATCH_SIZE,
                                     shuffle=True, debug_subset=DEBUG_SUBSET)
val_ds   = make_dataset_malware_only(X_test_path,  y_test_path,  BATCH_SIZE,
                                     shuffle=False, debug_subset=DEBUG_SUBSET)

# -------------------------
# Entrenamiento con curriculum ε y warm-start
# -------------------------
def eps_for_epoch(e):
    return np.float32(min(EPS_MAX, EPS_START + EPS_STEP*e))

print("Iniciando entrenamiento ...", flush=True)
best_val = 1e9
t_start_all = time.time()

for epoch in range(1, EPOCHS+1):
    epoch_start = time.time()
    eps = eps_for_epoch(epoch)
    print(f"\n🚀 Epoch {epoch}/{EPOCHS} | ε={eps:.3f}", flush=True)

    tl, tgt_l, tru_l, l1_l, tv_l = [], [], [], [], []
    batch_idx = 0
    times = []

    for xb, yb in train_ds:
        b0 = time.time()

        # Warm-start FGSM las primeras épocas
        if epoch <= WARM_START_EPOCHS:
            with tf.GradientTape() as tape_pgd:
                tape_pgd.watch(xb)
                y_tgt = tf.one_hot(tf.fill((tf.shape(yb)[0],), TARGET_CLASS), depth=yb.shape[1])
                pred0 = detector(xb, training=False)
                loss_to_benign = ce(y_tgt, pred0)
            grad0 = tape_pgd.gradient(loss_to_benign, xb)
            x_seed = tf.clip_by_value(xb + FGSM_STEP * tf.sign(grad0), 0.0, 1.0)
        else:
            x_seed = xb

        l, lt, ltrue, l1, ltv = train_step(x_seed, yb, tf.constant(eps))
        tl.append(l.numpy()); tgt_l.append(lt.numpy()); tru_l.append(ltrue.numpy())
        l1_l.append(l1.numpy()); tv_l.append(ltv.numpy())

        batch_idx += 1
        bt = time.time() - b0
        times.append(bt)
        if batch_idx % PRINT_EVERY == 0:
            print(f"  🔄 Epoch {epoch}, batch {batch_idx}: "
                  f"loss={np.mean(tl):.4f} | tgt={np.mean(tgt_l):.4f} | "
                  f"untgt={np.mean(tru_l):.4f} | L1={np.mean(l1_l):.5f} | TV={np.mean(tv_l):.5f} | "
                  f"avg_bt={np.mean(times[-PRINT_EVERY:]):.2f}s",
                  flush=True)

    # Validación malware-only
    vt = []
    for xb, yb in val_ds:
        delta_hat = attacker(xb, training=False)
        delta = eps * delta_hat
        x_adv = tf.clip_by_value(xb + delta, 0.0, 1.0)
        y_tgt = tf.one_hot(tf.fill((tf.shape(yb)[0],), TARGET_CLASS), depth=yb.shape[1])
        y_pred = detector(x_adv, training=False)
        vt.append(ce(y_tgt, y_pred).numpy())

    e_time = time.time() - epoch_start
    print(f"[Epoch {epoch:02d}] loss={np.mean(tl):.4f} | tgt={np.mean(tgt_l):.4f} | "
          f"untgt={np.mean(tru_l):.4f} | L1={np.mean(l1_l):.5f} | TV={np.mean(tv_l):.5f} | "
          f"val_target={np.mean(vt):.4f} | epoch_time={e_time:.2f}s", flush=True)

    cur_val = float(np.mean(vt))
    if cur_val < best_val:
        best_val = cur_val
        attacker.save(DATA_DIR / "attacker_model.keras")
        print(f"  ✅ Guardado mejor atacante (val_target={best_val:.4f})", flush=True)

print(f"\n✔ Entrenamiento finalizado en {time.time()-t_start_all:.2f}s (E={EPOCHS})", flush=True)
