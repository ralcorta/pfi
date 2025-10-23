#!/usr/bin/env python3
# 1_entrenar_atacante.py — Teacher-PGD (con restarts) + margin + anti-saturación + reporte ASR–ε

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

# Orden de clases esperado por el detector y por y_*: [benigno=0, malware=1]
TARGET_CLASS = 0

# Curriculum de epsilon (sólo train). Podés subir EPS_MAX si querés más presupuesto.
EPS_START = 0.05
EPS_MAX   = 0.08
EPS_STEP  = 0.005

# Pesos de pérdidas
ALIGN_LAMBDA   = 2.0
UNTARGETED_LMB = 0.5
TEACH_LAMBDA   = 2.0
MARGIN_LAMBDA  = 1.0

# Regularización leve anti-saturación
L1_LAMBDA = 0.0
TV_LAMBDA = 0.0
SAT_W     = 0.02   # > 0 para que no se pegue a ±eps

# Activación: tanh con ganancia moderada (menos saturación)
TEMP = 6.0
GAIN = 1.5

BATCH_SIZE = 64
EPOCHS = 40
LR = 2e-3

# PGD teacher (L∞) fuerte
PGD_STEPS    = 32
PGD_RESTARTS = 3   # más robusto que 1 solo

# Logging / early stop
PRINT_EVERY = 50
DEBUG_SUBSET = None

EARLY_STOP = True
PATIENCE   = 3
MIN_DELTA  = 1e-3
# Por defecto medimos al presupuesto máximo (cambia acá si querés reportar otro ε)
EVAL_EPS = EPS_MAX

GRAD_DEBUG = True
GRAD_DEBUG_EVERY  = 200
GRAD_DEBUG_LAYERS = 6

TF_FUNCTION = False

# Malla para ver ASR–ε en probe/val
EPS_GRID = [0.05, 0.06, 0.07, 0.08]

# -------------------------
# Utils
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

def eps_for_epoch(e):
    return np.float32(min(EPS_MAX, EPS_START + EPS_STEP*e))

def tv_loss(delta):
    dt = delta[:, 1:, ...] - delta[:, :-1, ...]
    return tf.reduce_mean(tf.abs(dt))

def has_bad(x):
    x = tf.convert_to_tensor(x)
    return bool(tf.math.reduce_any(tf.math.is_nan(x)).numpy() or
                tf.math.reduce_any(tf.math.is_inf(x)).numpy())

# -------------------------
# Carga detector y datos
# -------------------------
print(f"DATA_DIR = {DATA_DIR.resolve()}", flush=True)
print(f"DETECTOR_PATH = {DETECTOR_PATH.resolve()}", flush=True)
print(device_info(), flush=True)
if not DETECTOR_PATH.exists():
    raise FileNotFoundError(f"Detector no encontrado: {DETECTOR_PATH}")

print("Cargando detector ...", flush=True)
detector = load_model(DETECTOR_PATH)
detector.trainable = False
print("Detector cargado.", flush=True)

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
# Modelo atacante
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
    delta_hat = layers.TimeDistributed(layers.Conv2D(1, (1,1), padding="same", activation="linear"))(z)
    return models.Model(x_in, delta_hat, name="AttackerNet")

attacker = build_attacker()
ce = tf.keras.losses.CategoricalCrossentropy(from_logits=False)
print("Atacante listo. Parámetros:", attacker.count_params(), flush=True)

# -------------------------
# Datasets malware-only
# -------------------------
def make_dataset_malware_only(X_path, y_path, batch, shuffle=True, debug_subset=None):
    X = np.load(X_path, mmap_mode="r"); Y = np.load(y_path, mmap_mode="r")
    y_lab = np.argmax(Y, axis=1)
    idx = np.where(y_lab == 1)[0]  # 1 = malware
    if debug_subset: idx = idx[:int(debug_subset)]
    n = len(idx)
    if shuffle: np.random.shuffle(idx)
    X_sel, Y_sel = X[idx], Y[idx]
    ds = tf.data.Dataset.from_tensor_slices((X_sel, Y_sel))
    if shuffle: ds = ds.shuffle(min(n, 10000))
    return ds.batch(batch).prefetch(tf.data.AUTOTUNE), n

