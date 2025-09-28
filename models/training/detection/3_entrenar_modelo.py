import numpy as np
import tensorflow as tf
from tensorflow.keras import Input, Model
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (
    TimeDistributed, Conv2D, MaxPooling2D, GlobalAveragePooling2D,
    LSTM, Dense, Dropout, SpatialDropout2D, Concatenate
)
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.utils import Sequence
from sklearn.utils.class_weight import compute_class_weight
import sys
from pathlib import Path

print(" INICIANDO ENTRENAMIENTO DEL MODELO DE RANSOMWARE (dual-input ready)")
print("="*72)

# ──────────────────────────────────────────────────────────────────────────────
# Paths / reproducibilidad
# ──────────────────────────────────────────────────────────────────────────────
script_dir = Path(__file__).parent
print(f"📁 Directorio del script: {script_dir}")

np.random.seed(42)
tf.random.set_seed(42)
print("🔧 Semillas fijadas (numpy=42, tensorflow=42)")

# ──────────────────────────────────────────────────────────────────────────────
# Detectar si existen features tabulares (X_ransomware_train/test.npy)
# ──────────────────────────────────────────────────────────────────────────────
feat_train_path = script_dir / 'X_ransomware_train.npy'
feat_test_path  = script_dir / 'X_ransomware_test.npy'
USE_FEATURES = feat_train_path.exists() and feat_test_path.exists()

if USE_FEATURES:
    tmp_feats = np.load(feat_train_path, mmap_mode='r')
    F = tmp_feats.shape[1]
    del tmp_feats
    print(f"🧩 Features tabulares detectadas: F={F} (se usarán en el entrenamiento)")
else:
    F = 0
    print("ℹ️ No se detectaron 'X_ransomware_*'. Entrenamiento solo con payloads.")

# ──────────────────────────────────────────────────────────────────────────────
# DataGenerator: payload + (opc) features; aug solo sobre payload
# ──────────────────────────────────────────────────────────────────────────────
print("\n📦 Configurando DataGenerator...")
class DataGenerator(Sequence):
    def __init__(self, X_path, y_path, X_feat_path=None, batch_size=64, shuffle=True, augment=False):
        print(f"   Inicializando generador: {Path(X_path).name}")
        self.X = np.load(X_path, mmap_mode='r')                 # (N, T, 32, 32, 1)
        self.y = np.load(y_path, mmap_mode='r')                 # (N, 2)
        self.use_features = X_feat_path is not None and Path(X_feat_path).exists()
        self.Xf = np.load(X_feat_path, mmap_mode='r') if self.use_features else None  # (N, F)
        self.batch_size = batch_size
        self.length = self.X.shape[0]
        self.shuffle = shuffle
        self.augment = augment
        self.indices = np.arange(self.length)
        if self.shuffle:
            np.random.shuffle(self.indices)
        print(f"   ✅ Generador: {self.length} muestras | batches/epoch={self.__len__()} | features={self.use_features}")

    def __len__(self):
        return int(np.ceil(self.length / self.batch_size))

    def __getitem__(self, idx):
        ids = self.indices[idx*self.batch_size:(idx+1)*self.batch_size]
        Xb = self.X[ids].astype(np.float32, copy=True)   # (B,T,32,32,1)
        yb = self.y[ids].astype(np.float32, copy=True)

        # MixUp a nivel secuencia (solo payload)
        if self.augment and np.random.rand() < 0.7 and len(Xb) > 1:
            lam = np.random.beta(0.4, 0.4)
            perm = np.random.permutation(len(Xb))
            Xb = lam*Xb + (1-lam)*Xb[perm]
            yb = lam*yb + (1-lam)*yb[perm]

        # Augment solo sobre payloads
        if self.augment:
            Xb = self._augment_batch(Xb)

        if self.use_features:
            Fb = self.Xf[ids].astype(np.float32, copy=False)  # (B,F) — no se altera con aug
            # **Cambio importante**: devolver una TUPLA de inputs
            return (Xb, Fb), yb
        else:
            return Xb, yb

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

    def _augment_batch(self, X):
        X += 0.05 * np.random.normal(size=X.shape).astype(np.float32)  # ruido
        p_byte_dropout = 0.05
        mask = (np.random.rand(*X.shape) < p_byte_dropout)
        X[mask] = 0.0
        if np.random.rand() < 0.7:
            B,T,H,W,C = X.shape
            for _ in range(np.random.randint(1,3)):
                X[np.arange(B), np.random.randint(0,T)] = 0.0
        if np.random.rand() < 0.7:
            shift = np.random.choice([-2,-1,1,2])
            X = np.roll(X, shift=shift, axis=1)
        if np.random.rand() < 0.7:
            B,T,H,W,C = X.shape
            for b in range(B):
                t = np.random.randint(0,T)
                h = np.random.randint(0, H-6)
                w = np.random.randint(0, W-6)
                hh = np.random.randint(4, 10)
                ww = np.random.randint(4, 10)
                X[b, t, h:h+hh, w:w+ww, :] = 0.0
        np.clip(X, 0.0, 1.0, out=X)
        return X

