from typing import Any, List
import numpy as np
from tensorflow.keras.models import Model
import pyshark
import logging

from utils.preprocess import preprocess_traffic_data

# Module logger
logger = logging.getLogger(__name__)


def capture_traffic(interface: str = 'en0', packet_count: int = 10) -> List[Any]:
    """Capture packets from the given interface.
    
    Returns a list of captured packet objects (pyshark Packet instances).
    """
    logger.info(f"Starting packet capture on interface: {interface}")
    capture = pyshark.LiveCapture(interface=interface)

    packets: List[Any] = []
    for packet in capture.sniff_continuously(packet_count=packet_count):
        logger.info(f"Captured packet: {packet}")
        packets.append(packet)

    return packets


def predict_traffic(model: Model, data: Any) -> np.ndarray:
    """Preprocess input data and run model prediction.

    `data` should be in the raw form expected by `preprocess_traffic_data`.
    Returns the raw prediction output from the model (numpy array).
    """
    processed_data: np.ndarray = preprocess_traffic_data(data)
    predictions: np.ndarray = model.predict(processed_data)
    return predictions


def log_predictions(predictions: np.ndarray) -> None:
    for i, prediction in enumerate(predictions):
        logger.info(f"Prediction for packet {i}: {prediction}")