train_ds, n_train_mal = make_dataset_malware_only(X_train_path, y_train_path, BATCH_SIZE, shuffle=True,  debug_subset=DEBUG_SUBSET)
val_ds,   n_val_mal   = make_dataset_malware_only(X_test_path,  y_test_path,  BATCH_SIZE, shuffle=False, debug_subset=DEBUG_SUBSET)
steps_per_epoch = int(np.ceil(n_train_mal / BATCH_SIZE))
val_steps       = int(np.ceil(n_val_mal   / BATCH_SIZE))
print(f"Dataset malware-only: {n_train_mal} train ({steps_per_epoch}/época) | {n_val_mal} val ({val_steps}/val)", flush=True)

# Optimizador + clip norm
total_steps = steps_per_epoch * EPOCHS
lr_schedule = tf.keras.optimizers.schedules.CosineDecay(LR, total_steps, alpha=0.1)
optimizer = tf.keras.optimizers.Adam(learning_rate=lr_schedule, clipnorm=1.0)

# Probe (para logging rápido)
probe_xb, probe_yb = next(iter(val_ds.unbatch().batch(min(512, max(BATCH_SIZE, 256)))))
print(f"Probe de validación: {probe_xb.shape[0]} muestras", flush=True)

# -------------------------
# PGD teacher (L∞) con restarts
# -------------------------
@tf.function(reduce_retracing=True)
def pgd_teacher_once(x, y_tgt, eps, steps):
    alpha = eps / tf.cast(steps, tf.float32)
    adv = tf.clip_by_value(x + tf.random.uniform(tf.shape(x), -eps, eps), 0.0, 1.0)
    for _ in tf.range(steps):
        with tf.GradientTape() as t:
            t.watch(adv)
            pred = detector(adv, training=False)
            loss = ce(y_tgt, pred)
        grad = t.gradient(loss, adv)
        adv = adv + alpha * tf.sign(grad)
        adv = tf.clip_by_value(tf.minimum(x + eps, tf.maximum(x - eps, adv)), 0.0, 1.0)
    return adv, loss

def pgd_teacher(x, y_tgt, eps, steps, restarts):
    best_adv, best_loss = None, None
    for _ in range(restarts):
        adv, loss = pgd_teacher_once(x, y_tgt, eps, steps)
        if best_loss is None:
            best_adv, best_loss = adv, loss
        else:
            # elegimos el que más empuja hacia el target (menor CE al target)
            choose = tf.reshape(loss < best_loss, (-1,))  # per-sample no, usamos global
            if tf.reduce_all(~choose):
                if tf.reduce_mean(loss) < tf.reduce_mean(best_loss):
                    best_adv, best_loss = adv, loss
            else:
                best_adv, best_loss = adv, loss if tf.reduce_mean(loss) < tf.reduce_mean(best_loss) else (best_adv, best_loss)
    return best_adv

# -------------------------
# Alineamiento (cosine)
# -------------------------
def cosine_alignment_loss(delta, g):
    d  = tf.reshape(delta, [tf.shape(delta)[0], -1])
    gg = tf.reshape(g,     [tf.shape(g)[0], -1])
    dot  = tf.reduce_sum(d * (-gg), axis=1)
    norm = tf.norm(d, axis=1) * tf.norm(gg, axis=1) + 1e-8
    return -tf.reduce_mean(dot / norm)

