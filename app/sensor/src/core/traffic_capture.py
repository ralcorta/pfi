"""Network traffic capture for live monitoring and offline PCAP analysis."""

import time
from pathlib import Path
from typing import Generator, List, Optional

import pyshark
from scapy.all import PcapReader, sniff
from scapy.packet import Packet

from ..utils.config import CaptureConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TrafficCapture:
    """Network traffic capture for ransomware detection."""
    
    def __init__(self, config: CaptureConfig):
        """Initialize traffic capture.
        
        Args:
            config: Capture configuration
        """
        self.config = config
        self.is_capturing = False
        self.packet_count = 0
        
        logger.info(
            "Traffic capture initialized",
            interface=config.interface,
            filter=config.filter,
            timeout=config.timeout
        )
    
    def start_live_capture(self) -> Generator[Packet, None, None]:
        """Start live packet capture.
        
        Yields:
            Captured network packets
            
        Raises:
            PermissionError: If insufficient privileges for packet capture
            ValueError: If interface doesn't exist
        """
        logger.info("Starting live packet capture", interface=self.config.interface)
        
        try:
            self.is_capturing = True
            
            # Use scapy for packet capture
            for packet in sniff(
                iface=self.config.interface,
                filter=self.config.filter if self.config.filter else None,
                timeout=self.config.timeout,
                store=False  # Don't store packets in memory
            ):
                if not self.is_capturing:
                    break
                
                self.packet_count += 1
                yield packet
                
                # Log progress periodically
                if self.packet_count % 1000 == 0:
                    logger.info("Captured packets", count=self.packet_count)
                    
        except PermissionError:
            logger.error(
                "Insufficient privileges for packet capture. "
                "Run with sudo or use --privileged flag."
            )
            raise
        except Exception as e:
            logger.error("Live capture failed", error=str(e))
            raise
        finally:
            self.is_capturing = False
            logger.info("Live capture stopped", total_packets=self.packet_count)
    
    def read_pcap_file(self, pcap_path: str) -> Generator[Packet, None, None]:
        """Read packets from PCAP file.
        
        Args:
            pcap_path: Path to PCAP file
            
        Yields:
            Packets from PCAP file
            
        Raises:
            FileNotFoundError: If PCAP file doesn't exist
            ValueError: If PCAP file is corrupted
        """
        pcap_file = Path(pcap_path)
        if not pcap_file.exists():
            raise FileNotFoundError(f"PCAP file not found: {pcap_path}")
        
        logger.info("Reading PCAP file", path=pcap_path)
        
        try:
            with PcapReader(pcap_path) as pcap_reader:
                for packet in pcap_reader:
                    self.packet_count += 1
                    yield packet
                    
                    # Log progress periodically
                    if self.packet_count % 1000 == 0:
                        logger.info("Processed packets", count=self.packet_count)
                        
        except Exception as e:
            logger.error("PCAP reading failed", error=str(e), path=pcap_path)
            raise
        finally:
            logger.info("PCAP reading completed", total_packets=self.packet_count)
    
    def stop_capture(self) -> None:
        """Stop packet capture."""
        self.is_capturing = False
        logger.info("Capture stop requested")
    
    def get_statistics(self) -> dict:
        """Get capture statistics.
        
        Returns:
            Dictionary with capture statistics
        """
        return {
            "is_capturing": self.is_capturing,
            "packet_count": self.packet_count,
            "interface": self.config.interface,
            "filter": self.config.filter
        }


class PysharkCapture:
    """Alternative capture implementation using pyshark for better packet parsing."""
    
    def __init__(self, config: CaptureConfig):
        """Initialize pyshark capture.
        
        Args:
            config: Capture configuration
        """
        self.config = config
        self.capture: Optional[pyshark.LiveCapture] = None
        self.is_capturing = False
        self.packet_count = 0
        
        logger.info(
            "Pyshark capture initialized",
            interface=config.interface,
            filter=config.filter
        )
    
    def start_live_capture(self) -> Generator[Packet, None, None]:
        """Start live packet capture using pyshark.
        
        Yields:
            Captured network packets
            
        Raises:
            PermissionError: If insufficient privileges
            Exception: If capture fails
        """
        logger.info("Starting pyshark live capture", interface=self.config.interface)
        
        try:
            self.capture = pyshark.LiveCapture(
                interface=self.config.interface,
                bpf_filter=self.config.filter if self.config.filter else None
            )
            
            self.is_capturing = True
            
            for packet in self.capture.sniff_continuously():
                if not self.is_capturing:
                    break
                
                self.packet_count += 1
                
                # Convert pyshark packet to scapy packet
                scapy_packet = self._pyshark_to_scapy(packet)
                if scapy_packet:
                    yield scapy_packet
                
                # Log progress periodically
                if self.packet_count % 1000 == 0:
                    logger.info("Captured packets", count=self.packet_count)
                    
        except PermissionError:
            logger.error(
                "Insufficient privileges for packet capture. "
                "Run with sudo or use --privileged flag."
            )
            raise
        except Exception as e:
            logger.error("Pyshark capture failed", error=str(e))
            raise
        finally:
            self.is_capturing = False
            if self.capture:
                self.capture.close()
            logger.info("Pyshark capture stopped", total_packets=self.packet_count)
    
    def _pyshark_to_scapy(self, pyshark_packet) -> Optional[Packet]:
        """Convert pyshark packet to scapy packet.
        
        Args:
            pyshark_packet: Pyshark packet object
            
        Returns:
            Scapy packet object or None if conversion fails
        """
        try:
            # Get raw packet data
            raw_data = pyshark_packet.get_raw_packet()
            
            # Create scapy packet from raw data
            from scapy.all import Ether
            scapy_packet = Ether(raw_data)
            
            return scapy_packet
            
        except Exception as e:
            logger.debug("Failed to convert pyshark packet", error=str(e))
            return None
    
    def stop_capture(self) -> None:
        """Stop packet capture."""
        self.is_capturing = False
        if self.capture:
            self.capture.close()
        logger.info("Pyshark capture stop requested")
    
    def get_statistics(self) -> dict:
        """Get capture statistics.
        
        Returns:
            Dictionary with capture statistics
        """
        return {
            "is_capturing": self.is_capturing,
            "packet_count": self.packet_count,
            "interface": self.config.interface,
            "filter": self.config.filter
        }
