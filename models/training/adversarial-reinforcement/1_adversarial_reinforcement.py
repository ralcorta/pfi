# models/training/adversarial-reinforcement/adversarial_reinforcement.py
# Fine-tuning adversarial del detector usando el atacante entrenado (robustez > accuracy)
import os, time
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

# ──────────────────────────────────────────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]                       # carpeta PFI
DET_DIR = ROOT / "models" / "training" / "detection"

DETECTOR_IN_PATH  = DET_DIR / "convlstm_model.keras"                 # detector base
DETECTOR_OUT_PATH = DET_DIR / "convlstm_model_advtrained.keras"      # detector robustecido

ATTACKER_PATH = ROOT / "attacker_model.keras"                        # atacante entrenado

X_TRAIN = DET_DIR / "X_train.npy"
Y_TRAIN = DET_DIR / "y_train.npy"
X_TEST  = DET_DIR / "X_test.npy"
Y_TEST  = DET_DIR / "y_test.npy"

for p in [DETECTOR_IN_PATH, ATTACKER_PATH, X_TRAIN, Y_TRAIN, X_TEST, Y_TEST]:
    assert p.exists(), f"Falta: {p}"

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED); tf.random.set_seed(SEED)

BATCH = 64
EPOCHS = 12
LR = 1e-4                 # LR bajo: fine-tuning estable
ADV_RATIO = 0.7           # % de malware del batch que pasará a adversarial
EPSILON = 0.05            # igual al usado al evaluar/entrenar el atacante
TEMP = 6.0                # mismo escalado que en el entrenamiento del atacante
LABEL_SMOOTH = 0.05       # leve smoothing para estabilidad
USE_MIXUP = False         # dejalo en False para no confundir señales adversariales

# ──────────────────────────────────────────────────────────────────────────────
# Carga de modelos y datos (mmap para ahorrar RAM)
# ──────────────────────────────────────────────────────────────────────────────
print("Cargando detector y atacante…")
detector = load_model(DETECTOR_IN_PATH)
detector.summary()

attacker = load_model(ATTACKER_PATH)
attacker.trainable = False

Xtr = np.load(X_TRAIN, mmap_mode='r')       # (N, T, 32, 32, 1)
Ytr = np.load(Y_TRAIN, mmap_mode='r')       # one-hot (N, 2)
Xte = np.load(X_TEST,  mmap_mode='r')
Yte = np.load(Y_TEST,  mmap_mode='r')

Ntr = Xtr.shape[0]
T, H, W, C = Xtr.shape[1:]
print(f"Train: {Xtr.shape}, Test: {Xte.shape}")

# Índices por clase para armar batches estratificados
ytr_labels = np.argmax(Ytr, axis=1)
idx_mal = np.where(ytr_labels == 1)[0]
idx_ben = np.where(ytr_labels == 0)[0]
print(f"Distribución train -> Benigno: {len(idx_ben)} | Malware: {len(idx_mal)}")

# ──────────────────────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────────────────────
ce = tf.keras.losses.CategoricalCrossentropy(label_smoothing=LABEL_SMOOTH)

@tf.function(reduce_retracing=True)
def make_x_adv(x_batch):
    """
    Genera ejemplos adversariales *del atacante*:
    delta = eps * tanh(delta_hat/TEMP), x_adv = clip(x + delta, [0,1])
    """
    d_hat = attacker(x_batch, training=False)
    delta = EPSILON * tf.tanh(d_hat / TEMP)
    x_adv = tf.clip_by_value(x_batch + delta, 0.0, 1.0)
    return x_adv

def batch_sampler(batch_size=BATCH, adv_ratio=ADV_RATIO):
    """
    Generador que arma batches mixtos:
      - Todo BENIGNO queda limpio (el atacante fue targeteado malware->benigno).
      - Una fracción de MALWARE se convierte a adversarial.
    Mantiene el mismo tamaño de batch.
    """
    # fracciones aproximadas por batch según dataset real
    p_mal = len(idx_mal) / (len(idx_mal) + len(idx_ben) + 1e-8)
    mal_per_batch = max(1, int(round(p_mal * batch_size)))
    ben_per_batch = batch_size - mal_per_batch

    while True:
        mal_ids = np.random.choice(idx_mal, size=mal_per_batch, replace=len(idx_mal) < mal_per_batch)
        ben_ids = np.random.choice(idx_ben, size=ben_per_batch, replace=len(idx_ben) < ben_per_batch)

        # malware -> parte adversarial, parte limpio
        if mal_per_batch > 0:
            k_adv = int(round(adv_ratio * mal_per_batch))
            np.random.shuffle(mal_ids)
            mal_adv_ids = mal_ids[:k_adv]
            mal_clean_ids = mal_ids[k_adv:]
        else:
            mal_adv_ids, mal_clean_ids = np.array([], dtype=int), np.array([], dtype=int)

        ids_clean = np.concatenate([ben_ids, mal_clean_ids])
        X_clean = Xtr[ids_clean].astype(np.float32)
        y_clean = Ytr[ids_clean].astype(np.float32)

        if len(mal_adv_ids) > 0:
            X_mal = Xtr[mal_adv_ids].astype(np.float32)
            y_mal = Ytr[mal_adv_ids].astype(np.float32)   # etiqueta sigue siendo malware
            X_adv = make_x_adv(tf.convert_to_tensor(X_mal)).numpy()
            Xb = np.concatenate([X_clean, X_adv], axis=0)
            yb = np.concatenate([y_clean, y_mal], axis=0)
        else:
            Xb, yb = X_clean, y_clean

        # barajar dentro del batch
        perm = np.random.permutation(len(Xb))
        yield Xb[perm], yb[perm]

