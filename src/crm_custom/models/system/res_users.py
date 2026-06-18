from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    crm_partner_id = fields.Many2one(
        "partner",
        string="CRM Partner",
        ondelete="restrict",
    )
    is_partner_portal = fields.Boolean(string="Partner Portal User", default=False)

    @api.constrains("is_partner_portal", "groups_id")
    def _check_partner_portal_not_internal(self):
        internal_group = self.env.ref("base.group_user", raise_if_not_found=False)
        if not internal_group:
            return

        for user in self.filtered("is_partner_portal"):
            if internal_group in user.groups_id:
                raise ValidationError(
                    "Partner portal users cannot have Internal User access."
                )

    @api.constrains("is_partner_portal", "crm_partner_id")
    def _check_partner_portal_partner(self):
        for user in self.filtered("is_partner_portal"):
            if not user.crm_partner_id:
                raise ValidationError("Partner portal users must be linked to a partner.")

    @api.model
    def create_partner_portal_user(self, partner, name, email, password):
        partner_portal_group = self.env.ref("crm_custom.group_partner_portal")
        public_group = self.env.ref("base.group_public")
        login = (email or "").strip().lower()
        if not login:
            raise ValidationError("Email is required.")

        existing = self.search([("login", "=", login)], limit=1)
        if existing:
            raise ValidationError(f"Login '{login}' is already used.")

        return self.with_context(no_reset_password=True).create({
            "name": name,
            "login": login,
            "email": login,
            "password": password,
            "crm_partner_id": partner.id,
            "is_partner_portal": True,
            "groups_id": [(6, 0, [partner_portal_group.id, public_group.id])],
            "active": True,
        })

    @api.model
    def fix_partner_portal_groups(self):
        partner_portal_group = self.env.ref("crm_custom.group_partner_portal", raise_if_not_found=False)
        public_group = self.env.ref("base.group_public", raise_if_not_found=False)
        if not partner_portal_group or not public_group:
            return

        for user in self.sudo().search([("is_partner_portal", "=", True)]):
            groups_to_add = []
            if partner_portal_group not in user.groups_id:
                groups_to_add.append((4, partner_portal_group.id))
            if public_group not in user.groups_id:
                groups_to_add.append((4, public_group.id))
            if groups_to_add:
                user.write({"groups_id": groups_to_add})
