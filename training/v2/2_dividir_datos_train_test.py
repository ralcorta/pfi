import numpy as np
from sklearn.model_selection import train_test_split

print("Cargando datos originales...")
X = np.load('X.npy')
y = np.load('y_cat.npy')
print("Datos cargados.")

print("Dividiendo en train/test...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Guardando archivos...")
np.save('X_train.npy', X_train)
np.save('X_test.npy', X_test)
np.save('y_train.npy', y_train)
np.save('y_test.npy', y_test)

print("Listo. Datos divididos y guardados.")