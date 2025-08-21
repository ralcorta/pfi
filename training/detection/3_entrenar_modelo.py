import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import ConvLSTM2D, Flatten, Dense, Dropout
from tensorflow.keras.utils import Sequence
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import TimeDistributed, Conv2D, MaxPooling2D, Flatten, LSTM, Dense, Dropout
from tensorflow.keras.regularizers import l2

# Hay que usar este -> cambiar al full

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

        # Agregar ruido leve si se quiere aumentar la variabilidad
        if self.noise:
            noise_factor = 0.01
            X_batch = X_batch + noise_factor * np.random.normal(loc=0.0, scale=1.0, size=X_batch.shape)
            X_batch = np.clip(X_batch, 0.0, 1.0)

        return X_batch, y_batch

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

# ───────────────────────────────────────────────
# 1. Modelo ConvLSTM con regularización fuerte CNN+LSTM
# ───────────────────────────────────────────────
model = Sequential()
model.add(TimeDistributed(Conv2D(8, (3, 3), activation='relu', padding='same'), input_shape=(10, 32, 32, 1)))
model.add(TimeDistributed(MaxPooling2D((2, 2))))
model.add(TimeDistributed(Conv2D(16, (3, 3), activation='relu', padding='same')))
model.add(TimeDistributed(MaxPooling2D((2, 2))))
model.add(TimeDistributed(Flatten()))
model.add(LSTM(32))  # Aprende dependencias entre los 10 paquetes
model.add(Dropout(0.5))
model.add(Dense(16, activation='relu', kernel_regularizer=l2(0.01)))
model.add(Dense(2, activation='softmax'))

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# ───────────────────────────────────────────────
# 2. Generadores con shuffle
# ───────────────────────────────────────────────
train_gen = DataGenerator('X_train.npy', 'y_train.npy', shuffle=True, noise=False)
val_gen = DataGenerator('X_test.npy', 'y_test.npy', shuffle=False)

# ───────────────────────────────────────────────
# 3. Pesos balanceados por clase
# ───────────────────────────────────────────────
y_train_raw = np.load('y_train.npy')
y_labels = np.argmax(y_train_raw, axis=1)
weights = compute_class_weight(class_weight='balanced', classes=np.unique(y_labels), y=y_labels)
class_weights = dict(enumerate(weights))

# ───────────────────────────────────────────────
# 4. EarlyStopping agresivo
# ───────────────────────────────────────────────
early_stop = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True)

# ───────────────────────────────────────────────
# 5. Entrenar modelo
# ───────────────────────────────────────────────
model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=30,
    callbacks=[early_stop],
    class_weight=class_weights
)

# ───────────────────────────────────────────────
# 6. Guardar modelo
# ───────────────────────────────────────────────
model.save('convlstm_model.keras')