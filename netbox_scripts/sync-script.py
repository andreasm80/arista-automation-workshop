from extras.scripts import Script
import requests
import hmac
import hashlib
import json
from datetime import datetime

class TriggerSync(Script):
    class Meta:
        name = "Trigger Repository Sync"
        description = "Manually trigger a repository sync and playbook run"

    # Webhook configuration
    WEBHOOK_URL = "http://10.100.5.11:5000/webhook"
    WEBHOOK_SECRET = "GW7M3riaqoI9xzV4wHdTUdWGwrt3AcMQADZ0_qImQEI"

    def run(self, data, commit):
        # Minimal payload with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        payload = {
            "event": "manual_sync",
            "timestamp": timestamp
        }

        # Compute HMAC signature
        payload_json = json.dumps(payload)
        signature = hmac.new(
            self.WEBHOOK_SECRET.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

        # Send webhook request
        headers = {
            "X-Hook-Signature": signature,
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(self.WEBHOOK_URL, data=payload_json, headers=headers, timeout=10)
            response.raise_for_status()
            self.log_success(f"Webhook triggered successfully. Response: {response.text}")
        except requests.RequestException as e:
            self.log_failure(f"Failed to trigger webhook: {str(e)}")

        return f"Webhook sent at {timestamp}"
