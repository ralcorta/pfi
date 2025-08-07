import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import ConvLSTM2D, Flatten, Dense, Dropout
from tensorflow.keras.utils import Sequence
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.utils.class_weight import compute_class_weight

# ───────────────────────────────────────────────
# 1. Combinar datos reales + adversarios
# ───────────────────────────────────────────────
X_train = np.load('X_train.npy')
y_train = np.load('y_train.npy')

X_adv = np.load('X_adv.npy')
y_adv = np.load('y_adv.npy')

print(f"Original: {X_train.shape}, Adversarios: {X_adv.shape}")

# Concatenar y mezclar
X_combined = np.concatenate([X_train, X_adv], axis=0)
y_combined = np.concatenate([y_train, y_adv], axis=0)

indices = np.arange(X_combined.shape[0])
np.random.shuffle(indices)

X_combined = X_combined[indices]
y_combined = y_combined[indices]

# Guardar por si querés reutilizar
np.save('X_train_adv.npy', X_combined)
np.save('y_train_adv.npy', y_combined)

print("✅ Dataset combinado guardado como X_train_adv.npy y y_train_adv.npy")

# ───────────────────────────────────────────────
# 2. Definir DataGenerator
# ───────────────────────────────────────────────
class DataGenerator(Sequence):
    def __init__(self, X_path, y_path, batch_size=32, shuffle=True, noise=False):
        self.X = np.load(X_path, mmap_mode='r')
        self.y = np.load(y_path, mmap_mode='r')
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

        if self.noise:
            noise_factor = 0.01
            X_batch = X_batch + noise_factor * np.random.normal(loc=0.0, scale=1.0, size=X_batch.shape)
            X_batch = np.clip(X_batch, 0.0, 1.0)

        return X_batch, y_batch

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

# ───────────────────────────────────────────────
# 3. Definir modelo
# ───────────────────────────────────────────────
model = Sequential()
model.add(ConvLSTM2D(
    filters=2,
    kernel_size=(3, 3),
    activation='relu',
    input_shape=(10, 32, 32, 1),
    kernel_regularizer=l2(0.01)
))
model.add(Dropout(0.6))
model.add(Flatten())
model.add(Dense(4, activation='relu', kernel_regularizer=l2(0.02)))
model.add(Dropout(0.6))
model.add(Dense(2, activation='softmax'))

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# ───────────────────────────────────────────────
# 4. Generadores
# ───────────────────────────────────────────────
train_gen = DataGenerator('X_train_adv.npy', 'y_train_adv.npy', shuffle=True, noise=False)
val_gen = DataGenerator('X_test.npy', 'y_test.npy', shuffle=False)

# ───────────────────────────────────────────────
# 5. Pesos balanceados
# ───────────────────────────────────────────────
y_labels = np.argmax(y_combined, axis=1)
weights = compute_class_weight(class_weight='balanced', classes=np.unique(y_labels), y=y_labels)
class_weights = dict(enumerate(weights))

# ───────────────────────────────────────────────
# 6. EarlyStopping y entrenamiento
# ───────────────────────────────────────────────
early_stop = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True)

model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=30,
    callbacks=[early_stop],
    class_weight=class_weights
)

# ───────────────────────────────────────────────
# 7. Guardar modelo entrenado con adversarial training
# ───────────────────────────────────────────────
model.save('convlstm_model_adversarial.keras')
print("✅ Modelo con entrenamiento adversarial guardado como convlstm_model_adversarial.keras")