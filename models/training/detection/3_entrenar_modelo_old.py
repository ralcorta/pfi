import numpy as np
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import (
    TimeDistributed, Conv2D, MaxPooling2D, Flatten, LSTM, Dense, Dropout,
    Input, Concatenate, BatchNormalization, GlobalAveragePooling2D
)
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.utils import Sequence
from sklearn.utils.class_weight import compute_class_weight
import joblib
import sys
from pathlib import Path

# ───────────────────────────────────────────────
# 1. DataGenerator mejorado para ransomware
# ───────────────────────────────────────────────
class RansomwareDataGenerator(Sequence):
    def __init__(self, X_path, y_path, X_ransomware_path, batch_size=32, shuffle=True, noise=False):
        self.X = np.load(X_path, mmap_mode='r')
        self.y = np.load(y_path, mmap_mode='r')
        self.X_ransomware = np.load(X_ransomware_path, mmap_mode='r')
        self.batch_size = batch_size
        self.length = self.X.shape[0]
        self.shuffle = shuffle
        self.noise = noise
        self.indices = np.arange(self.length)
        if self.shuffle:
            np.random.shuffle(self.indices)

    def __len__(self):
        return int(np.ceil(self.length / self.batch_size))

    def __getitem__(self, idx):
        indices = self.indices[idx * self.batch_size:(idx + 1) * self.batch_size]
        X_batch = self.X[indices]
        y_batch = self.y[indices]
        X_ransomware_batch = self.X_ransomware[indices]

        # Agregar ruido leve para data augmentation
        if self.noise:
            noise_factor = 0.01
            X_batch = X_batch + noise_factor * np.random.normal(loc=0.0, scale=1.0, size=X_batch.shape)
            X_batch = np.clip(X_batch, 0.0, 1.0)

        return [X_batch, X_ransomware_batch], y_batch

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

# ───────────────────────────────────────────────
# 2. Arquitectura híbrida CNN+LSTM+Features
# ───────────────────────────────────────────────
def create_ransomware_model(sequence_length=20, payload_shape=(32, 32, 1), ransomware_features=10):
    """
    Modelo híbrido para detección de ransomware:
    - CNN para extraer patrones espaciales de payloads
    - LSTM para capturar dependencias temporales
    - Dense layers para features específicas de ransomware
    """
    
    # Input para secuencias de payload
    payload_input = Input(shape=(sequence_length,) + payload_shape, name='payload_input')
    
    # CNN para extraer features espaciales de cada frame
    cnn_branch = TimeDistributed(Conv2D(16, (3, 3), activation='relu', padding='same'))(payload_input)
    cnn_branch = TimeDistributed(BatchNormalization())(cnn_branch)
    cnn_branch = TimeDistributed(MaxPooling2D((2, 2)))(cnn_branch)
    
    cnn_branch = TimeDistributed(Conv2D(32, (3, 3), activation='relu', padding='same'))(cnn_branch)
    cnn_branch = TimeDistributed(BatchNormalization())(cnn_branch)
    cnn_branch = TimeDistributed(MaxPooling2D((2, 2)))(cnn_branch)
    
    cnn_branch = TimeDistributed(Conv2D(64, (3, 3), activation='relu', padding='same'))(cnn_branch)
    cnn_branch = TimeDistributed(BatchNormalization())(cnn_branch)
    cnn_branch = TimeDistributed(GlobalAveragePooling2D())(cnn_branch)
    
    # LSTM para dependencias temporales
    lstm_branch = LSTM(64, return_sequences=True, dropout=0.3, recurrent_dropout=0.3)(cnn_branch)
    lstm_branch = LSTM(32, dropout=0.3, recurrent_dropout=0.3)(lstm_branch)
    
    # Input para features específicas de ransomware
    ransomware_input = Input(shape=(ransomware_features,), name='ransomware_features_input')
    
    # Dense layers para features de ransomware
    ransomware_branch = Dense(32, activation='relu', kernel_regularizer=l2(0.01))(ransomware_input)
    ransomware_branch = BatchNormalization()(ransomware_branch)
    ransomware_branch = Dropout(0.5)(ransomware_branch)
    
    ransomware_branch = Dense(16, activation='relu', kernel_regularizer=l2(0.01))(ransomware_branch)
    ransomware_branch = Dropout(0.3)(ransomware_branch)
    
    # Concatenar ambas ramas
    combined = Concatenate()([lstm_branch, ransomware_branch])
    
    # Capas finales
    combined = Dense(64, activation='relu', kernel_regularizer=l2(0.01))(combined)
    combined = BatchNormalization()(combined)
    combined = Dropout(0.5)(combined)
    
    combined = Dense(32, activation='relu', kernel_regularizer=l2(0.01))(combined)
    combined = Dropout(0.3)(combined)
    
    # Salida
    output = Dense(2, activation='softmax', name='output')(combined)
    
    # Crear modelo
    model = Model(inputs=[payload_input, ransomware_input], outputs=output)
    
    return model

# ───────────────────────────────────────────────
# 3. Configuración y entrenamiento
# ───────────────────────────────────────────────
print("🚀 Iniciando entrenamiento del modelo de ransomware...")

