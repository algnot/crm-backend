from html import escape

from odoo import api, fields, models


class User(models.Model):
    _name = "crm.user"
    _description = "User"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _sql_constraints = [
        ("user_line_user_id_uniq", "unique(line_user_id, partner_id)", "LINE user ID and Partner combination must be unique."),
    ]

    display_name = fields.Char(string="Display Name", tracking=True, required=True)
    picture_url = fields.Char(string="Picture URL", tracking=True, required=True)
    picture_preview = fields.Html(
        string="Picture",
        compute="_compute_picture_preview",
        sanitize=False,
    )
    line_user_id = fields.Char(string="LINE UUID", tracking=True, required=True)

    email = fields.Char(string="Email", tracking=True)
    is_email_verified = fields.Boolean(string="Is Email Verified", tracking=True)

    phone = fields.Char(string="Phone", tracking=True)
    is_phone_verified = fields.Boolean(string="Is Phone Verified", tracking=True)

    birth_date = fields.Date(string="Birth Date", tracking=True)
    gender = fields.Selection([
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other")
    ], string="Gender", tracking=True)

    active = fields.Boolean(string="Active", default=True, tracking=True)

    partner_id = fields.Many2one(
        "partner",
        string="Partner",
        required=True,
        ondelete="cascade",
    )

    point_ids = fields.One2many(
        "crm.user.point",
        "user_id",
        string="Points",
    )

    coupon_ids = fields.One2many(
        "crm.user.coupon",
        "user_id",
        string="Coupons",
    )

    @api.depends("picture_url")
    def _compute_picture_preview(self):
        for record in self:
            if not record.picture_url:
                record.picture_preview = False
                continue

            picture_url = escape(record.picture_url, quote=True)
            record.picture_preview = (
                f'<img src="{picture_url}" '
                'style="width:128px;height:128px;object-fit:cover;border-radius:50%;" '
                'alt="User picture"/>'
            )
