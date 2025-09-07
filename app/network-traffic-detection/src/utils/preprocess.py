from typing import Any, Tuple, List
import numpy as np
from tensorflow.keras.models import load_model, Model


def packets_to_features(packets: List[Any]) -> np.ndarray:
    """Convert pyshark packets to numerical features for the model.
    
    This is a simplified conversion that extracts basic packet features.
    In a real implementation, you would need to convert packets to the 
    same format used during training (likely image-like representations).
    """
    if not packets:
        # Return empty array with correct shape if no packets
        return np.zeros((1, 10, 32, 32, 1))
    
    # For now, create dummy data with the expected shape
    # This should be replaced with actual packet-to-image conversion
    num_packets = len(packets)
    features = np.random.randint(0, 256, (num_packets, 10, 32, 32, 1), dtype=np.uint8)
    return features.astype(np.float32)


def preprocess_traffic_data(raw_data: np.ndarray) -> np.ndarray:
    """Scale and reshape raw traffic numpy array to model input.

    Expected input shape: (N, 10, 32, 32, 1) or a flat representation that can be
    reshaped by the caller. This function normalizes to [0,1].
    """
    scaled_data: np.ndarray = raw_data / 255.0
    reshaped_data: np.ndarray = scaled_data.reshape(-1, 10, 32, 32, 1)
    return reshaped_data


def load_and_preprocess_model(model_path: str, traffic_data: np.ndarray) -> Tuple[Model, np.ndarray]:
    model: Model = load_model(model_path)
    preprocessed_data: np.ndarray = preprocess_traffic_data(traffic_data)
    return model, preprocessed_data