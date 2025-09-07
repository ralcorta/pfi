"""AWS SNS alert system."""

import json
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SNSAlert:
    """AWS SNS alert system for ransomware detections."""
    
    def __init__(self, enabled: bool = False, topic_arn: str = "", region: str = "us-east-1"):
        """Initialize SNS alert system.
        
        Args:
            enabled: Whether to enable SNS alerts
            topic_arn: SNS topic ARN
            region: AWS region
        """
        self.enabled = enabled
        self.topic_arn = topic_arn
        self.region = region
        self.sns_client: Optional[boto3.client] = None
        self.alert_count = 0
        self.error_count = 0
        
        if self.enabled:
            self._initialize_client()
        
        logger.info(
            "SNS alert system initialized",
            enabled=enabled,
            topic_arn=topic_arn,
            region=region
        )
    
    def _initialize_client(self) -> None:
        """Initialize AWS SNS client."""
        try:
            self.sns_client = boto3.client('sns', region_name=self.region)
            logger.info("SNS client initialized successfully")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            self.enabled = False
        except Exception as e:
            logger.error("Failed to initialize SNS client", error=str(e))
            self.enabled = False
    
    def send_alert(self, detection_data: Dict[str, Any]) -> bool:
        """Send alert to SNS topic.
        
        Args:
            detection_data: Detection information
            
        Returns:
            True if alert was sent successfully
        """
        if not self.enabled or not self.sns_client:
            return True
        
        try:
            self.alert_count += 1
            
            # Create subject and message
            subject = self._create_subject(detection_data)
            message = self._create_message(detection_data)
            
            # Send message to SNS
            response = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=json.dumps(message, indent=2)
            )
            
            logger.info(
                "SNS alert sent successfully",
                message_id=response['MessageId'],
                alert_id=self.alert_count
            )
            return True
            
        except ClientError as e:
            self.error_count += 1
            logger.error(
                "SNS client error",
                error=str(e),
                error_code=e.response['Error']['Code']
            )
            return False
        except Exception as e:
            self.error_count += 1
            logger.error("Failed to send SNS alert", error=str(e))
            return False
    
    def _create_subject(self, detection_data: Dict[str, Any]) -> str:
        """Create SNS subject from detection data.
        
        Args:
            detection_data: Detection information
            
        Returns:
            Subject string
        """
        is_malicious = detection_data.get("is_malicious", False)
        confidence = detection_data.get("confidence", 0.0)
        
        if is_malicious:
            return f"🚨 RANSOMWARE DETECTED - Confidence: {confidence:.2%}"
        else:
            return f"⚠️ Suspicious Activity - Confidence: {confidence:.2%}"
    
    def _create_message(self, detection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create SNS message from detection data.
        
        Args:
            detection_data: Detection information
            
        Returns:
            Message dictionary
        """
        return {
            "alert_type": "ransomware_detection",
            "timestamp": detection_data.get("timestamp"),
            "confidence": detection_data.get("confidence", 0.0),
            "is_malicious": detection_data.get("is_malicious", False),
            "packet_info": detection_data.get("packet_info", {}),
            "statistics": detection_data.get("statistics", {}),
            "sensor_info": {
                "version": "1.0.0",
                "alert_id": self.alert_count
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics.
        
        Returns:
            Dictionary with alert statistics
        """
        return {
            "enabled": self.enabled,
            "topic_arn": self.topic_arn,
            "region": self.region,
            "alert_count": self.alert_count,
            "error_count": self.error_count,
            "success_rate": (
                (self.alert_count / (self.alert_count + self.error_count) * 100)
                if (self.alert_count + self.error_count) > 0 else 0
            )
        }
