import secrets
import string
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OTP(models.Model):
    _name = "crm.otp"
    _description = "OTP"
    _REF_ALPHABET = string.ascii_letters + string.digits

    key = fields.Char(string="Key")
    key_id = fields.Char(string="Key Id")
    ref = fields.Char(string="Ref", required=True)
    otp = fields.Char(string="OTP", required=True)
    expiry = fields.Datetime(string="Expiry", required=True, default=fields.Datetime.now)

    type = fields.Selection(
        selection=[
            ("email", "Email"),
            ("phone", "Phone"),
        ],
        string="Type",
        required=True,
    )

    @api.model
    def generate_otp(self, otp_type, key, key_id):
        valid_types = dict(self._fields["type"].selection)
        if otp_type not in valid_types:
            raise ValidationError("Invalid OTP type.")

        return self.create({
            "type": otp_type,
            "otp": f"{secrets.randbelow(1000000):06d}",
            "ref": "".join(secrets.choice(self._REF_ALPHABET) for _ in range(5)),
            "expiry": fields.Datetime.now() + timedelta(minutes=15),
            "key": key,
            "key_id": key_id,
        })
