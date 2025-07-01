import numpy as np
from sklearn.model_selection import KFold
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import ConvLSTM2D, Flatten, Dense
from tensorflow.keras.utils import to_categorical

# Cargar datos
X = np.load("X.npy")
y = np.load("y_cat.npy")

# Configuración de 5 folds
kfold = KFold(n_splits=5, shuffle=False)

acc_per_fold = []
loss_per_fold = []

fold_no = 1

for train_idx, val_idx in kfold.split(X, y):
    print(f"────────────── Fold {fold_no} ──────────────")
    
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
    
    # Nuevo modelo para cada fold
    model = Sequential()
    model.add(ConvLSTM2D(filters=32, kernel_size=(3, 3), activation='relu', input_shape=(1, 32, 32, 1)))
    model.add(Flatten())
    model.add(Dense(64, activation='relu'))
    model.add(Dense(2, activation='softmax'))
    
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    
    # Entrenamiento
    history = model.fit(
        X_train, y_train,
        epochs=5,
        batch_size=32,
        validation_data=(X_val, y_val),
        verbose=1
    )

    # model.save('convlstm_model_small.h5')
    # print("Modelo guardado como convlstm_model_small.h5")
    
    scores = model.evaluate(X_val, y_val, verbose=0)
    print(f"→ Score fold {fold_no}: {model.metrics_names[0]}={scores[0]:.4f}, {model.metrics_names[1]}={scores[1]*100:.2f}%")
    
    acc_per_fold.append(scores[1] * 100)
    loss_per_fold.append(scores[0])
    
    fold_no += 1

print("────────── RESULTADOS CROSS VALIDATION ──────────")
for i in range(len(acc_per_fold)):
    print(f"> Fold {i+1} - Accuracy: {acc_per_fold[i]:.2f}% - Loss: {loss_per_fold[i]:.4f}")

print(f"> Promedio accuracy: {np.mean(acc_per_fold):.2f}%")
print(f"> Promedio loss: {np.mean(loss_per_fold):.4f}")
