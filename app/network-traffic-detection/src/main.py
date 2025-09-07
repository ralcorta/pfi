from typing import List, Any
import numpy as np
import tensorflow as tf
import os
from utils.capture import capture_traffic, predict_traffic
from utils.preprocess import preprocess_traffic_data, packets_to_features
from utils.logging_setup import setup_logging, log_prediction


def main() -> None:
    logger = setup_logging()

    # Load model with correct path relative to the script location
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'convlstm_model.keras')
    model = tf.keras.models.load_model(model_path)

    logger.info("Capturing network traffic...")
    packets: List[Any] = capture_traffic()

    logger.info("Preprocessing captured data...")
    X = packets_to_features(packets)
    X = preprocess_traffic_data(X)

    # Make predictions
    logger.info("Making predictions...")
    predictions = model.predict(X)

    # Log the predictions
    for i, prediction in enumerate(predictions):
        predicted_class = int(np.argmax(prediction))
        log_prediction(packets[i], predicted_class)

    logger.info("Prediction logging complete.")


if __name__ == "__main__":
    main()