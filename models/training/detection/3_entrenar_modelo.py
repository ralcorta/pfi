import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (TimeDistributed, Conv2D, MaxPooling2D,
                                     GlobalAveragePooling2D, LSTM, Dense, Dropout, SpatialDropout2D)
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.utils import Sequence
from sklearn.utils.class_weight import compute_class_weight
import sys
from pathlib import Path

print(" INICIANDO ENTRENAMIENTO DEL MODELO DE RANSOMWARE")
print("="*60)

# Obtener el directorio del script actual
script_dir = Path(__file__).parent
print(f"📁 Directorio del script: {script_dir}")

# Reproducibilidad básica
print("🔧 Configurando semillas para reproducibilidad...")
np.random.seed(42)
tf.random.set_seed(42)
print("   ✅ Semillas configuradas (numpy=42, tensorflow=42)")

# -----------------------------
# DataGenerator con MixUp + Aug
# -----------------------------
print("\n📦 Configurando DataGenerator...")
class DataGenerator(Sequence):
    def __init__(self, X_path, y_path, batch_size=64, shuffle=True, augment=False):
        print(f"   Inicializando generador: {X_path}")
        self.X = np.load(X_path, mmap_mode='r')
        self.y = np.load(y_path, mmap_mode='r')
        self.batch_size = batch_size
        self.length = self.X.shape[0]
        self.shuffle = shuffle
        self.augment = augment
        self.indices = np.arange(self.length)
        if self.shuffle:
            np.random.shuffle(self.indices)
        print(f"   ✅ Generador creado: {self.length} muestras, {self.__len__()} batches")

    def __len__(self):
        return int(np.ceil(self.length / self.batch_size))

    def __getitem__(self, idx):
        ids = self.indices[idx*self.batch_size:(idx+1)*self.batch_size]
        Xb = self.X[ids].astype(np.float32, copy=True)  # (B,20,32,32,1) - Cambiar de 10 a 20
        yb = self.y[ids].astype(np.float32, copy=True)

        # MixUp a nivel secuencia
        if self.augment and np.random.rand() < 0.7 and len(Xb) > 1:
            lam = np.random.beta(0.4, 0.4)
            perm = np.random.permutation(len(Xb))
            Xb = lam*Xb + (1-lam)*Xb[perm]
            yb = lam*yb + (1-lam)*yb[perm]

        if self.augment:
            Xb = self._augment_batch(Xb)

        return Xb, yb

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

    def _augment_batch(self, X):
        # Ruido gaussiano
        X += 0.05 * np.random.normal(size=X.shape).astype(np.float32)

        # Byte dropout
        p_byte_dropout = 0.05
        mask = (np.random.rand(*X.shape) < p_byte_dropout)
        X[mask] = 0.0

        # Packet dropout (1–2 pasos)
        if np.random.rand() < 0.7:
            B,T,H,W,C = X.shape
            for _ in range(np.random.randint(1,3)):
                X[np.arange(B), np.random.randint(0,T)] = 0.0

        # Temporal shift +-1 o +-2
        if np.random.rand() < 0.7:
            shift = np.random.choice([-2,-1,1,2])
            X = np.roll(X, shift=shift, axis=1)

        # Cutout en un frame
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

# -----------------------------
# Modelo con GAP + regularización
# -----------------------------
print("\n🏗️ Construyendo arquitectura del modelo...")
print("   🔄 Creando capas del modelo...")

model = Sequential([
    TimeDistributed(Conv2D(8, (3,3), activation='relu', padding='same',
                           kernel_regularizer=l2(3e-3)), input_shape=(20,32,32,1)),  # Cambiar de 10 a 20
    TimeDistributed(SpatialDropout2D(0.3)),
    TimeDistributed(MaxPooling2D((2,2))),

    TimeDistributed(Conv2D(16, (3,3), activation='relu', padding='same',
                           kernel_regularizer=l2(3e-3))),
    TimeDistributed(SpatialDropout2D(0.3)),
    TimeDistributed(MaxPooling2D((2,2))),

    # Menos parámetros que Flatten
    TimeDistributed(GlobalAveragePooling2D()),

    LSTM(16, dropout=0.4, recurrent_dropout=0.4),
    Dropout(0.6),
    Dense(8, activation='relu', kernel_regularizer=l2(3e-3)),
    Dropout(0.6),
    Dense(2, activation='softmax')
])

print("   ✅ Modelo creado exitosamente")

print("\n📊 Arquitectura del modelo:")
model.summary()

