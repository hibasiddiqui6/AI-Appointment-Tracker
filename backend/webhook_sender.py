import aiohttp
import logging
from models import AppointmentData
from config import Config

logger = logging.getLogger(__name__)

class WebhookSender:
    def __init__(self):
        self.config = Config()
        self.n8n_webhook_url = self.config.N8N_WEBHOOK_URL
        
    async def send_appointment_data(self, appointment_data: AppointmentData) -> bool:
        """Send appointment data to n8n webhook"""
        if not self.n8n_webhook_url:
            logger.error("N8N webhook URL not configured")
            return False
            
        try:
            # Convert to JSON
            payload = appointment_data.to_json()
            
            logger.info(f"Sending data to webhook: {payload}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.n8n_webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        logger.info("Successfully sent data to n8n webhook")
                        return True
                    else:
                        logger.error(f"Webhook returned status {response.status}")
                        response_text = await response.text()
                        logger.error(f"Response: {response_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending to webhook: {e}")
            return False