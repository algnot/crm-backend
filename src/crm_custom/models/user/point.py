from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UsePoint(models.Model):
    _name = "crm.user.point"
    _description = "Point"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", required=True)
    value = fields.Float(string="Value", tracking=True, required=True)
    type = fields.Selection([
        ("earn", "Earn"),
        ("transfer", "Transfer"),
        ("burn", "Burn"),
    ], string="Type", required=True)
    given_date = fields.Datetime(string="Given Date", tracking=True, required=True)
    expiration_date = fields.Datetime(string="Expiration Date", tracking=True)

    currency_id = fields.Many2one(
        "crm.user.point.currency",
        string="Currency",
        required=True,
        ondelete="cascade",
    )

    user_id = fields.Many2one(
        "crm.user",
        string="User",
        required=True,
        ondelete="cascade",
    )

    @api.constrains("currency_id", "user_id")
    def _check_currency_partner(self):
        for record in self:
            if (
                record.currency_id
                and record.user_id
                and record.currency_id.partner_id != record.user_id.partner_id
            ):
                raise ValidationError("Point currency must belong to the user's partner.")
