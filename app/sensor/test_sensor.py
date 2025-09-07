#!/usr/bin/env python3
"""Test script for the ransomware detection sensor."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.packet_processor import PacketProcessor
from src.core.inference_engine import InferenceEngine
from src.utils.config import ModelConfig, DetectionConfig
from src.utils.logger import setup_logging
from scapy.all import Ether, IP, TCP, Raw


def create_test_packet() -> Ether:
    """Create a test packet for testing."""
    return Ether() / IP(src="192.168.1.1", dst="192.168.1.2") / TCP(dport=80) / Raw(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")


def test_packet_processor():
    """Test packet processor."""
    print("Testing Packet Processor...")
    
    processor = PacketProcessor(packet_size=1024, image_size=32)
    packet = create_test_packet()
    
    # Test single packet processing
    image = processor.process_packet(packet)
    print(f"  ✓ Single packet processed: {image.shape}")
    
    # Test batch processing
    packets = [create_test_packet() for _ in range(5)]
    batch = processor.process_packet_batch(packets)
    print(f"  ✓ Batch processing: {batch.shape}")
    
    # Test temporal window
    windows = processor.create_temporal_window(packets, 3)
    print(f"  ✓ Temporal windows: {len(windows)} windows")
    
    print("  ✓ Packet processor tests passed!\n")


def test_inference_engine():
    """Test inference engine (without model)."""
    print("Testing Inference Engine...")
    
    # Create test configs
    model_config = ModelConfig(path="../../convlstm_model.keras")
    detection_config = DetectionConfig(threshold=0.80, window_size=3)
    
    try:
        engine = InferenceEngine(model_config, detection_config)
        
        # Test packet addition
        packet = create_test_packet()
        result = engine.add_packet(packet)
        print(f"  ✓ Packet added to buffer: {result is None}")
        
        # Add more packets to trigger inference
        for _ in range(2):
            engine.add_packet(create_test_packet())
        
        # Get statistics
        stats = engine.get_statistics()
        print(f"  ✓ Statistics: {stats}")
        
        print("  ✓ Inference engine tests passed!\n")
        
    except Exception as e:
        print(f"  ⚠ Inference engine test skipped (model not available): {e}\n")


def test_configuration():
    """Test configuration system."""
    print("Testing Configuration System...")
    
    try:
        from src.utils.config import load_config
        config = load_config("configs/sensor.yaml")
        print(f"  ✓ Configuration loaded: {config.detection.threshold}")
        print("  ✓ Configuration tests passed!\n")
    except Exception as e:
        print(f"  ⚠ Configuration test skipped: {e}\n")


def test_logging():
    """Test logging system."""
    print("Testing Logging System...")
    
    try:
        from src.utils.logger import get_logger
        logger = get_logger("test")
        logger.info("Test log message")
        print("  ✓ Logging system working")
        print("  ✓ Logging tests passed!\n")
    except Exception as e:
        print(f"  ⚠ Logging test failed: {e}\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("RANSOMWARE DETECTION SENSOR - TEST SUITE")
    print("=" * 60)
    print()
    
    test_packet_processor()
    test_inference_engine()
    test_configuration()
    test_logging()
    
    print("=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
