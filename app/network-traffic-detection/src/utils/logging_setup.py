import logging
import os
from typing import Optional


def setup_logging(log_file: str = 'network_traffic_detection.log') -> logging.Logger:
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            # logging.FileHandler(os.path.join(log_dir, log_file)),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('network_traffic_detection')


def log_prediction(prediction: object, additional_info: Optional[object] = None) -> None:
    if additional_info:
        logging.info(f"Prediction: {prediction}, Info: {additional_info}")
    else:
        logging.info(f"Prediction: {prediction}")