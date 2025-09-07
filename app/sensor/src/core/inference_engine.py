"""Inference engine for ransomware detection using ConvLSTM model."""

import time
from typing import List, Optional, Tuple

import numpy as np
import tensorflow as tf
from scapy.packet import Packet

from ..utils.config import DetectionConfig, ModelConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class InferenceEngine:
    """Inference engine for real-time ransomware detection."""
    
    def __init__(self, model_config: ModelConfig, detection_config: DetectionConfig):
        """Initialize inference engine.
        
        Args:
            model_config: Model configuration
            detection_config: Detection configuration
        """
        self.model_config = model_config
        self.detection_config = detection_config
        self.model: Optional[tf.keras.Model] = None
        self.packet_buffer: List[Packet] = []
        self.inference_count = 0
        self.detection_count = 0
        
        self._load_model()
        
        logger.info(
            "Inference engine initialized",
            model_path=model_config.path,
            threshold=detection_config.threshold,
            window_size=detection_config.window_size
        )
    
    def _load_model(self) -> None:
        """Load the trained ConvLSTM model."""
        try:
            self.model = tf.keras.models.load_model(self.model_config.path)
            logger.info("Model loaded successfully", model_path=self.model_config.path)
        except Exception as e:
            logger.error("Failed to load model", error=str(e), model_path=self.model_config.path)
            raise
    
    def add_packet(self, packet: Packet) -> Optional[Tuple[float, bool]]:
        """Add packet to buffer and perform inference if window is complete.
        
        Args:
            packet: Network packet to analyze
            
        Returns:
            Tuple of (confidence, is_malicious) if inference was performed, None otherwise
        """
        self.packet_buffer.append(packet)
        
        # Check if we have enough packets for inference
        if len(self.packet_buffer) >= self.detection_config.window_size:
            return self._perform_inference()
        
        return None
    
    def _perform_inference(self) -> Tuple[float, bool]:
        """Perform inference on the current packet window.
        
        Returns:
            Tuple of (confidence, is_malicious)
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        start_time = time.time()
        
        try:
            # Get the window of packets
            window_packets = self.packet_buffer[:self.detection_config.window_size]
            
            # Convert packets to model input format
            model_input = self._packets_to_model_input(window_packets)
            
            # Perform inference
            predictions = self.model.predict(model_input, verbose=0)
            
            # Get the confidence score (assuming binary classification)
            confidence = float(predictions[0][1])  # Probability of malicious class
            
            # Determine if malicious based on threshold
            is_malicious = confidence >= self.detection_config.threshold
            
            # Update statistics
            self.inference_count += 1
            if is_malicious:
                self.detection_count += 1
            
            inference_time = time.time() - start_time
            
            logger.info(
                "Inference completed",
                confidence=confidence,
                is_malicious=is_malicious,
                threshold=self.detection_config.threshold,
                inference_time_ms=inference_time * 1000,
                total_inferences=self.inference_count,
                total_detections=self.detection_count
            )
            
            # Remove processed packets from buffer (sliding window)
            self.packet_buffer = self.packet_buffer[1:]
            
            return confidence, is_malicious
            
        except Exception as e:
            logger.error("Inference failed", error=str(e))
            # Clear buffer on error to prevent accumulation
            self.packet_buffer.clear()
            raise
    
    def _packets_to_model_input(self, packets: List[Packet]) -> np.ndarray:
        """Convert packets to model input format.
        
        Args:
            packets: List of packets to convert
            
        Returns:
            Model input array with shape (1, window_size, 32, 32, 1)
        """
        from .packet_processor import PacketProcessor
        
        processor = PacketProcessor(
            packet_size=self.detection_config.packet_size,
            image_size=32
        )
        
        # Process packets to images
        images = processor.process_packet_batch(packets)
        
        # Ensure we have the correct number of packets
        if len(images) < self.detection_config.window_size:
            # Pad with zero images
            padding_needed = self.detection_config.window_size - len(images)
            zero_image = np.zeros((1, 32, 32, 1), dtype=np.float32)
            padding = np.repeat(zero_image, padding_needed, axis=0)
            images = np.concatenate([images, padding], axis=0)
        elif len(images) > self.detection_config.window_size:
            # Truncate to window size
            images = images[:self.detection_config.window_size]
        
        # Add batch dimension
        model_input = np.expand_dims(images, axis=0)
        
        # Verify shape
        expected_shape = (1, self.detection_config.window_size, 32, 32, 1)
        if model_input.shape != expected_shape:
            logger.warning(
                "Unexpected model input shape",
                actual=model_input.shape,
                expected=expected_shape
            )
        
        return model_input
    
    def get_statistics(self) -> dict:
        """Get inference statistics.
        
        Returns:
            Dictionary with inference statistics
        """
        detection_rate = (self.detection_count / self.inference_count * 100) if self.inference_count > 0 else 0
        
        return {
            "total_inferences": self.inference_count,
            "total_detections": self.detection_count,
            "detection_rate": detection_rate,
            "buffer_size": len(self.packet_buffer),
            "threshold": self.detection_config.threshold
        }
    
    def reset_statistics(self) -> None:
        """Reset inference statistics."""
        self.inference_count = 0
        self.detection_count = 0
        logger.info("Inference statistics reset")
    
    def clear_buffer(self) -> None:
        """Clear the packet buffer."""
        self.packet_buffer.clear()
        logger.info("Packet buffer cleared")