# ──────────────────────────────────────────────────────────────────────────────
# Arquitectura: payload branch (+ features branch si aplica) → late fusion
# ──────────────────────────────────────────────────────────────────────────────
print("\n🏗️ Construyendo arquitectura del modelo...")
T, H, W, C = 20, 32, 32, 1

if USE_FEATURES:
    payload_in = Input(shape=(T,H,W,C), name='payload_input')
    x = TimeDistributed(Conv2D(8, (3,3), activation='relu', padding='same',
                               kernel_regularizer=l2(3e-3)))(payload_in)
    x = TimeDistributed(SpatialDropout2D(0.3))(x)
    x = TimeDistributed(MaxPooling2D((2,2)))(x)
    x = TimeDistributed(Conv2D(16, (3,3), activation='relu', padding='same',
                               kernel_regularizer=l2(3e-3)))(x)
    x = TimeDistributed(SpatialDropout2D(0.3))(x)
    x = TimeDistributed(MaxPooling2D((2,2)))(x)
    x = TimeDistributed(GlobalAveragePooling2D())(x)      # -> (B,T,C')
    x = LSTM(16, dropout=0.4, recurrent_dropout=0.4)(x)   # -> (B,16)

    feat_in = Input(shape=(F,), name='ransomware_features_input')

    h = Concatenate(axis=1)([x, feat_in])                 # -> (B, 16+F)
    h = Dropout(0.6)(h)
    h = Dense(8, activation='relu', kernel_regularizer=l2(3e-3))(h)
    h = Dropout(0.6)(h)
    out = Dense(2, activation='softmax')(h)

    model = Model(inputs=[payload_in, feat_in], outputs=out, name='convLSTM_plus_features')
else:
    model = Sequential([
        TimeDistributed(Conv2D(8, (3,3), activation='relu', padding='same',
                               kernel_regularizer=l2(3e-3)), input_shape=(T,32,32,1)),
        TimeDistributed(SpatialDropout2D(0.3)),
        TimeDistributed(MaxPooling2D((2,2))),
        TimeDistributed(Conv2D(16, (3,3), activation='relu', padding='same',
                               kernel_regularizer=l2(3e-3))),
        TimeDistributed(SpatialDropout2D(0.3)),
        TimeDistributed(MaxPooling2D((2,2))),
        TimeDistributed(GlobalAveragePooling2D()),
        LSTM(16, dropout=0.4, recurrent_dropout=0.4),
        Dropout(0.6),
        Dense(8, activation='relu', kernel_regularizer=l2(3e-3)),
        Dropout(0.6),
        Dense(2, activation='softmax')
    ])

print("   ✅ Modelo creado")
print("\n📊 Resumen de la arquitectura:")
model.summary(line_length=120)

