import re
from odoo import fields, models

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class PartnerAds(models.Model):
    _name = "partner.ads"
    _description = "Partner Ads"

    action = fields.Char(string="Action")
    message = fields.Text(string="Message")
    image = fields.Image(string="Image", max_width=1920, max_height=1920)
    start_date = fields.Datetime(string="Start Date", tracking=True, default=fields.Datetime.now)
    end_date = fields.Datetime(string="End Date", tracking=True, default=fields.Datetime.now)
    active = fields.Boolean(default=True, tracking=True)

    partner_id = fields.Many2one(
        "partner",
        string="Partner",
        required=True,
        ondelete="cascade",
    )
