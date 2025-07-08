import pandas as pd
import numpy as np
from tensorflow.keras.utils import to_categorical

# ───────────────────────────────────────────────
# 1. Configuración
# ───────────────────────────────────────────────
CSV_TYPE = '_small' # 'small' o 'full'
PAYLOAD_LEN = 1024  # 32x32 para imagen
CSV_PATH = f'C:/Users/Elias/Desktop/pfi/data/traffic_dataset{CSV_TYPE}.csv'

# ───────────────────────────────────────────────
# 2. Cargar y preparar los datos
# ───────────────────────────────────────────────
print("Iniciando...")
print("---------------------------------------")
print("Cargando datos...")
df = pd.read_csv(CSV_PATH)
print("CSV cargado!")
print("---------------------------------------")

# Solo usamos los bytes del payload
print("Preparando datos...")
X_raw = df[[f'byte_{i}' for i in range(PAYLOAD_LEN)]].astype(np.uint8).values
y = df['label'].values
print(f"Dimensiones de X_raw: {X_raw.shape}")
print(f"Dimensiones de y: {y.shape}")
print("---------------------------------------")

# Normalización simple
print("Escalando datos...")
X_scaled = X_raw / 255.0
print(f"Dimensiones de X_scaled: {X_scaled.shape}")
print("---------------------------------------")

# Reformatear para ConvLSTM
# Reshape a (samples, time_steps=1, height=32, width=32, channels=1)
print("Reformateando datos...")
X = X_scaled.reshape(-1, 1, 32, 32, 1)
print(f"Dimensiones de X: {X.shape}")
print("---------------------------------------")

# One-hot encoding
# Etiquetas a formato categórico (0 → [1,0], 1 → [0,1])
print("Transformando etiquetas...")
y_cat = to_categorical(y, num_classes=2)
print(f"Dimensiones de y_cat: {y_cat.shape}")
print(f"Ejemplo de y_cat: {y_cat[0]}")
print("---------------------------------------")

# Guardar archivos preprocesados
print("Guardando datos preprocesados...")
np.save('X.npy', X)
np.save('y_cat.npy', y_cat)
print("Datos preprocesadcos guardados.")
print("---------------------------------------")
