from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UserCoupon(models.Model):
    _name = "crm.user.coupon"
    _description = "User Coupon"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _sql_constraints = [
        ("user_coupon_code_uniq", "unique(code)", "Coupon code must be unique."),
    ]

    name = fields.Char(string="Name", required=True, tracking=True)
    admin_note = fields.Text(string="Admin Note", tracking=True)
    code = fields.Char(string="Code", required=True, readonly=True, copy=False, tracking=True)
    value = fields.Float(string="Value", required=True, readonly=True, tracking=True)
    acquired_date = fields.Datetime(string="Acquired Date", required=True, readonly=True, tracking=True)
    expiration_date = fields.Datetime(string="Expiration Date", readonly=True, tracking=True)
    is_used = fields.Boolean(string="Used", default=False, tracking=True)
    used_date = fields.Datetime(string="Used Date", readonly=True, tracking=True)

    user_id = fields.Many2one(
        "crm.user",
        string="User",
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "partner",
        string="Partner",
        required=True,
        ondelete="cascade",
    )
    coupon_id = fields.Many2one(
        "partner.coupon",
        string="Partner Coupon",
        required=True,
        ondelete="restrict",
    )
    currency_id = fields.Many2one(
        "crm.partner.currency",
        string="Currency",
        required=True,
        ondelete="restrict",
    )
    point_id = fields.Many2one(
        "crm.user.point",
        string="Point Transaction",
        readonly=True,
        ondelete="restrict",
    )
    coupon_code_id = fields.Many2one(
        "partner.coupon.code",
        string="Coupon Code",
        readonly=True,
        ondelete="set null",
    )
    point_redeem_id = fields.Many2one(
        "crm.partner.point.redeem",
        string="Point Redeem",
        readonly=True,
        ondelete="set null",
    )

    member_reward_id = fields.Many2one(
        "partner.member.reward",
        string="Member Reward",
        readonly=True,
        ondelete="set null",
    )
    member_reward_event = fields.Selection(
        [
            ("join", "Join"),
            ("tier_promotion", "Tier Promotion"),
        ],
        string="Member Reward Event",
        readonly=True,
    )
    member_reward_tier_id = fields.Many2one(
        "partner.tier",
        string="Member Reward Tier",
        readonly=True,
        ondelete="set null",
    )

    def action_mark_used(self):
        now = fields.Datetime.now()
        for record in self:
            if record.is_used:
                continue
            if record.expiration_date and now > record.expiration_date:
                raise ValidationError("Coupon หมดอายุแล้ว")
            record.write({
                "is_used": True,
                "used_date": now,
            })
            if record.coupon_code_id:
                record.coupon_code_id.write({
                    "state": "used",
                    "used_by_user_id": record.user_id.id,
                    "used_date": now,
                })

    @api.constrains("currency_id", "partner_id", "coupon_id", "user_id")
    def _check_partner_consistency(self):
        for record in self:
            if record.user_id and record.user_id.partner_id != record.partner_id:
                raise ValidationError("User coupon partner must match the user's partner.")
            if record.coupon_id and record.coupon_id.partner_id != record.partner_id:
                raise ValidationError("User coupon partner must match the coupon partner.")
            if record.currency_id and record.currency_id.partner_id != record.partner_id:
                raise ValidationError("User coupon currency must belong to this partner.")
