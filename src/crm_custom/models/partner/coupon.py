import secrets
import string
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PartnerCoupon(models.Model):
    _name = "partner.coupon"
    _description = "Partner Coupon"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", required=True, tracking=True)
    image = fields.Image(string="Image", max_width=1000, max_height=1000)
    prefix_code = fields.Char(string="Prefix Code", tracking=True)
    random_range = fields.Integer(string="Random Range", default=6, tracking=True)
    suffix_code = fields.Char(string="Suffix Code", tracking=True)
    value = fields.Float(string="Value", required=True, default=0, tracking=True)
    start_time = fields.Datetime(string="Start Date", default=fields.Datetime.now, required=True, tracking=True)
    code_expiry_interval = fields.Integer(
        string="Expiry Interval (Hours)",
        default=24,
        tracking=True,
    )
    end_time = fields.Datetime(string="End Date", tracking=True)
    redeemed_count = fields.Integer(
        string="Redeemed Count",
        compute="_compute_redeemed_count",
    )

    currency_id = fields.Many2one(
        "crm.partner.currency",
        string="Currency",
        required=True,
        ondelete="restrict",
    )

    partner_id = fields.Many2one(
        "partner",
        string="Partner",
        required=True,
        ondelete="cascade",
    )

    user_coupon_ids = fields.One2many(
        "crm.user.coupon",
        "coupon_id",
        string="User Coupons",
    )

    @api.depends("user_coupon_ids")
    def _compute_redeemed_count(self):
        for record in self:
            record.redeemed_count = len(record.user_coupon_ids)

    def redeem_for_user(self, user):
        self.ensure_one()
        self._check_can_redeem(user)

        now = fields.Datetime.now()
        expiration_date = False
        if self.code_expiry_interval:
            expiration_date = now + timedelta(hours=self.code_expiry_interval)

        point = self.env["crm.user.point"].sudo().create({
            "name": f"Redeem coupon: {self.name}",
            "value": self.value,
            "type": "burn",
            "given_date": now,
            "currency_id": self.currency_id.id,
            "user_id": user.id,
        })

        return self.env["crm.user.coupon"].sudo().create({
            "name": self.name,
            "code": self._generate_user_coupon_code(),
            "value": self.value,
            "acquired_date": now,
            "expiration_date": expiration_date,
            "currency_id": self.currency_id.id,
            "partner_id": self.partner_id.id,
            "coupon_id": self.id,
            "user_id": user.id,
            "point_id": point.id,
        })

    def _check_can_redeem(self, user):
        self.ensure_one()
        now = fields.Datetime.now()

        if user.partner_id != self.partner_id:
            raise ValidationError("User does not belong to this partner.")

        if self.currency_id.partner_id != self.partner_id:
            raise ValidationError("Coupon currency must belong to this partner.")

        if self.value <= 0:
            raise ValidationError("Coupon value must be greater than zero.")

        if self.random_range <= 0:
            raise ValidationError("Random range must be greater than zero.")

        if self.start_time and now < self.start_time:
            raise ValidationError("Coupon is not available yet.")

        if self.end_time and now > self.end_time:
            raise ValidationError("Coupon is expired.")

        if self._get_user_balance(user) < self.value:
            raise ValidationError("User does not have enough points.")

    def _get_user_balance(self, user):
        points = self.env["crm.user.point"].sudo().search([
            ("user_id", "=", user.id),
            ("currency_id", "=", self.currency_id.id),
        ])
        earn = sum(points.filtered(lambda point: point.type == "earn").mapped("value"))
        transfer = sum(points.filtered(lambda point: point.type == "transfer").mapped("value"))
        burn = sum(points.filtered(lambda point: point.type == "burn").mapped("value"))
        return earn - transfer - burn

    def _generate_user_coupon_code(self):
        alphabet = string.ascii_uppercase + string.digits
        prefix = self.prefix_code or ""
        suffix = self.suffix_code or ""

        for _attempt in range(20):
            random_part = "".join(secrets.choice(alphabet) for _index in range(self.random_range))
            code = f"{prefix}{random_part}{suffix}"
            if not self.env["crm.user.coupon"].sudo().search_count([("code", "=", code)]):
                return code

        raise ValidationError("Could not generate a unique coupon code.")

    @api.constrains("value", "random_range", "code_expiry_interval")
    def _check_coupon_numbers(self):
        for record in self:
            if record.value < 0:
                raise ValidationError("Coupon value must be zero or greater.")
            if record.random_range <= 0:
                raise ValidationError("Random range must be greater than zero.")
            if record.code_expiry_interval < 0:
                raise ValidationError("Expiry interval must be zero or greater.")

    @api.constrains("start_time", "end_time")
    def _check_coupon_dates(self):
        for record in self:
            if record.start_time and record.end_time and record.start_time > record.end_time:
                raise ValidationError("Start date must be before end date.")

    @api.constrains("currency_id", "partner_id")
    def _check_currency_partner(self):
        for record in self:
            if (
                record.currency_id
                and record.partner_id
                and record.currency_id.partner_id != record.partner_id
            ):
                raise ValidationError("Coupon currency must belong to this partner.")