# -------------------------
# Train step (con teacher)
# -------------------------
def train_step_impl(x, y_true, eps):
    y_tgt = tf.one_hot(tf.fill((tf.shape(y_true)[0],), TARGET_CLASS), depth=y_true.shape[1])

    # Teacher PGD desde x
    x_pgd = pgd_teacher(x, y_tgt, tf.cast(eps, tf.float32), tf.constant(PGD_STEPS), PGD_RESTARTS)
    delta_teacher = tf.clip_by_value(x_pgd - x, -eps, eps)

    with tf.GradientTape() as tape:
        delta_hat = attacker(x, training=True)
        delta_raw = tf.tanh(GAIN * delta_hat / TEMP)
        delta = eps * delta_raw
        x_adv = tf.clip_by_value(x + delta, 0.0, 1.0)

        y_pred = detector(x_adv, training=False)

        # CE hacia benigno + alejar del label real
        loss_target = ce(y_tgt, y_pred)
        loss_untgt  = ce(y_true, y_pred)

        # Margin (log-probs)
        p_ben = tf.clip_by_value(y_pred[:, TARGET_CLASS], 1e-6, 1.0)
        p_mal = tf.clip_by_value(y_pred[:, 1 - TARGET_CLASS], 1e-6, 1.0)
        margin_loss = -tf.reduce_mean(tf.math.log(p_ben) - tf.math.log(p_mal))

        # Alineamiento con gradiente en x_adv
        with tf.GradientTape() as tape_align:
            tape_align.watch(x_adv)
            loss_to_benign = ce(y_tgt, detector(x_adv, training=False))
        g_adv = tf.stop_gradient(tape_align.gradient(loss_to_benign, x_adv))
        loss_align = cosine_alignment_loss(delta, g_adv)

        # Teacher imitation
        teach_mse = tf.reduce_mean(tf.square(delta - delta_teacher))

        # Regularizadores
        loss_l1  = tf.reduce_mean(tf.abs(delta)) if L1_LAMBDA > 0 else 0.0
        loss_tv  = tv_loss(delta)                if TV_LAMBDA > 0 else 0.0
        sat_loss = tf.reduce_mean(tf.nn.relu(tf.abs(delta) - 0.9*eps)) if SAT_W > 0 else 0.0

        loss = (loss_target
                - UNTARGETED_LMB * loss_untgt
                + ALIGN_LAMBDA * loss_align
                + TEACH_LAMBDA * teach_mse
                + MARGIN_LAMBDA * margin_loss
                + L1_LAMBDA * loss_l1 + TV_LAMBDA * loss_tv + SAT_W * sat_loss)

    grads = tape.gradient(loss, attacker.trainable_variables)
    gnorm = tf.linalg.global_norm([g for g in grads if g is not None])
    optimizer.apply_gradients(zip(grads, attacker.trainable_variables))

    benign_prob = tf.reduce_mean(p_ben)
    frac_sat = tf.reduce_mean(tf.cast(tf.abs(delta) >= 0.9*eps, tf.float32))
    return (loss, loss_target, loss_align, teach_mse, margin_loss, gnorm, benign_prob, frac_sat)

train_step = tf.function(train_step_impl) if TF_FUNCTION else train_step_impl

def debug_grad_norms(x, y_true, eps, max_vars=GRAD_DEBUG_LAYERS):
    y_tgt = tf.one_hot(tf.fill((tf.shape(y_true)[0],), TARGET_CLASS), depth=y_true.shape[1])
    with tf.GradientTape() as tape:
        d_hat = attacker(x, training=True)
        d = eps * tf.tanh(GAIN * d_hat / TEMP)
        x_adv = tf.clip_by_value(x + d, 0.0, 1.0)
        loss = ce(y_tgt, detector(x_adv, training=False))
    grads = tape.gradient(loss, attacker.trainable_variables)
    print("   ↳ Grad norms por variable (primeros):", flush=True)
    shown = 0
    for v, g in zip(attacker.trainable_variables, grads):
        if g is None: continue
        try: nrm = float(tf.linalg.norm(g).numpy())
        except Exception: continue
        print(f"     - {v.name:40s} ||g||={nrm:.6f}", flush=True)
        shown += 1
        if shown >= max_vars: break