# ──────────────────────────────────────────────────────────────────────────────
# Compilación y generadores
# ──────────────────────────────────────────────────────────────────────────────
loss = tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1)
model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
              loss=loss, metrics=['accuracy'])
print("\n⚙️ Compilado: Adam(lr=1e-3) + CCE(ls=0.1) + accuracy")

print("\n📦 Creando generadores...")
train_gen = DataGenerator(
    script_dir / 'X_train.npy',
    script_dir / 'y_train.npy',
    X_feat_path=(feat_train_path if USE_FEATURES else None),
    batch_size=64, shuffle=True, augment=True
)
val_gen = DataGenerator(
    script_dir / 'X_test.npy',
    script_dir / 'y_test.npy',
    X_feat_path=(feat_test_path if USE_FEATURES else None),
    batch_size=64, shuffle=False, augment=False
)

# ──────────────────────────────────────────────────────────────────────────────
# Pesos por clase y callbacks
# ──────────────────────────────────────────────────────────────────────────────
print("\n⚖️ Calculando pesos de clase…")
y_train_raw = np.load(script_dir / 'y_train.npy')
y_labels = np.argmax(y_train_raw, axis=1)
print(f"   Distribución de clases: {np.bincount(y_labels)}")
weights = compute_class_weight(class_weight='balanced', classes=np.unique(y_labels), y=y_labels)
class_weights = dict(enumerate(weights))
print(f"   Pesos: {class_weights}")

print("\n🔧 Configurando callbacks…")
early_stop = EarlyStopping(monitor='val_loss', patience=2, min_delta=1e-3, restore_best_weights=True)
reduce_lr  = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=1, min_lr=1e-5, verbose=1)

# ──────────────────────────────────────────────────────────────────────────────
# Entrenamiento
# ──────────────────────────────────────────────────────────────────────────────
print("\n🏋️ INICIANDO ENTRENAMIENTO")
print("="*72)
print(f"   - Épocas: 30")
print(f"   - Batch size: 64")
print(f"   - Train batches: {len(train_gen)}")
print(f"   - Val batches:   {len(val_gen)}")
print(f"   - Inputs: {'payload + features' if USE_FEATURES else 'payload solo'}")
print("="*72)

try:
    history = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=30,
        callbacks=[early_stop, reduce_lr],
        class_weight=class_weights,
        verbose=1
    )
    print("\n✅ ENTRENAMIENTO COMPLETADO")
    print(f"   Épocas reales: {len(history.history['loss'])}")
    print(f"   Loss final:    {history.history['loss'][-1]:.4f}")
    print(f"   Val loss:      {history.history['val_loss'][-1]:.4f}")
    print(f"   Acc final:     {history.history['accuracy'][-1]:.4f}")
    print(f"   Val acc:       {history.history['val_accuracy'][-1]:.4f}")

except KeyboardInterrupt:
    print("\n⏹️ Interrumpido por usuario. Guardando modelo parcial…")
    model.save(script_dir / 'convlstm_model_interrupted.keras')
    print("   ✅ Guardado: convlstm_model_interrupted.keras")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ ERROR DURANTE EL ENTRENAMIENTO: {e}")
    print("   Intentando guardar modelo parcial…")
    try:
        model.save(script_dir / 'convlstm_model_error.keras')
        print("   ✅ Guardado: convlstm_model_error.keras")
    except:
        print("   ❌ No se pudo guardar el modelo parcial")
    raise

# ──────────────────────────────────────────────────────────────────────────────
# Guardado final
# ──────────────────────────────────────────────────────────────────────────────
print("\n💾 Guardando modelo final…")
model.save(script_dir / 'convlstm_model.keras')
print("   ✅ Modelo guardado como: convlstm_model.keras")

print("\n PROCESO COMPLETADO")
print("="*72)
print(" Archivos generados:")
print("   - convlstm_model.keras (modelo entrenado)")
print(f"   - Entrenamiento con: {'payload + features' if USE_FEATURES else 'solo payload'}")