def steps_per_epoch_est(n_samples, batch=BATCH):
    return int(np.ceil(n_samples / batch))

# ──────────────────────────────────────────────────────────────────────────────
# Compilación (fine-tuning)
# ──────────────────────────────────────────────────────────────────────────────
opt = tf.keras.optimizers.Adam(learning_rate=LR)
detector.compile(optimizer=opt, loss=ce, metrics=['accuracy'])

early = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True, min_delta=1e-3)
plateau = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=1, min_lr=1e-5, verbose=1)
ckpt = ModelCheckpoint(DETECTOR_OUT_PATH, monitor='val_loss', save_best_only=True, verbose=1)

# ──────────────────────────────────────────────────────────────────────────────
# Entrenamiento
# ──────────────────────────────────────────────────────────────────────────────
train_gen = batch_sampler()
val_data = (Xte[:].astype(np.float32), Yte[:].astype(np.float32))

print("\n🚀 Fine-tuning adversarial…")
hist = detector.fit(
    x = tf.data.Dataset.from_generator(
            lambda: train_gen,
            output_signature=(
                tf.TensorSpec(shape=(None, T, H, W, C), dtype=tf.float32),
                tf.TensorSpec(shape=(None, 2),           dtype=tf.float32)
            )
        ).prefetch(tf.data.AUTOTUNE),
    steps_per_epoch = steps_per_epoch_est(Ntr, BATCH),
    epochs = EPOCHS,
    validation_data = val_data,
    callbacks = [early, plateau, ckpt],
    verbose = 1
)

# Aseguramos guardar el último/best
detector.save(DETECTOR_OUT_PATH)
print(f"\n✅ Detector robustecido guardado en: {DETECTOR_OUT_PATH}")

# ──────────────────────────────────────────────────────────────────────────────
# Evaluación: limpio vs adversarial (test)
# ──────────────────────────────────────────────────────────────────────────────
print("\n🔎 Evaluando robustez…")
clean_loss, clean_acc = detector.evaluate(Xte[:].astype(np.float32), Yte, verbose=0)
print(f"Clean  -> loss={clean_loss:.4f} | acc={clean_acc:.4f}")

# Generamos adversarial para TODO test malware y medimos recall malware adversarial
yte_lab = np.argmax(Yte, axis=1)
MAL_TEST_IDX = np.where(yte_lab == 1)[0]
if len(MAL_TEST_IDX) > 0:
    # creamos X_adv solo para malware de test (sin ocupar RAM total)
    B = 256
    preds_clean_mal = []
    preds_adv_mal = []
    for s in range(0, len(MAL_TEST_IDX), B):
        e = min(s+B, len(MAL_TEST_IDX))
        ids = MAL_TEST_IDX[s:e]
        xb = Xte[ids].astype(np.float32)
        yb = Yte[ids].astype(np.float32)

        y_clean = detector.predict(xb, verbose=0)
        x_adv = make_x_adv(tf.convert_to_tensor(xb)).numpy()
        y_adv  = detector.predict(x_adv, verbose=0)

        preds_clean_mal.append(np.argmax(y_clean, axis=1))
        preds_adv_mal.append(np.argmax(y_adv,  axis=1))

    preds_clean_mal = np.concatenate(preds_clean_mal)
    preds_adv_mal   = np.concatenate(preds_adv_mal)

    # Recall malware limpio y adversarial
    recall_clean_mal = (preds_clean_mal == 1).mean()
    recall_adv_mal   = (preds_adv_mal   == 1).mean()

    print(f"Malware clean recall: {recall_clean_mal:.4f}")
    print(f"Malware ADV  recall: {recall_adv_mal:.4f}")
else:
    print("⚠️ No hay muestras de malware en test para evaluación adversarial.")

print("\n🏁 Listo.")
