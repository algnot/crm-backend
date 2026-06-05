from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UserAddPointWizard(models.TransientModel):
    _name = "crm.user.add.point.wizard"
    _description = "Add Point To User"

    user_id = fields.Many2one(
        "crm.user",
        string="User",
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "partner",
        string="Partner",
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "crm.partner.currency",
        string="Currency",
        required=True,
    )
    value = fields.Float(string="Value", required=True, default=0)
    type = fields.Selection(
        [
            ("earn", "Earn"),
            ("transfer", "Transfer"),
            ("burn", "Burn"),
        ],
        string="Type",
        required=True,
        default="earn",
    )
    note = fields.Text(string="Note", required=True)
    expiration_date = fields.Datetime(string="Expiration Date")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        partner_id = values.get("partner_id") or self.env.context.get("default_partner_id")
        if partner_id and "currency_id" in fields_list:
            partner = self.env["partner"].browse(partner_id)
            currency = partner.currency_ids.filtered("is_default")[:1] or partner.currency_ids[:1]
            if currency:
                values["currency_id"] = currency.id
        return values

    def action_add_point(self):
        self.ensure_one()
        if not self.note or not self.note.strip():
            raise ValidationError("กรุณาระบุหมายเหตุ")
        if self.value <= 0:
            raise ValidationError("Value ต้องมากกว่า 0")
        if self.currency_id.partner_id != self.partner_id:
            raise ValidationError("Point currency must belong to this partner.")

        self.env["crm.user.point"].create({
            "name": f"Admin: {self.user_id.display_name}",
            "admin_note": self.note.strip(),
            "value": self.value,
            "type": self.type,
            "given_date": fields.Datetime.now(),
            "expiration_date": self.expiration_date,
            "currency_id": self.currency_id.id,
            "user_id": self.user_id.id,
        })

        return {"type": "ir.actions.act_window_close"}
