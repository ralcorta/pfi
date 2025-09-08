#!/usr/bin/env python3
"""
Script de prueba rápida para el modelo de ransomware
Usa el dataset pequeño para entrenamiento rápido
"""

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

# ───────────────────────────────────────────────
# 1. DataGenerator simplificado
# ───────────────────────────────────────────────
class QuickDataGenerator(Sequence):
    def __init__(self, X_path, y_path, X_ransomware_path, batch_size=16, shuffle=True):
        self.X = np.load(X_path, mmap_mode='r')
        self.y = np.load(y_path, mmap_mode='r')
        self.X_ransomware = np.load(X_ransomware_path, mmap_mode='r')
        self.batch_size = batch_size
        self.length = min(1000, self.X.shape[0])  # Limitar a 1000 muestras para prueba rápida
        self.shuffle = shuffle
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
        return [X_batch, X_ransomware_batch], y_batch

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

# ───────────────────────────────────────────────
# 2. Modelo simplificado para prueba rápida
# ───────────────────────────────────────────────
def create_quick_model(sequence_length=20, payload_shape=(32, 32, 1), ransomware_features=10):
    """Modelo simplificado para pruebas rápidas"""
    
    # Input para secuencias de payload
    payload_input = Input(shape=(sequence_length,) + payload_shape, name='payload_input')
    
    # CNN simplificado
    cnn_branch = TimeDistributed(Conv2D(8, (3, 3), activation='relu', padding='same'))(payload_input)
    cnn_branch = TimeDistributed(MaxPooling2D((2, 2)))(cnn_branch)
    cnn_branch = TimeDistributed(Conv2D(16, (3, 3), activation='relu', padding='same'))(cnn_branch)
    cnn_branch = TimeDistributed(GlobalAveragePooling2D())(cnn_branch)
    
    # LSTM simplificado
    lstm_branch = LSTM(32, dropout=0.3)(cnn_branch)
    
    # Input para features específicas de ransomware
    ransomware_input = Input(shape=(ransomware_features,), name='ransomware_features_input')
    
    # Dense layers simplificadas
    ransomware_branch = Dense(16, activation='relu')(ransomware_input)
    ransomware_branch = Dropout(0.5)(ransomware_branch)
    
    # Concatenar ambas ramas
    combined = Concatenate()([lstm_branch, ransomware_branch])
    
    # Capas finales
    combined = Dense(32, activation='relu')(combined)
    combined = Dropout(0.3)(combined)
    
    # Salida
    output = Dense(2, activation='softmax', name='output')(combined)
    
    # Crear modelo
    model = Model(inputs=[payload_input, ransomware_input], outputs=output)
    
    return model

# ───────────────────────────────────────────────
# 3. Entrenamiento rápido
# ───────────────────────────────────────────────
print("🚀 Iniciando entrenamiento rápido del modelo de ransomware...")

# Crear modelo simplificado
model = create_quick_model(sequence_length=20, payload_shape=(32, 32, 1), ransomware_features=10)
model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

print("📊 Arquitectura del modelo simplificado:")
model.summary()

# ───────────────────────────────────────────────
# 4. Generadores de datos rápidos
# ───────────────────────────────────────────────
print("📦 Configurando generadores de datos rápidos...")
train_gen = QuickDataGenerator(
    'X_train.npy', 'y_train.npy', 'X_ransomware_train.npy',
    batch_size=16, shuffle=True
)
val_gen = QuickDataGenerator(
    'X_test.npy', 'y_test.npy', 'X_ransomware_test.npy',
    batch_size=16, shuffle=False
)

# ───────────────────────────────────────────────
# 5. Pesos balanceados por clase
# ───────────────────────────────────────────────
print("⚖️ Calculando pesos de clase...")
y_train_raw = np.load('y_train.npy')
y_labels = np.argmax(y_train_raw, axis=1)
weights = compute_class_weight(class_weight='balanced', classes=np.unique(y_labels), y=y_labels)
class_weights = dict(enumerate(weights))
print(f"Pesos de clase: {class_weights}")

# ───────────────────────────────────────────────
# 6. Callbacks simplificados
# ───────────────────────────────────────────────
callbacks = [
    EarlyStopping(
        monitor='val_loss',
        patience=3,
        restore_best_weights=True,
        verbose=1
    ),
    ModelCheckpoint(
        '../convlstm_model_ransomware_quick.keras',
        monitor='val_accuracy',
        save_best_only=True,
        verbose=1
    )
]

# ───────────────────────────────────────────────
# 7. Entrenamiento rápido (solo 10 épocas)
# ───────────────────────────────────────────────
print("🏋️ Iniciando entrenamiento rápido (10 épocas)...")
history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=10,
    callbacks=callbacks,
    class_weight=class_weights,
    verbose=1
)

# ───────────────────────────────────────────────
# 8. Guardar modelo y resultados
# ───────────────────────────────────────────────
print("💾 Guardando modelo rápido...")
model.save('../convlstm_model_ransomware_quick_final.keras')

# Guardar historial de entrenamiento
np.save('../training_history_quick.npy', history.history)

print("✅ Entrenamiento rápido completado!")
print(f"📁 Modelo guardado en: convlstm_model_ransomware_quick_final.keras")
print(f"📊 Historial guardado en: training_history_quick.npy")

# ───────────────────────────────────────────────
# 9. Evaluación rápida
# ───────────────────────────────────────────────
print("\n🔍 Evaluación rápida...")
X_test = np.load('X_test.npy')[:100]  # Solo 100 muestras para evaluación rápida
y_test = np.load('y_test.npy')[:100]
X_ransomware_test = np.load('X_ransomware_test.npy')[:100]

loss, accuracy = model.evaluate([X_test, X_ransomware_test], y_test, verbose=0)
print(f"📈 Resultados rápidos:")
print(f"  - Loss: {loss:.4f}")
print(f"  - Accuracy: {accuracy:.4f}")

# Predicciones
y_pred_proba = model.predict([X_test, X_ransomware_test], verbose=0)
y_pred = np.argmax(y_pred_proba, axis=1)
y_true = np.argmax(y_test, axis=1)

# Métricas básicas
from sklearn.metrics import classification_report
print(f"\n📊 Reporte de clasificación:")
print(classification_report(y_true, y_pred, target_names=['Benigno', 'Ransomware']))
