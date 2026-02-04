import requests

class WhatsappService:
    BASE_URL = "https://messaginghub.solutions/relaybridge/api/v1/meta"

    def __init__(self, channel_id: str, api_key: str):
        """
        Same pattern as your shipment services
        """
        self.channel_id = channel_id
        self.api_key = api_key

        if not self.channel_id or not self.api_key:
            raise Exception("WhatsApp credentials missing")

        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }

    # ================= SEND MESSAGE ================= #

    def send_message(self, phone: str, payload: dict):
        """
        Generic sender for ALL template types:
        - Text
        - Media
        - QR
        - CTA
        - Carousel
        - LTO
        """
        url = f"{self.BASE_URL}/{self.channel_id}/messages"
        payload["to"] = phone
        res = requests.post(url, json=payload, headers=self.headers, timeout=20)
        return res.json()

    # ================= TEXT TEMPLATE ================= #

    def send_text_template(self, phone, template_name, params):
        payload = {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)} for p in params
                    ]
                }]
            }
        }
        return self.send_message(phone, payload)

    # ================= MEDIA TEMPLATE ================= #

    def send_media_template(self, phone, template_name, media_id, params):
        payload = {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "header",
                        "parameters": [{
                            "type": "image",
                            "image": {"id": media_id}
                        }]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(p)} for p in params
                        ]
                    }
                ]
            }
        }
        return self.send_message(phone, payload)

    # ================= QR TEMPLATE ================= #

    def send_qr_template(self, phone, template_name, qr_text):
        payload = {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [{
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {"type": "text", "text": qr_text}
                    ]
                }]
            }
        }
        return self.send_message(phone, payload)

    # ================= CAROUSEL TEMPLATE ================= #

    def send_carousel_template(self, phone, template_name, cards):
        payload = {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": cards
            }
        }
        return self.send_message(phone, payload)

    # ================= LTO TEMPLATE ================= #

    def send_lto_template(self, phone, template_name, offer_text, expiry):
        payload = {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": offer_text},
                        {"type": "text", "text": expiry}
                    ]
                }]
            }
        }
        return self.send_message(phone, payload)

    # ================= SESSION TEXT ================= #

    def send_text(self, phone, text):
        payload = {
            "to": phone,
            "type": "text",
            "text": {"body": text}
        }
        return self.send_message(phone, payload)

    # ================= MEDIA UPLOAD ================= #

    def upload_media(self, file_path, mime_type):
        url = f"{self.BASE_URL}/{self.channel_id}/media/template"
        files = {"file": open(file_path, "rb")}
        data = {
            "type": mime_type,
            "messaging_product": "whatsapp"
        }
        res = requests.post(
            url,
            headers={"X-API-KEY": self.api_key},
            files=files,
            data=data
        )
        return res.json()

    # ================= TEMPLATE MANAGEMENT ================= #

    def list_templates(self):
        url = f"{self.BASE_URL}/{self.channel_id}/message_templates"
        res = requests.get(url, headers=self.headers)
        return res.json()

    def get_template(self, template_id):
        url = f"{self.BASE_URL}/{self.channel_id}/message_templates/{template_id}"
        res = requests.get(url, headers=self.headers)
        return res.json()

    def create_template(self, payload):
        url = f"{self.BASE_URL}/{self.channel_id}/message_templates"
        res = requests.post(url, json=payload, headers=self.headers)
        return res.json()

    def edit_template(self, template_id, payload):
        url = f"{self.BASE_URL}/{self.channel_id}/message_templates/{template_id}"
        res = requests.post(url, json=payload, headers=self.headers)
        return res.json()

    def delete_template(self, template_id):
        url = f"{self.BASE_URL}/{self.channel_id}/message_templates?hsm_id={template_id}"
        res = requests.delete(url, headers=self.headers)
        return res.json()
