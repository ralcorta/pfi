import numpy as np

data = np.load('C:/Users/Elias/Desktop/pfi/data/flow_dataset.npz')
X, y = data['X'], data['y']

print("Datos cargados del npz")
print("Shape X:", X.shape)  # (n_flows, TIME_STEPS, 32, 32, 1)
print("Shape y:", y.shape)

np.save('X.npy', X)
np.save('y_cat.npy', y)
print("Guardado X.npy y y_cat.npy")


# --- 3. 2_dividir_datos_train_test.py ---
import numpy as np
from sklearn.model_selection import train_test_split

X = np.load('X.npy')
y = np.load('y_cat.npy')

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

np.save('X_train.npy', X_train)
np.save('X_test.npy', X_test)
np.save('y_train.npy', y_train)
np.save('y_test.npy', y_test)
print("Datos divididos y guardados")