import numpy as np
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import ConvLSTM2D, Flatten, Dense
from tensorflow.keras.models import load_model

# Cargar datos preprocesados
print("Cargando X e Y preprocesados...")
X = np.load('X.npy')
y = np.load('y_cat.npy')
print("Datos cargados exitosamente.")
print("---------------------------------------")

# Separar en train/test
print("Dividiendo en train/test...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Dimensiones de X_train: {X_train.shape}")
print(f"Dimensiones de X_test: {X_test.shape}")
print(f"Dimensiones de y_train: {y_train.shape}")
print(f"Dimensiones de y_test: {y_test.shape}")
print("---------------------------------------")

# ───────────────────────────────────────────────
# 3. Crear el modelo ConvLSTM
# ───────────────────────────────────────────────
print("Creando modelo...")
model = Sequential()
model.add(ConvLSTM2D(filters=32, kernel_size=(3, 3), activation='relu', input_shape=(1, 32, 32, 1)))
model.add(Flatten())
model.add(Dense(64, activation='relu'))
model.add(Dense(2, activation='softmax'))

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
print("Modelo creado exitosamente!")
print("---------------------------------------")

# ───────────────────────────────────────────────
# 4. Entrenar el modelo
# ───────────────────────────────────────────────
print("Entrenando modelo...")
model.fit(X_train, y_train, epochs=10, batch_size=32, validation_split=0.1)
print("Entrenamiento finalizado!")
print("---------------------------------------")


# Guardar modelo
print("Guardando modelo...")
model.save('convlstm_model.h5')
print("Modelo entrenado y guardado.")
print("---------------------------------------")
