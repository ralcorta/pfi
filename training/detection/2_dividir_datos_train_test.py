import numpy as np
from sklearn.model_selection import train_test_split

# ───────────────────────────────────────────────
# 1. Cargar datos completos
# ───────────────────────────────────────────────
print("Cargando X.npy e y_cat.npy...")
X = np.load('X.npy')
y = np.load('y_cat.npy')
print(f"Datos cargados: {X.shape}, {y.shape}")

# ───────────────────────────────────────────────
# 2. Dividir en train/test (estratificado si querés)
# ───────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ───────────────────────────────────────────────
# 3. Guardar a disco
# ───────────────────────────────────────────────
np.save('X_train.npy', X_train)
np.save('X_test.npy', X_test)
np.save('y_train.npy', y_train)
np.save('y_test.npy', y_test)
print("Listo: datos divididos y guardados.")