import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import ConvLSTM2D, Flatten, Dense
from tensorflow.keras.utils import Sequence

class DataGenerator(Sequence):
    def __init__(self, X_path, y_path, batch_size=32):
        self.X = np.load(X_path, mmap_mode='r')
        self.y = np.load(y_path, mmap_mode='r')
        self.batch_size = batch_size
        self.length = self.X.shape[0]

    def __len__(self):
        return int(np.ceil(self.length / self.batch_size))

    def __getitem__(self, idx):
        batch_start = idx * self.batch_size
        batch_end = min((idx + 1) * self.batch_size, self.length)
        return self.X[batch_start:batch_end], self.y[batch_start:batch_end]

model = Sequential()
model.add(ConvLSTM2D(8, (3, 3), activation='relu', input_shape=(10, 32, 32, 1)))
model.add(Flatten())
model.add(Dense(16, activation='relu'))
model.add(Dense(2, activation='softmax'))
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

train_gen = DataGenerator('X_train.npy', 'y_train.npy')
val_gen = DataGenerator('X_test.npy', 'y_test.npy')
model.fit(train_gen, validation_data=val_gen, epochs=10)
model.save('convlstm_model.h5')