print("\n⚙️ Configurando optimizador y función de pérdida...")
loss = tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1)
print("   ✅ Función de pérdida: CategoricalCrossentropy con label_smoothing=0.1")

model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
              loss=loss, metrics=['accuracy'])
print("   ✅ Optimizador: Adam con learning_rate=1e-3")
print("   ✅ Métricas: accuracy")

# -----------------------------
# Generadores
# -----------------------------
print("\n📦 Creando generadores de datos...")
print("   🔄 Creando generador de entrenamiento...")
train_gen = DataGenerator(
    script_dir / 'X_train.npy', 
    script_dir / 'y_train.npy', 
    batch_size=64, shuffle=True, augment=True
)

print("   🔄 Creando generador de validación...")
val_gen = DataGenerator(
    script_dir / 'X_test.npy', 
    script_dir / 'y_test.npy', 
    batch_size=64, shuffle=False, augment=False
)

# -----------------------------
# Pesos por clase
# -----------------------------
print("\n⚖️ Calculando pesos de clase...")
print("   Cargando etiquetas de entrenamiento...")
y_train_raw = np.load(script_dir / 'y_train.npy')
y_labels = np.argmax(y_train_raw, axis=1)
print(f"   📊 Distribución de clases: {np.bincount(y_labels)}")

weights = compute_class_weight(class_weight='balanced', classes=np.unique(y_labels), y=y_labels)
class_weights = dict(enumerate(weights))
print(f"   ✅ Pesos de clase calculados: {class_weights}")

# -----------------------------
# Callbacks
# -----------------------------
print("\n🔧 Configurando callbacks...")
early_stop = EarlyStopping(monitor='val_loss',
                           patience=2,
                           min_delta=1e-3,
                           restore_best_weights=True)
print("   ✅ EarlyStopping: patience=2, min_delta=1e-3")

reduce_lr = ReduceLROnPlateau(monitor='val_loss',
                               factor=0.5, patience=1,
                               min_lr=1e-5, verbose=1)
print("   ✅ ReduceLROnPlateau: factor=0.5, patience=1")

# -----------------------------
# Entrenamiento
# -----------------------------
print("\n🏋️ INICIANDO ENTRENAMIENTO")
print("="*60)
print("📊 Configuración del entrenamiento:")
print(f"   - Épocas máximas: 30")
print(f"   - Batch size: 64")
print(f"   - Train batches: {len(train_gen)}")
print(f"   - Validation batches: {len(val_gen)}")
print(f"   - Total train samples: {train_gen.length}")
print(f"   - Total validation samples: {val_gen.length}")
print(f"   - Data augmentation: {'Activado' if train_gen.augment else 'Desactivado'}")
print("="*60)

try:
    print("🚀 Comenzando entrenamiento...")
    history = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=30,
        callbacks=[early_stop, reduce_lr],
        class_weight=class_weights,
        verbose=1
    )
    
    print("\n✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE!")
    print("="*60)
    print(" Resumen del entrenamiento:")
    print(f"   - Épocas entrenadas: {len(history.history['loss'])}")
    print(f"   - Loss final: {history.history['loss'][-1]:.4f}")
    print(f"   - Val loss final: {history.history['val_loss'][-1]:.4f}")
    print(f"   - Accuracy final: {history.history['accuracy'][-1]:.4f}")
    print(f"   - Val accuracy final: {history.history['val_accuracy'][-1]:.4f}")
    
except KeyboardInterrupt:
    print("\n⏹️ ENTRENAMIENTO INTERRUMPIDO POR EL USUARIO")
    print("   💾 Guardando modelo actual...")
    model.save(script_dir / 'convlstm_model_interrupted.keras')
    print("   ✅ Modelo guardado como: convlstm_model_interrupted.keras")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ ERROR DURANTE EL ENTRENAMIENTO: {e}")
    print("   Intentando guardar modelo parcial...")
    try:
        model.save(script_dir / 'convlstm_model_error.keras')
        print("   ✅ Modelo parcial guardado como: convlstm_model_error.keras")
    except:
        print("   ❌ No se pudo guardar el modelo parcial")
    raise

# -----------------------------
# Guardar modelo
# -----------------------------
print("\n💾 Guardando modelo final...")
model.save(script_dir / 'convlstm_model.keras')
print("   ✅ Modelo guardado como: convlstm_model.keras")

print("\n PROCESO COMPLETADO")
print("="*60)
print(" Archivos generados:")
print("   - convlstm_model.keras (modelo entrenado)")
print("\n🎯 El modelo está listo para detectar ransomware!")
print(" Próximo paso: Ejecutar evaluación del modelo")