# -------------------------
# Evaluaciones
# -------------------------
def eval_val_fixed_eps(attacker_model, detector_model, val_dataset, eps_fixed):
    vals, probs, fr_sats = [], [], []
    for xb, yb in val_dataset:
        d_hat = attacker_model(xb, training=False)
        d = eps_fixed * tf.tanh(GAIN * d_hat / TEMP)
        x_adv = tf.clip_by_value(xb + d, 0.0, 1.0)
        y_tgt = tf.one_hot(tf.fill((tf.shape(yb)[0],), TARGET_CLASS), depth=yb.shape[1])
        y_pred = detector_model(x_adv, training=False)
        vals.append(ce(y_tgt, y_pred).numpy())
        probs.append(tf.reduce_mean(y_pred[:, TARGET_CLASS]).numpy())
        fr_sats.append(tf.reduce_mean(tf.cast(tf.abs(d) >= 0.9*eps_fixed, tf.float32)).numpy())
    return float(np.mean(vals)), float(np.mean(probs)), float(np.mean(fr_sats))

def asr_on_batch(xb, eps_list):
    # Devuelve dict eps->ASR para el probe
    d = {}
    for eps in eps_list:
        d_hat = attacker(xb, training=False)
        delta = eps * tf.tanh(GAIN * d_hat / TEMP)
        xa = tf.clip_by_value(xb + delta, 0.0, 1.0)
        yp = detector(xa, training=False)
        y_pred = tf.argmax(yp, axis=1)
        d[eps] = float(tf.reduce_mean(tf.cast(y_pred == TARGET_CLASS, tf.float32)).numpy())
    return d

def asr_on_dataset(ds, eps_list):
    # Devuelve dict eps->ASR en todo el dataset (val)
    d = {eps: [] for eps in eps_list}
    for xb, yb in ds:
        d_hat = attacker(xb, training=False)
        for eps in eps_list:
            delta = eps * tf.tanh(GAIN * d_hat / TEMP)
            xa = tf.clip_by_value(xb + delta, 0.0, 1.0)
            yp = detector(xa, training=False)
            y_pred = tf.argmax(yp, axis=1)
            d[eps].append(tf.reduce_mean(tf.cast(y_pred == TARGET_CLASS, tf.float32)).numpy())
    return {eps: float(np.mean(vals)) for eps, vals in d.items()}

# -------------------------
# Train loop
# -------------------------
print("Iniciando entrenamiento ...", flush=True)
best_val = 1e9
best_fixed = np.inf
no_improve = 0

t_start_all = time.time()
ema_bt = None

