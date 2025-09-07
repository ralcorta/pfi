"""Main entry point for the ransomware detection sensor."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from scapy.packet import Packet

from .alerts.sns import SNSAlert
from .alerts.sqs import SQSAlert
from .alerts.stdout import StdoutAlert
from .core.inference_engine import InferenceEngine
from .core.signal_handler import SignalHandler
from .core.traffic_capture import PysharkCapture, TrafficCapture
from .utils.config import load_config, SensorConfig
from .utils.logger import setup_logging

# Global variables for signal handling
signal_handler: Optional[SignalHandler] = None
inference_engine: Optional[InferenceEngine] = None
traffic_capture: Optional[TrafficCapture] = None


def shutdown_sensor() -> None:
    """Graceful shutdown of the sensor."""
    global inference_engine, traffic_capture
    
    if traffic_capture:
        traffic_capture.stop_capture()
    
    if inference_engine:
        stats = inference_engine.get_statistics()
        print(f"\nFinal Statistics:")
        print(f"  Total Inferences: {stats['total_inferences']}")
        print(f"  Total Detections: {stats['total_detections']}")
        print(f"  Detection Rate: {stats['detection_rate']:.2f}%")


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["live", "pcap"]),
    default="live",
    help="Capture mode: live network monitoring or PCAP file analysis"
)
@click.option(
    "--interface",
    "-i",
    default="en0",
    help="Network interface for live capture"
)
@click.option(
    "--filter",
    "-f",
    default="",
    help="BPF filter for packet capture"
)
@click.option(
    "--input",
    "-r",
    help="Input PCAP file for offline analysis"
)
@click.option(
    "--threshold",
    "-t",
    type=float,
    default=0.80,
    help="Detection threshold (0.0-1.0)"
)
@click.option(
    "--config",
    "-c",
    help="Configuration file path"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging"
)
def main(
    mode: str,
    interface: str,
    filter: str,
    input: Optional[str],
    threshold: float,
    config: Optional[str],
    verbose: bool
) -> None:
    """Ransomware Detection Sensor - Real-time network traffic analysis."""
    
    global signal_handler, inference_engine, traffic_capture
    
    try:
        # Load configuration
        if config is None:
            config = "app/sensor/configs/sensor.yaml"
        sensor_config = load_config(config)
        
        # Override config with command line arguments
        if interface != "en0":
            sensor_config.capture.interface = interface
        if filter:
            sensor_config.capture.filter = filter
        if threshold != 0.80:
            sensor_config.detection.threshold = threshold
        if verbose:
            sensor_config.logging.level = "DEBUG"
        
        # Setup logging
        logger = setup_logging(sensor_config.logging.dict())
        logger.info("Ransomware sensor starting", mode=mode, interface=interface)
        
        # Initialize signal handler
        signal_handler = SignalHandler()
        signal_handler.set_shutdown_callback(shutdown_sensor)
        
        # Initialize inference engine
        inference_engine = InferenceEngine(
            sensor_config.model,
            sensor_config.detection
        )
        
        # Initialize alert systems
        stdout_alert = StdoutAlert(sensor_config.alerts.stdout)
        sqs_alert = SQSAlert(
            sensor_config.alerts.sqs.enabled,
            sensor_config.alerts.sqs.queue_url,
            sensor_config.alerts.sqs.region
        )
        sns_alert = SNSAlert(
            sensor_config.alerts.sns.enabled,
            sensor_config.alerts.sns.topic_arn,
            sensor_config.alerts.sns.region
        )
        
        # Initialize traffic capture
        if mode == "live":
            traffic_capture = PysharkCapture(sensor_config.capture)
            packet_generator = traffic_capture.start_live_capture()
        elif mode == "pcap":
            if not input:
                click.echo("Error: --input required for PCAP mode", err=True)
                sys.exit(1)
            traffic_capture = TrafficCapture(sensor_config.capture)
            packet_generator = traffic_capture.read_pcap_file(input)
        else:
            click.echo(f"Error: Invalid mode '{mode}'", err=True)
            sys.exit(1)
        
        logger.info("Starting packet processing", mode=mode)
        
        # Main processing loop
        for packet in packet_generator:
            if signal_handler.is_shutdown_requested():
                break
            
            try:
                # Add packet to inference engine
                result = inference_engine.add_packet(packet)
                
                if result:
                    confidence, is_malicious = result
                    
                    # Create detection data
                    detection_data = {
                        "timestamp": datetime.now().isoformat(),
                        "confidence": confidence,
                        "is_malicious": is_malicious,
                        "packet_info": {
                            "src_ip": getattr(packet.getlayer("IP"), "src", "N/A"),
                            "dst_ip": getattr(packet.getlayer("IP"), "dst", "N/A"),
                            "protocol": getattr(packet.getlayer("IP"), "proto", "N/A"),
                            "port": getattr(packet.getlayer("TCP"), "dport", "N/A")
                        },
                        "statistics": inference_engine.get_statistics()
                    }
                    
                    # Send alerts
                    stdout_alert.send_alert(detection_data)
                    sqs_alert.send_alert(detection_data)
                    sns_alert.send_alert(detection_data)
                    
            except Exception as e:
                logger.error("Error processing packet", error=str(e))
                continue
        
        logger.info("Packet processing completed")
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        sys.exit(1)
    finally:
        if signal_handler:
            shutdown_sensor()


if __name__ == "__main__":
    main()
