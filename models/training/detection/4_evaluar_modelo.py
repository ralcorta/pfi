import numpy as np
from tensorflow.keras.models import load_model
from sklearn.metrics import classification_report

model = load_model('convlstm_model.keras')
X_test = np.load('X_test.npy')
y_test = np.load('y_test.npy')

loss, acc = model.evaluate(X_test, y_test)
print(f"Loss: {loss}, Accuracy: {acc}")

y_pred = np.argmax(model.predict(X_test), axis=1)
y_true = np.argmax(y_test, axis=1)
print(classification_report(y_true, y_pred, labels=[0, 1], target_names=["Benigno", "Malware"]))