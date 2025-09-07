"""Console output alert system."""

import json
from datetime import datetime
from typing import Any, Dict

from ..utils.logger import get_logger

logger = get_logger(__name__)


class StdoutAlert:
    """Console alert system for ransomware detections."""
    
    def __init__(self, enabled: bool = True):
        """Initialize stdout alert system.
        
        Args:
            enabled: Whether to enable stdout alerts
        """
        self.enabled = enabled
        self.alert_count = 0
        
        logger.info("Stdout alert system initialized", enabled=enabled)
    
    def send_alert(self, detection_data: Dict[str, Any]) -> bool:
        """Send alert to stdout.
        
        Args:
            detection_data: Detection information
            
        Returns:
            True if alert was sent successfully
        """
        if not self.enabled:
            return True
        
        try:
            self.alert_count += 1
            
            # Create alert message
            alert_message = self._format_alert(detection_data)
            
            # Print to stdout
            print(alert_message)
            
            logger.info("Stdout alert sent", alert_id=self.alert_count)
            return True
            
        except Exception as e:
            logger.error("Failed to send stdout alert", error=str(e))
            return False
    
    def _format_alert(self, detection_data: Dict[str, Any]) -> str:
        """Format detection data into alert message.
        
        Args:
            detection_data: Detection information
            
        Returns:
            Formatted alert message
        """
        timestamp = datetime.now().isoformat()
        confidence = detection_data.get("confidence", 0.0)
        is_malicious = detection_data.get("is_malicious", False)
        
        # Create alert header
        alert_type = "🚨 RANSOMWARE DETECTED" if is_malicious else "⚠️  SUSPICIOUS ACTIVITY"
        
        # Format alert message
        alert_lines = [
            "=" * 80,
            f"{alert_type}",
            "=" * 80,
            f"Timestamp: {timestamp}",
            f"Confidence: {confidence:.4f}",
            f"Status: {'MALICIOUS' if is_malicious else 'SUSPICIOUS'}",
            f"Alert ID: {self.alert_count}",
        ]
        
        # Add packet information if available
        if "packet_info" in detection_data:
            packet_info = detection_data["packet_info"]
            alert_lines.extend([
                "",
                "Packet Information:",
                f"  Source IP: {packet_info.get('src_ip', 'N/A')}",
                f"  Destination IP: {packet_info.get('dst_ip', 'N/A')}",
                f"  Protocol: {packet_info.get('protocol', 'N/A')}",
                f"  Port: {packet_info.get('port', 'N/A')}",
            ])
        
        # Add statistics if available
        if "statistics" in detection_data:
            stats = detection_data["statistics"]
            alert_lines.extend([
                "",
                "Detection Statistics:",
                f"  Total Inferences: {stats.get('total_inferences', 0)}",
                f"  Total Detections: {stats.get('total_detections', 0)}",
                f"  Detection Rate: {stats.get('detection_rate', 0):.2f}%",
            ])
        
        alert_lines.extend([
            "",
            "=" * 80,
            ""
        ])
        
        return "\n".join(alert_lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics.
        
        Returns:
            Dictionary with alert statistics
        """
        return {
            "enabled": self.enabled,
            "alert_count": self.alert_count
        }
