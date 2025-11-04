import os, json, sys
import numpy as np
from pathlib import Path
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (TimeDistributed, Conv2D, MaxPooling2D,
                                     GlobalAveragePooling2D, LSTM, Dense, Dropout, SpatialDropout2D)
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, CSVLogger
from tensorflow.keras.utils import Sequence
from sklearn.utils.class_weight import compute_class_weight

print(" INICIANDO ENTRENAMIENTO DEL MODELO DE RANSOMWARE")
print("="*70)

script_dir = Path(__file__).parent
np.random.seed(42)
tf.random.set_seed(42)

try:
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        for g in gpus: tf.config.experimental.set_memory_growth(g, True)
        print(f"GPU detectada(s): {len(gpus)} | memory growth ON")
    else:
        print("Entrenando en CPU (o GPU no detectada)")
except Exception as e:
    print(f"[WARN] No se pudo configurar memory growth: {e}")

os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")

import numbers
def to_py(o):
    import numpy as _np
    if isinstance(o, (str, bool, type(None), numbers.Number)):
        if isinstance(o, (_np.generic,)):
            return o.item()
        return o
    if isinstance(o, (list, tuple)):
        return [to_py(x) for x in o]
    if isinstance(o, dict):
        return {str(k): to_py(v) for k, v in o.items()}
    if hasattr(o, "tolist"):
        return o.tolist()
    try:
        return float(o)
    except Exception:
        return str(o)

def safe_json_dump(obj, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_py(obj), f, indent=2, ensure_ascii=False)

class DataGenerator(Sequence):
    def __init__(self, X_path, y_path, batch_size=64, shuffle=True, augment=False):
        self.X_path = Path(X_path); self.y_path = Path(y_path)
        if not self.X_path.exists() or not self.y_path.exists():
            raise FileNotFoundError(f"Faltan archivos: {self.X_path} / {self.y_path}")
        self.X = np.load(self.X_path, mmap_mode='r')
        self.y = np.load(self.y_path, mmap_mode='r')
        assert len(self.X) == len(self.y), f"X({len(self.X)}) != y({len(self.y)})"
        self.batch_size = batch_size
        self.length = self.X.shape[0]
        self.shuffle = shuffle
        self.augment = augment
        self.indices = np.arange(self.length)
        if self.shuffle: np.random.shuffle(self.indices)

    def __len__(self): return int(np.ceil(self.length / self.batch_size))

    def __getitem__(self, idx):
        ids = self.indices[idx*self.batch_size:(idx+1)*self.batch_size]
        Xb = self.X[ids].astype(np.float32, copy=True)
        yb = self.y[ids].astype(np.float32, copy=True)
        
        if self.augment and np.random.rand() < 0.7 and len(Xb) > 1:
            lam = np.random.beta(0.4, 0.4); perm = np.random.permutation(len(Xb))
            Xb = lam*Xb + (1-lam)*Xb[perm]; yb = lam*yb + (1-lam)*yb[perm]
        if self.augment: Xb = self._augment_batch(Xb)
        np.clip(Xb, 0.0, 1.0, out=Xb)
        return Xb, yb

    def on_epoch_end(self):
        if self.shuffle: np.random.shuffle(self.indices)

    def _augment_batch(self, X):
        X += 0.05 * np.random.normal(size=X.shape).astype(np.float32)
        p_byte_dropout = 0.05
        mask = (np.random.rand(*X.shape) < p_byte_dropout); X[mask] = 0.0
        if np.random.rand() < 0.7:
            B,T,_,_,_ = X.shape
            for _ in range(np.random.randint(1,3)):
                X[np.arange(B), np.random.randint(0,T)] = 0.0
        if np.random.rand() < 0.7:
            X = np.roll(X, shift=np.random.choice([-2,-1,1,2]), axis=1)
        if np.random.rand() < 0.7:
            B,T,H,W,C = X.shape
            for b in range(B):
                t = np.random.randint(0,T); h = np.random.randint(0, H-6); w = np.random.randint(0, W-6)
                hh = np.random.randint(4, 10); ww = np.random.randint(4, 10)
                X[b, t, h:h+hh, w:w+ww, :] = 0.0
        return X

print("\nCreando generadores...")
train_gen = DataGenerator(script_dir / 'X_train.npy', script_dir / 'y_train.npy',
                          batch_size=64, shuffle=True,  augment=True)
val_gen   = DataGenerator(script_dir / 'X_test.npy',  script_dir / 'y_test.npy',
                          batch_size=64, shuffle=False, augment=False)

