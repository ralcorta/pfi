import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ───────────────────────────────────────────────
# 1. Cargar datos completos
# ───────────────────────────────────────────────
print("Cargando datos procesados...")
X = np.load('X.npy')
y = np.load('y_cat.npy')
X_ransomware_features = np.load('X_ransomware_features.npy')

print(f"Datos cargados:")
print(f"  - X (payloads): {X.shape}")
print(f"  - y (etiquetas): {y.shape}")
print(f"  - X_ransomware_features: {X_ransomware_features.shape}")

# ───────────────────────────────────────────────
# 2. Normalizar features de ransomware
# ───────────────────────────────────────────────
print("Normalizando features de ransomware...")
scaler = StandardScaler()
X_ransomware_features_scaled = scaler.fit_transform(X_ransomware_features)

# ───────────────────────────────────────────────
# 3. Dividir en train/test (estratificado)
# ───────────────────────────────────────────────
print("Dividiendo datos en train/test...")
y_labels = np.argmax(y, axis=1)  # Para estratificación

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y_labels, shuffle=True
)

X_ransomware_train, X_ransomware_test, _, _ = train_test_split(
    X_ransomware_features_scaled, y, test_size=0.2, random_state=42, stratify=y_labels, shuffle=True
)

# ───────────────────────────────────────────────
# 4. Guardar a disco
# ───────────────────────────────────────────────
print("Guardando datos divididos...")

# Datos principales
np.save('X_train.npy', X_train)
np.save('X_test.npy', X_test)
np.save('y_train.npy', y_train)
np.save('y_test.npy', y_test)

# Features de ransomware
np.save('X_ransomware_train.npy', X_ransomware_train)
np.save('X_ransomware_test.npy', X_ransomware_test)

# Guardar scaler para uso posterior
import joblib
joblib.dump(scaler, 'ransomware_features_scaler.pkl')

print("✅ Datos divididos y guardados:")
print(f"  - Train: {X_train.shape[0]} muestras")
print(f"  - Test: {X_test.shape[0]} muestras")
print(f"  - Features de ransomware normalizadas y guardadas")
print(f"  - Scaler guardado en: ransomware_features_scaler.pkl")