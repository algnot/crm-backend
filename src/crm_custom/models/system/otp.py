import secrets
import string
import requests
import os

from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OTP(models.Model):
    _name = "crm.otp"
    _description = "OTP"
    _order = "create_date desc"
    _REF_ALPHABET = string.ascii_letters + string.digits

    recipient = fields.Char(string="Recipient")
    key = fields.Char(string="Key")
    key_id = fields.Char(string="Key Id")
    ref = fields.Char(string="Ref")
    otp = fields.Char(string="OTP")
    expiry = fields.Datetime(string="Expiry", default=fields.Datetime.now)
    is_sent = fields.Boolean(string="Is Sent")
    reason = fields.Char(string="Reason")

    partner_id = fields.Many2one(
        "partner",
        string="Partner",
        required=True,
        ondelete="cascade",
    )

    type = fields.Selection(
        selection=[
            ("email", "Email"),
            ("phone", "Phone"),
        ],
        string="Type",
        required=True,
    )

    @api.model
    def generate_otp(self, recipient, otp_type, key, key_id, partner):
        valid_types = dict(self._fields["type"].selection)
        if otp_type not in valid_types:
            raise ValidationError("Invalid OTP type.")

        otp = self.create({
            "recipient": recipient,
            "type": otp_type,
            "expiry": fields.Datetime.now() + timedelta(minutes=15),
            "key": key,
            "key_id": key_id,
            "partner_id": partner.id,
        })

        if otp_type == "phone":
            otp_ref = otp.send_sms_otp()
            if otp_ref:
                otp.write({
                    "otp": otp_ref.get("transaction_id"),
                    "ref": otp_ref.get("ref"),
                })

        elif otp_type == "email":
            otp.write({
                "otp": f"{secrets.randbelow(1000000):06d}",
                "ref": "".join(secrets.choice(self._REF_ALPHABET) for _ in range(5)),
            })

        return otp

    @api.model
    def has_sms_otp_credit(self):
        base_url = os.getenv("SMS_API_ENDPOINT", False)
        if not base_url:
            return False

        api_token = os.getenv("SMS_API_TOKEN", False)
        if not api_token:
            return False

        url = f"{base_url}/openapi/sms/balance"

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {api_token}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return False

        remaining_credit = response.json().get("balance", 0)

        if remaining_credit < 1:
            return False

        return True

    def make_as_fail(self, reason: str):
        return self.write({
            "reason": reason,
            "is_sent": False
        })

    def make_as_send(self, reason: str):
        return self.write({
            "reason": reason,
            "is_sent": True
        })

    def send_sms_otp(self):
        base_url = os.getenv("SMS_API_ENDPOINT", False)
        if not base_url:
            self.make_as_fail("SMS_API_ENDPOINT not configured.")
            return False

        api_token = os.getenv("SMS_API_TOKEN", False)
        if not api_token:
            self.make_as_fail("SMS_API_TOKEN not configured.")
            return False

        sms_app_key = os.getenv("SMS_APP_KEY", False)
        if not sms_app_key:
            self.make_as_fail("SMS_APP_KEY not configured.")
            return False

        sms_app_secret = os.getenv("SMS_APP_SECRET", False)
        if not sms_app_secret:
            self.make_as_fail("SMS_APP_SECRET not configured.")
            return False

        url = f"{base_url}/openapi/sms/app/otp"

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {api_token}",
            "secret": f"{sms_app_secret}",
            "content-type": "application/json"
        }

        payload = {
            "msisdn": self.recipient,
            "appKey": sms_app_key
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200 or response.status_code != 201:
            self.make_as_fail(f"failed to send sms otp: {response.text}")
            return False

        self.make_as_send(response.text)
        return {
            "ref": response.json().get("ref", False),
            "transaction_id": response.json().get("transaction_id", False)
        }

    def verify_sms_otp(self, otp_code):
        base_url = os.getenv("SMS_API_ENDPOINT", False)
        if not base_url:
            return False

        api_token = os.getenv("SMS_API_TOKEN", False)
        if not api_token:
            self.make_as_fail("SMS_API_TOKEN not configured.")
            return False

        url = f"{base_url}/openapi/verify/otp"

        payload = {
            "msisdn": self.recipient,
            "otp": otp_code,
            "transaction_id": self.otp,
        }
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {api_token}",
            "content-type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            return False

        status = response.json().get("status", False)

        return status
