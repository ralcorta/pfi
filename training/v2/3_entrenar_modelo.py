import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import ConvLSTM2D, Flatten, Dense
from tensorflow.keras.utils import Sequence

# ───────────────────────────────────────────────
# 1. Data Generator que lee por lotes desde disco
# ───────────────────────────────────────────────
class DataGenerator(Sequence):
    def __init__(self, X_path, y_path, batch_size=32):
        self.X_path = X_path
        self.y_path = y_path
        self.batch_size = batch_size
        self.length = np.load(X_path, mmap_mode='r').shape[0]

    def __len__(self):
        return int(np.ceil(self.length / self.batch_size))

    def __getitem__(self, index):
        X = np.load(self.X_path, mmap_mode='r')
        y = np.load(self.y_path, mmap_mode='r')

        batch_start = index * self.batch_size
        batch_end = min((index + 1) * self.batch_size, self.length)

        return X[batch_start:batch_end], y[batch_start:batch_end]

# ───────────────────────────────────────────────
# 2. Crear el modelo ConvLSTM
# ───────────────────────────────────────────────
print("Creando modelo...")
model = Sequential()
model.add(ConvLSTM2D(filters=8, kernel_size=(3, 3), activation='relu', input_shape=(1, 32, 32, 1)))
model.add(Flatten())
model.add(Dense(16, activation='relu'))
model.add(Dense(2, activation='softmax'))

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
print("Modelo creado exitosamente!")

# ───────────────────────────────────────────────
# 3. Generadores de entrenamiento y validación
# ───────────────────────────────────────────────
train_gen = DataGenerator('X_train.npy', 'y_train.npy', batch_size=32)
val_gen = DataGenerator('X_test.npy', 'y_test.npy', batch_size=32)

# ───────────────────────────────────────────────
# 4. Entrenamiento
# ───────────────────────────────────────────────
print("Entrenando modelo desde disco con DataGenerator...")
model.fit(train_gen, validation_data=val_gen, epochs=10)

# ───────────────────────────────────────────────
# 5. Guardar modelo
# ───────────────────────────────────────────────
model.save('convlstm_model.h5')
print("Modelo guardado como convlstm_model.h5")
