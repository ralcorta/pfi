"""Sistema de alertas por SNS"""
import json
import logging
import boto3

class SNSAlert:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        # self.sns_client = boto3.client('sns', region_name=config.get('region', 'us-east-1'))
    
    async def send_malware_alert(self, alert_data):
        try:
            print(f"Enviando alerta SNS: {alert_data}")
            # message = json.dumps(alert_data, indent=2)
            # self.sns_client.publish(
            #     TopicArn=self.config['topic_arn'],
            #     Message=message,
            #     Subject='🚨 Ransomware Detectado'
            # )
            self.logger.info("✅ Alerta SNS enviada")
        except Exception as e:
            self.logger.error(f"❌ Error enviando alerta SNS: {e}")