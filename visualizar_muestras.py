import matplotlib.pyplot as plt
import numpy as np

X = np.load('X.npy')
y = np.argmax(np.load('y_cat.npy'), axis=1)

for i in range(3):
    plt.imshow(X[i][0].squeeze(), cmap='gray')
    plt.title("Malware" if y[i] == 1 else "Benigno")
    plt.show()