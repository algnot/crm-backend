import re
import os
from odoo import api, fields, models
from odoo.exceptions import ValidationError

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class Inventory(models.Model):
    _name = "partner"
    _description = "Partner"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _sql_constraints = [
        ("partner_slug_uniq", "unique(slug)", "Slug must be unique."),
    ]

    name = fields.Char(string="Name", tracking=True, required=True)
    slug = fields.Char(string="Slug", tracking=True, required=True)
    logo = fields.Image(string="Logo", max_width=1920, max_height=1920)

    partner_line_liff_id = fields.Char(string="LIFF ID", tracking=True)
    partner_line_channel_access_token = fields.Char(string="Channel Access Token", password="True" ,tracking=True)

    description = fields.Text(string="Description", tracking=True)

    ui_background_color = fields.Char(string="Background Color", tracking=True)
    ui_background_white_color = fields.Char(string="Background White Color", tracking=True)
    ui_primary_color = fields.Char(string="Primary Color", tracking=True)
    ui_secondary_color = fields.Char(string="Secondary Color", tracking=True)

    ui_text_color = fields.Char(string="Text Color", tracking=True)
    ui_text_white_color = fields.Char(string="Text White Color", tracking=True)
    ui_text_gray_color = fields.Char(string="Text Gray Color", tracking=True)
    ui_text_success_color = fields.Char(string="Text Success Color", tracking=True)
    ui_text_error_color = fields.Char(string="Text Error Color", tracking=True)

    ui_button_color = fields.Char(string="Button Color", tracking=True)
    ui_button_text_color = fields.Char(string="Button Text Color", tracking=True)

    ui_welcome_title = fields.Char(string="Welcome Title", tracking=True)

    ui_crm_required_phone = fields.Boolean(string="Require Phone", default=False, tracking=True)
    ui_crm_required_email = fields.Boolean(string="Require Email", default=False, tracking=True)
    ui_custom_field_ids = fields.One2many(
        "partner.custom.field",
        "partner_id",
        string="Custom Field",
        tracking=True,
    )

    user_ids = fields.One2many(
        "crm.user",
        "partner_id",
        string="Users",
    )

    currency_ids = fields.One2many(
        "crm.partner.currency",
        "partner_id",
        string="Currencies",
    )

    point_redeem_ids = fields.One2many(
        "crm.partner.point.redeem",
        "partner_id",
        string="Point Redeems",
    )

    coupon_ids = fields.One2many(
        "partner.coupon",
        "partner_id",
        string="Coupons",
    )

    active = fields.Boolean(string="Active", default=True, tracking=True)

    liff_setup_url = fields.Char(
        string="LIFF Setup URL",
        compute="_compute_liff_setup_url",
        sanitize=False,
    )

    @api.depends("slug")
    def _compute_liff_setup_url(self):
        for record in self:
            frontend_path = os.getenv("BACKEND_PATH")
            if not record.slug:
                record.liff_setup_url = False
                continue

            record.liff_setup_url = f"{frontend_path}/{record.slug}"

    def action_generate_redeem(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Generate Redeem QR",
            "res_model": "crm.user.point.redeem.generate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
            },
        }

    def action_generate_coupon(self):
        self.ensure_one()
        currency = self.currency_ids.filtered("is_default")[:1] or self.currency_ids[:1]
        return {
            "type": "ir.actions.act_window",
            "name": "Generate Coupon",
            "res_model": "partner.coupon",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "default_currency_id": currency.id,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)

        for partner in partners:
            default_currency = partner.currency_ids.filtered("is_default")
            if not default_currency:
                self.env["crm.partner.currency"].create({
                    "name": "point",
                    "is_default": True,
                    "partner_id": partner.id,
                })

        return partners

    @api.constrains("ui_background_color", "ui_button_color", "ui_text_color", "ui_button_text_color",  "ui_success_color", "ui_error_color")
    def _check_hex_color_fields(self):
        color_field_names = [
            name
            for name, field in self._fields.items()
            if name.endswith("_color") and field.type == "char"
        ]

        for record in self:
            for field_name in color_field_names:
                color = record[field_name]
                if color and not HEX_COLOR_PATTERN.match(color):
                    label = record._fields[field_name].string
                    raise ValidationError(
                        f"{label} must start with # followed by 6 hexadecimal digits."
                    )
