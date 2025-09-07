"""AWS SQS alert system."""

import json
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SQSAlert:
    """AWS SQS alert system for ransomware detections."""
    
    def __init__(self, enabled: bool = False, queue_url: str = "", region: str = "us-east-1"):
        """Initialize SQS alert system.
        
        Args:
            enabled: Whether to enable SQS alerts
            queue_url: SQS queue URL
            region: AWS region
        """
        self.enabled = enabled
        self.queue_url = queue_url
        self.region = region
        self.sqs_client: Optional[boto3.client] = None
        self.alert_count = 0
        self.error_count = 0
        
        if self.enabled:
            self._initialize_client()
        
        logger.info(
            "SQS alert system initialized",
            enabled=enabled,
            queue_url=queue_url,
            region=region
        )
    
    def _initialize_client(self) -> None:
        """Initialize AWS SQS client."""
        try:
            self.sqs_client = boto3.client('sqs', region_name=self.region)
            logger.info("SQS client initialized successfully")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            self.enabled = False
        except Exception as e:
            logger.error("Failed to initialize SQS client", error=str(e))
            self.enabled = False
    
    def send_alert(self, detection_data: Dict[str, Any]) -> bool:
        """Send alert to SQS queue.
        
        Args:
            detection_data: Detection information
            
        Returns:
            True if alert was sent successfully
        """
        if not self.enabled or not self.sqs_client:
            return True
        
        try:
            self.alert_count += 1
            
            # Create message
            message = self._create_message(detection_data)
            
            # Send message to SQS
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'AlertType': {
                        'StringValue': 'RansomwareDetection',
                        'DataType': 'String'
                    },
                    'Confidence': {
                        'StringValue': str(detection_data.get('confidence', 0.0)),
                        'DataType': 'Number'
                    },
                    'IsMalicious': {
                        'StringValue': str(detection_data.get('is_malicious', False)),
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(
                "SQS alert sent successfully",
                message_id=response['MessageId'],
                alert_id=self.alert_count
            )
            return True
            
        except ClientError as e:
            self.error_count += 1
            logger.error(
                "SQS client error",
                error=str(e),
                error_code=e.response['Error']['Code']
            )
            return False
        except Exception as e:
            self.error_count += 1
            logger.error("Failed to send SQS alert", error=str(e))
            return False
    
    def _create_message(self, detection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create SQS message from detection data.
        
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
            "queue_url": self.queue_url,
            "region": self.region,
            "alert_count": self.alert_count,
            "error_count": self.error_count,
            "success_rate": (
                (self.alert_count / (self.alert_count + self.error_count) * 100)
                if (self.alert_count + self.error_count) > 0 else 0
            )
        }