print(f"   Train samples: {train_gen.length} | batches: {len(train_gen)}")
print(f"   Val   samples: {val_gen.length} | batches: {len(val_gen)}")

print("\nConstruyendo arquitectura...")
model = Sequential([
    TimeDistributed(Conv2D(8, (3,3), activation='relu', padding='same', kernel_regularizer=l2(3e-3)),
                    input_shape=(20,32,32,1)),
    TimeDistributed(SpatialDropout2D(0.3)),
    TimeDistributed(MaxPooling2D((2,2))),
    TimeDistributed(Conv2D(16, (3,3), activation='relu', padding='same', kernel_regularizer=l2(3e-3))),
    TimeDistributed(SpatialDropout2D(0.3)),
    TimeDistributed(MaxPooling2D((2,2))),
    TimeDistributed(GlobalAveragePooling2D()),
    LSTM(16, dropout=0.4, recurrent_dropout=0.4),
    Dropout(0.6),
    Dense(8, activation='relu', kernel_regularizer=l2(3e-3)),
    Dropout(0.6),
    Dense(2, activation='softmax')
])

loss = tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1)
optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3, clipnorm=1.0)
model.compile(optimizer=optimizer, loss=loss, metrics=['accuracy'])

print("\nResumen del modelo:")
model.summary()

y_train_raw = np.load(script_dir / 'y_train.npy')
y_labels = np.argmax(y_train_raw, axis=1)
class_counts = np.bincount(y_labels, minlength=2)
weights = compute_class_weight(class_weight='balanced', classes=np.arange(2), y=y_labels)
class_weights = dict(enumerate(weights))
print("\nPesos de clase:", class_weights, "| distrib:", class_counts.tolist())

early_stop = EarlyStopping(monitor='val_loss', patience=2, min_delta=1e-3,
                           restore_best_weights=True, verbose=1)
reduce_lr  = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=1,
                               min_lr=1e-5, verbose=1)
chkpt = ModelCheckpoint(filepath=str(script_dir / 'convlstm_model_best.keras'),
                        monitor='val_loss', save_best_only=True, verbose=1)
csvlog = CSVLogger(str(script_dir / 'training_log.csv'))

EPOCHS = 30
print("\nINICIANDO ENTRENAMIENTO")
print("="*70)
print(f"Épocas: {EPOCHS} | Batch: {train_gen.batch_size}")

try:
    history = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=EPOCHS,
        callbacks=[early_stop, reduce_lr, chkpt, csvlog],
        class_weight=class_weights,
        verbose=1
    )

    safe_json_dump(history.history, script_dir / 'history.json')

    summary = {
        "epochs_trained": len(history.history.get('loss', [])),
        "final": {
            "loss": history.history['loss'][-1],
            "val_loss": history.history['val_loss'][-1],
            "accuracy": history.history['accuracy'][-1],
            "val_accuracy": history.history['val_accuracy'][-1]
        },
        "class_counts_train": class_counts.tolist(),
        "class_weights": {int(k): float(v) for k, v in class_weights.items()},
        "optimizer": "Adam(1e-3, clipnorm=1.0)",
        "loss": "CategoricalCrossentropy(label_smoothing=0.1)",
        "callbacks": ["EarlyStopping(p=2)", "ReduceLROnPlateau(f=0.5,p=1)", "ModelCheckpoint(best)", "CSVLogger"],
        "input_shape": [20, 32, 32, 1]
    }
    safe_json_dump(summary, script_dir / 'training_summary.json')

    print("\nENTRENAMIENTO COMPLETADO")

except KeyboardInterrupt:
    print("\nENTRENAMIENTO INTERRUMPIDO POR EL USUARIO")
    model.save(script_dir / 'convlstm_model_interrupted.keras')
    print("  - Guardado: convlstm_model_interrupted.keras")
    sys.exit(0)

except Exception as e:
    print(f"\nERROR DURANTE EL ENTRENAMIENTO: {e}")
    try:
        model.save(script_dir / 'convlstm_model_error.keras')
        print("   - Modelo parcial guardado como: convlstm_model_error.keras")
    except Exception as ee:
        print(f"   - No se pudo guardar el modelo parcial: {ee}")
    raise

print("\nGuardando modelo final...")
model.save(script_dir / 'convlstm_model.keras')
print("  - convlstm_model.keras")
print("  - convlstm_model_best.keras (mejor val_loss durante el training)")

print("\n PROCESO COMPLETADO")
print("="*70)
print(" Archivos generados:")
print("   - convlstm_model.keras")
print("   - convlstm_model_best.keras")
print("   - history.json")
print("   - training_summary.json")
print("   - training_log.csv")