# Crear modelo
model = create_ransomware_model(sequence_length=20, payload_shape=(32, 32, 1), ransomware_features=13)
model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

print("📊 Arquitectura del modelo:")
model.summary()

# ───────────────────────────────────────────────
# 4. Generadores de datos
# ───────────────────────────────────────────────
print("📦 Configurando generadores de datos...")
print("   🔄 Creando generador de entrenamiento...")
train_gen = RansomwareDataGenerator(
    Path(__file__).parent / 'X_train.npy', 
    Path(__file__).parent / 'y_train.npy', 
    Path(__file__).parent / 'X_ransomware_train.npy',
    batch_size=32, shuffle=True, noise=True
)
print(f"   ✅ Generador de entrenamiento creado: {len(train_gen)} batches")

print("   🔄 Creando generador de validación...")
val_gen = RansomwareDataGenerator(
    Path(__file__).parent / 'X_test.npy', 
    Path(__file__).parent / 'y_test.npy', 
    Path(__file__).parent / 'X_ransomware_test.npy',
    batch_size=32, shuffle=False, noise=False
)
print(f"   ✅ Generador de validación creado: {len(val_gen)} batches")

# ───────────────────────────────────────────────
# 5. Pesos balanceados por clase
# ───────────────────────────────────────────────
print("⚖️ Calculando pesos de clase...")
y_train_raw = np.load(Path(__file__).parent / 'y_train.npy')
y_labels = np.argmax(y_train_raw, axis=1)
weights = compute_class_weight(class_weight='balanced', classes=np.unique(y_labels), y=y_labels)
class_weights = dict(enumerate(weights))
print(f"   📊 Pesos de clase calculados: {class_weights}")

# ───────────────────────────────────────────────
# 6. Callbacks
# ───────────────────────────────────────────────
print("🔧 Configurando callbacks...")
callbacks = [
    EarlyStopping(
        monitor='val_loss',
        patience=5,
        restore_best_weights=True,
        verbose=1
    ),
    ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=3,
        min_lr=1e-7,
        verbose=1
    ),
    ModelCheckpoint(
        'convlstm_model_ransomware_final.keras',
        monitor='val_loss',
        save_best_only=True,
        verbose=1
    )
]
print("   ✅ Callbacks configurados:")
print("      - EarlyStopping (patience=5)")
print("      - ReduceLROnPlateau (patience=3)")
print("      - ModelCheckpoint (save_best_only)")

# ───────────────────────────────────────────────
# 7. Entrenar modelo
# ───────────────────────────────────────────────
print("🏋️ Iniciando entrenamiento...")
print("   📊 Configuración del entrenamiento:")
print(f"      - Épocas: 50")
print(f"      - Batch size: 32")
print(f"      - Train batches: {len(train_gen)}")
print(f"      - Validation batches: {len(val_gen)}")
print(f"      - Total train samples: {train_gen.length}")
print(f"      - Total validation samples: {val_gen.length}")
print("   🚀 Comenzando entrenamiento...")

try:
    history = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=50,
        callbacks=callbacks,
        class_weight=class_weights,
        verbose=1
    )
    
    print("✅ Entrenamiento completado exitosamente!")
    print("   📈 Historial de entrenamiento guardado")
    
except KeyboardInterrupt:
    print("⏹️ Entrenamiento interrumpido por el usuario")
    print("   💾 Guardando modelo actual...")
    model.save('convlstm_model_ransomware_interrupted.keras')
    print("   ✅ Modelo guardado como: convlstm_model_ransomware_interrupted.keras")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Error durante el entrenamiento: {e}")
    print("    Intentando guardar modelo parcial...")
    try:
        model.save('convlstm_model_ransomware_error.keras')
        print("   ✅ Modelo parcial guardado como: convlstm_model_ransomware_error.keras")
    except:
        print("   ❌ No se pudo guardar el modelo parcial")
    raise

# ───────────────────────────────────────────────
# 8. Guardar resultados
# ───────────────────────────────────────────────
print("💾 Guardando resultados...")
print("   🔄 Guardando historial de entrenamiento...")
np.save('training_history.npy', history.history)
print("   ✅ Historial guardado como: training_history.npy")

print("   🔄 Guardando modelo final...")
model.save('convlstm_model_ransomware_final.keras')
print("   ✅ Modelo final guardado como: convlstm_model_ransomware_final.keras")

# ───────────────────────────────────────────────
# 9. Resumen final
# ───────────────────────────────────────────────
print("\n ENTRENAMIENTO COMPLETADO")
print("="*50)
print(" Resumen del entrenamiento:")
print(f"   - Épocas entrenadas: {len(history.history['loss'])}")
print(f"   - Loss final: {history.history['loss'][-1]:.4f}")
print(f"   - Val loss final: {history.history['val_loss'][-1]:.4f}")
print(f"   - Accuracy final: {history.history['accuracy'][-1]:.4f}")
print(f"   - Val accuracy final: {history.history['val_accuracy'][-1]:.4f}")

print("\n Archivos generados:")
print("   - convlstm_model_ransomware_final.keras (modelo entrenado)")
print("   - training_history.npy (historial de entrenamiento)")

print("\n🎯 El modelo está listo para detectar ransomware!")
print(" Próximo paso: Ejecutar evaluación del modelo")