for epoch in range(1, EPOCHS+1):
    epoch_start = time.time()
    eps = eps_for_epoch(epoch)
    print(f"\n🚀 Epoch {epoch}/{EPOCHS} | ε={eps:.3f} | steps={steps_per_epoch}", flush=True)

    tl, t_ce, l_align, l_teach, l_margin, gn_l, bprob_l, fsat_l = [], [], [], [], [], [], [], []
    batch_idx = 0

    for xb, yb in train_ds:
        b0 = time.time()

        (loss, loss_ce_tgt, loss_align, teach_mse, margin_loss,
         gnorm, benign_prob, frac_sat) = train_step(xb, yb, tf.constant(eps))

        if has_bad(loss) or has_bad(gnorm):
            print("❌ NaN/Inf detectado. Abortando.", flush=True)
            raise RuntimeError("NaN/Inf en entrenamiento")

        tl.append(float(loss)); t_ce.append(float(loss_ce_tgt))
        l_align.append(float(loss_align)); l_teach.append(float(teach_mse))
        l_margin.append(float(margin_loss)); gn_l.append(float(gnorm))
        bprob_l.append(float(benign_prob)); fsat_l.append(float(frac_sat))

        batch_idx += 1
        bt = time.time() - b0
        ema_bt = bt if ema_bt is None else 0.9*ema_bt + 0.1*bt
        eta_min = (steps_per_epoch - batch_idx) * (ema_bt or bt) / 60.0

        if batch_idx % PRINT_EVERY == 0 or batch_idx == steps_per_epoch:
            probe_asr = asr_on_batch(probe_xb, EPS_GRID)
            print(f"  🔄 Epoch {epoch}, batch {batch_idx}/{steps_per_epoch}: "
                  f"loss={np.mean(tl):.4f} | tgtCE={np.mean(t_ce):.4f} | "
                  f"align={np.mean(l_align):.4f} | teachMSE={np.mean(l_teach):.6f} | "
                  f"margin={np.mean(l_margin):.4f} | gnorm={np.mean(gn_l):.6f} | "
                  f"benign_p={np.mean(bprob_l):.3f} | frac_sat={np.mean(fsat_l):.3f} | "
                  f"ASR_probe{{ε}}={ {f'{k:.2f}': f'{v:.2f}' for k,v in probe_asr.items()} } | "
                  f"bt={bt:.2f}s | ETA≈{eta_min:.1f} min",
                  flush=True)

        if GRAD_DEBUG and (batch_idx % GRAD_DEBUG_EVERY == 0):
            debug_grad_norms(xb[:min(8, xb.shape[0])], yb[:min(8, yb.shape[0])], eps)

    # Validación al eps actual
    vt, bps, fsats = [], [], []
    for xb, yb in val_ds:
        d_hat = attacker(xb, training=False)
        dlt = eps * tf.tanh(GAIN * d_hat / TEMP)
        x_adv = tf.clip_by_value(xb + dlt, 0.0, 1.0)
        y_tgt = tf.one_hot(tf.fill((tf.shape(yb)[0],), TARGET_CLASS), depth=yb.shape[1])
        y_pred = detector(x_adv, training=False)
        vt.append(ce(y_tgt, y_pred).numpy())
        bps.append(tf.reduce_mean(y_pred[:, TARGET_CLASS]).numpy())
        fsats.append(tf.reduce_mean(tf.cast(tf.abs(dlt) >= 0.9*eps, tf.float32)).numpy())

    e_time = time.time() - epoch_start
    print(f"[Epoch {epoch:02d}] loss={np.mean(tl):.4f} | tgtCE={np.mean(t_ce):.4f} | "
          f"align={np.mean(l_align):.4f} | teachMSE={np.mean(l_teach):.6f} | margin={np.mean(l_margin):.4f} | "
          f"gnorm={np.mean(gn_l):.6f} | val_tgtCE={np.mean(vt):.4f} | "
          f"val_benign_p={np.mean(bps):.3f} | val_frac_sat={np.mean(fsats):.3f} | "
          f"epoch_time={e_time:.2f}s", flush=True)

    # Guardado por métrica a ε actual
    cur_val = float(np.mean(vt))
    if cur_val < best_val:
        best_val = cur_val
        attacker.save(DATA_DIR / "attacker_model.keras")
        print(f"  ✅ Guardado mejor atacante (val_tgtCE={best_val:.4f})", flush=True)

    # Early stopping a ε=EVAL_EPS
    if EARLY_STOP:
        val_fixed_ce, val_fixed_bp, val_fixed_fs = eval_val_fixed_eps(attacker, detector, val_ds, EVAL_EPS)
        print(f"🧪 val_tgtCE @ ε={EVAL_EPS:.3f}: {val_fixed_ce:.4f} | benign_p: {val_fixed_bp:.3f} | frac_sat: {val_fixed_fs:.3f}", flush=True)
        if val_fixed_ce < best_fixed - MIN_DELTA:
            best_fixed = val_fixed_ce
            no_improve = 0
            attacker.save(DATA_DIR / "attacker_model.keras")
            print("  ✅ Mejoró a ε fijo — guardado", flush=True)
        else:
            no_improve += 1
            print(f"  ⚠️ Sin mejora a ε fijo ({no_improve}/{PATIENCE})", flush=True)
            if no_improve >= PATIENCE:
                print("⏸️ Early stopping: sin mejora a ε fijo", flush=True)
                break

    # Curva ASR–ε en validación (para entender el “knee”)
    val_asr_grid = asr_on_dataset(val_ds, EPS_GRID)
    print(f"📈 ASR_val{{ε}} = { {f'{k:.2f}': f'{v:.3f}' for k,v in val_asr_grid.items()} }", flush=True)

print(f"\n✔ Entrenamiento finalizado en {time.time()-t_start_all:.2f}s (E={EPOCHS})", flush=True)