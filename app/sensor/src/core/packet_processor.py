"""Packet processing and conversion to image format for model inference."""

import struct
from typing import List, Optional, Tuple

import numpy as np
from scapy.packet import Packet
from scapy.all import raw

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PacketProcessor:
    """Processes network packets and converts them to image format for model inference."""
    
    def __init__(self, packet_size: int = 1024, image_size: int = 32):
        """Initialize packet processor.
        
        Args:
            packet_size: Maximum packet size in bytes
            image_size: Output image size (assumes square image)
        """
        self.packet_size = packet_size
        self.image_size = image_size
        self.pixels_per_packet = image_size * image_size
        
        logger.info(
            "Packet processor initialized",
            packet_size=packet_size,
            image_size=image_size,
            pixels_per_packet=self.pixels_per_packet
        )
    
    def process_packet(self, packet: Packet) -> np.ndarray:
        """Process a single packet and convert to image format.
        
        Args:
            packet: Scapy packet object
            
        Returns:
            Processed packet as numpy array with shape (32, 32, 1)
        """
        try:
            # Extract raw packet data
            raw_data = raw(packet)
            
            # Truncate or pad to fixed size
            processed_data = self._truncate_or_pad(raw_data)
            
            # Convert to image format
            image = self._bytes_to_image(processed_data)
            
            return image
            
        except Exception as e:
            logger.error("Failed to process packet", error=str(e), packet_len=len(raw(packet)))
            # Return zero-filled image on error
            return np.zeros((self.image_size, self.image_size, 1), dtype=np.float32)
    
    def process_packet_batch(self, packets: List[Packet]) -> np.ndarray:
        """Process a batch of packets and convert to image format.
        
        Args:
            packets: List of Scapy packet objects
            
        Returns:
            Batch of processed packets as numpy array with shape (N, 32, 32, 1)
        """
        if not packets:
            logger.warning("Empty packet batch received")
            return np.zeros((1, self.image_size, self.image_size, 1), dtype=np.float32)
        
        processed_packets = []
        for packet in packets:
            processed_packet = self.process_packet(packet)
            processed_packets.append(processed_packet)
        
        batch = np.stack(processed_packets, axis=0)
        
        logger.debug(
            "Processed packet batch",
            batch_size=len(packets),
            output_shape=batch.shape
        )
        
        return batch
    
    def _truncate_or_pad(self, data: bytes) -> bytes:
        """Truncate or pad packet data to fixed size.
        
        Args:
            data: Raw packet bytes
            
        Returns:
            Bytes of exactly packet_size length
        """
        if len(data) > self.packet_size:
            # Truncate to packet_size
            return data[:self.packet_size]
        elif len(data) < self.packet_size:
            # Pad with zeros
            return data + b'\x00' * (self.packet_size - len(data))
        else:
            # Already correct size
            return data
    
    def _bytes_to_image(self, data: bytes) -> np.ndarray:
        """Convert packet bytes to grayscale image.
        
        Args:
            data: Packet bytes (must be exactly packet_size)
            
        Returns:
            Grayscale image as numpy array with shape (32, 32, 1)
        """
        if len(data) != self.packet_size:
            raise ValueError(f"Data length {len(data)} != expected {self.packet_size}")
        
        # Convert bytes to numpy array
        byte_array = np.frombuffer(data, dtype=np.uint8)
        
        # Reshape to image dimensions
        # We need exactly image_size * image_size pixels
        if len(byte_array) >= self.pixels_per_packet:
            # Take first pixels_per_packet bytes
            image_data = byte_array[:self.pixels_per_packet]
        else:
            # Pad with zeros if not enough data
            image_data = np.zeros(self.pixels_per_packet, dtype=np.uint8)
            image_data[:len(byte_array)] = byte_array
        
        # Reshape to 2D image
        image_2d = image_data.reshape(self.image_size, self.image_size)
        
        # Normalize to [0, 1] range
        image_normalized = image_2d.astype(np.float32) / 255.0
        
        # Add channel dimension for grayscale
        image_with_channel = np.expand_dims(image_normalized, axis=-1)
        
        return image_with_channel
    
    def create_temporal_window(self, packets: List[Packet], window_size: int) -> List[np.ndarray]:
        """Create temporal windows from packet sequence.
        
        Args:
            packets: List of packets
            window_size: Number of packets per window
            
        Returns:
            List of windows, each containing window_size processed packets
        """
        if len(packets) < window_size:
            logger.warning(
                "Not enough packets for window",
                available=len(packets),
                required=window_size
            )
            # Pad with zero-filled packets
            padded_packets = packets + [None] * (window_size - len(packets))
            return [self.process_packet_batch(padded_packets)]
        
        windows = []
        for i in range(0, len(packets) - window_size + 1, window_size):
            window_packets = packets[i:i + window_size]
            window = self.process_packet_batch(window_packets)
            windows.append(window)
        
        logger.debug(
            "Created temporal windows",
            total_packets=len(packets),
            window_size=window_size,
            num_windows=len(windows)
        )
        
        return windows
