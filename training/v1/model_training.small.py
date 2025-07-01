import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import ConvLSTM2D, Flatten, Dense
from tensorflow.keras.utils import to_categorical

# ───────────────────────────────────────────────
# 1. Configuración
# ───────────────────────────────────────────────
PAYLOAD_LEN = 1024  # 32x32 para imagen
CSV_PATH = '/Users/rodrigo/Documents/uade/tesis/data/traffic_dataset.small.csv'

# ───────────────────────────────────────────────
# 2. Cargar y preparar los datos
# ───────────────────────────────────────────────
print("Iniciando...")
print("---------------------------------------")
print("Cargando datos...")
df = pd.read_csv(CSV_PATH)
print("Datos cargados exitosamente!")
print("---------------------------------------")

# Solo usamos los bytes del payload para entrenar el modelo
print("Preparando datos...")
X_raw = df[[f'byte_{i}' for i in range(PAYLOAD_LEN)]].astype(np.float32).values
y = df['label'].values
print(f"Dimensiones de X_raw: {X_raw.shape}")
print(f"Dimensiones de y: {y.shape}")
print("---------------------------------------")

# Escalado (opcional: también podrías normalizar dividiendo por 255.0)
print("Escalando datos...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_raw)
print(f"Dimensiones de X_scaled: {X_scaled.shape}")
print("---------------------------------------")

# Reshape a (samples, time_steps=1, height=32, width=32, channels=1)
print("Reformateando datos...")
X = X_scaled.reshape(-1, 1, 32, 32, 1)
print(f"Dimensiones de X: {X.shape}")
print("---------------------------------------")

# Etiquetas a formato categórico (0 → [1,0], 1 → [0,1])
print("Transformando etiquetas...")
y_cat = to_categorical(y, num_classes=2)
print(f"Dimensiones de y_cat: {y_cat.shape}")
print(f"Ejemplo de y_cat: {y_cat[0]}")
print("---------------------------------------")

# Dividir en train/test
print("Dividiendo en train/test...")
X_train, X_test, y_train, y_test = train_test_split(X, y_cat, test_size=0.2, random_state=42)
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


# ───────────────────────────────────────────────
# 5. Evaluar el modelo
# ───────────────────────────────────────────────
print("Evaluando modelo...")
loss, accuracy = model.evaluate(X_test, y_test)
print(f"\nAccuracy final sobre test: {accuracy:.4f}")
print("---------------------------------------")

print("Guardando modelo...")
model.save('convlstm_model.small.h5')
print("Modelo guardado exitosamente!")
print("---------------------------------------")

print("FIN.")
