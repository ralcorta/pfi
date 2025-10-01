"""Sistema de alertas por stdout"""
import json
import logging

class StdoutAlert:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def send_malware_alert(self, alert_data):
        if self.config.get('format') == 'json':
            print(f"ALERT: {json.dumps(alert_data)}")
        else:
            print(f"🚨 MALWARE DETECTADO: {alert_data}")