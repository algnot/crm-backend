from odoo import api, fields, models
from odoo.exceptions import AccessDenied, ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    PORTAL_LOGIN_SEPARATOR = ":"
    PORTAL_ROLE_ADMIN = "admin"
    PORTAL_ROLE_OPERATION = "operation"
    PORTAL_ROLES = (PORTAL_ROLE_ADMIN, PORTAL_ROLE_OPERATION)

    crm_partner_id = fields.Many2one(
        "partner",
        string="CRM Partner",
        ondelete="restrict",
    )
    is_partner_portal = fields.Boolean(string="Partner Portal User", default=False)
    portal_role = fields.Selection(
        selection=[
            (PORTAL_ROLE_ADMIN, "Admin"),
            (PORTAL_ROLE_OPERATION, "Operation"),
        ],
        string="Portal Role",
        default=PORTAL_ROLE_ADMIN,
    )

    @api.model
    def _normalize_portal_email(self, email):
        return (email or "").strip().lower()

    @api.model
    def _validate_portal_role(self, role):
        if role not in self.PORTAL_ROLES:
            raise ValidationError("Portal role must be admin or operation.")
        return role

    def is_portal_admin(self):
        self.ensure_one()
        return (self.portal_role or self.PORTAL_ROLE_ADMIN) == self.PORTAL_ROLE_ADMIN

    def _check_partner_admin_exists(self, partner, exclude_user=None):
        domain = [
            ("is_partner_portal", "=", True),
            ("crm_partner_id", "=", partner.id),
            ("portal_role", "=", self.PORTAL_ROLE_ADMIN),
            ("active", "=", True),
        ]
        if exclude_user:
            domain.append(("id", "!=", exclude_user.id))
        if not self.search_count(domain):
            raise ValidationError("ต้องมี admin อย่างน้อย 1 คน")

    @api.model
    def migrate_portal_user_roles(self):
        for user in self.sudo().search([("is_partner_portal", "=", True)]):
            if not user.portal_role:
                user.write({"portal_role": self.PORTAL_ROLE_ADMIN})

    @api.model
    def _make_portal_login(self, partner, email):
        normalized_email = self._normalize_portal_email(email)
        if not partner or not partner.slug:
            raise ValidationError("Partner slug is required for portal users.")
        if not normalized_email:
            raise ValidationError("Email is required.")
        return f"{partner.slug}{self.PORTAL_LOGIN_SEPARATOR}{normalized_email}"

    @api.model
    def _find_portal_user(self, partner, email):
        login = self._make_portal_login(partner, email)
        return self.sudo().search([
            ("login", "=", login),
            ("is_partner_portal", "=", True),
            ("crm_partner_id", "=", partner.id),
        ], limit=1)

    def _get_portal_email(self):
        self.ensure_one()
        if self.email:
            return self.email
        login = self.login or ""
        if self.PORTAL_LOGIN_SEPARATOR in login:
            return login.split(self.PORTAL_LOGIN_SEPARATOR, 1)[1]
        return login

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

    @api.constrains("is_partner_portal", "crm_partner_id", "email")
    def _check_portal_email_unique_per_partner(self):
        for user in self.filtered(lambda record: record.is_partner_portal and record.crm_partner_id):
            email = self._normalize_portal_email(user.email or user._get_portal_email())
            if not email:
                raise ValidationError("Email is required.")

            duplicate = self.search([
                ("id", "!=", user.id),
                ("is_partner_portal", "=", True),
                ("crm_partner_id", "=", user.crm_partner_id.id),
                ("email", "=", email),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"Email '{email}' is already used for this partner."
                )

    @api.model
    def create_partner_portal_user(self, partner, name, email, password, portal_role=None):
        partner_portal_group = self.env.ref("crm_custom.group_partner_portal")
        public_group = self.env.ref("base.group_public")
        normalized_email = self._normalize_portal_email(email)
        if not normalized_email:
            raise ValidationError("Email is required.")
        portal_role = self._validate_portal_role(portal_role or self.PORTAL_ROLE_ADMIN)

        existing = self._find_portal_user(partner, normalized_email)
        if existing:
            raise ValidationError(
                f"Email '{normalized_email}' is already used for partner '{partner.name}'."
            )

        login = self._make_portal_login(partner, normalized_email)

        return self.with_context(no_reset_password=True).create({
            "name": name,
            "login": login,
            "email": normalized_email,
            "password": password,
            "crm_partner_id": partner.id,
            "is_partner_portal": True,
            "portal_role": portal_role,
            "groups_id": [(6, 0, [partner_portal_group.id, public_group.id])],
            "active": True,
        })

    def update_partner_portal_user(
        self,
        name=None,
        portal_role=None,
        active=None,
        password=None,
    ):
        self.ensure_one()
        self._ensure_portal_user()

        vals = {}
        if name is not None:
            cleaned_name = name.strip()
            if not cleaned_name:
                raise ValidationError("Name is required.")
            vals["name"] = cleaned_name

        if portal_role is not None:
            vals["portal_role"] = self._validate_portal_role(portal_role)

        if active is not None:
            vals["active"] = bool(active)

        if password:
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters.")
            vals["password"] = password

        if not vals:
            return self

        losing_admin = (
            self.portal_role == self.PORTAL_ROLE_ADMIN
            and (
                vals.get("portal_role") == self.PORTAL_ROLE_OPERATION
                or vals.get("active") is False
            )
        )
        if losing_admin:
            self._check_partner_admin_exists(self.crm_partner_id, exclude_user=self)

        self.write(vals)
        return self

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

    @api.model
    def migrate_portal_user_logins(self):
        portal_users = self.sudo().search([("is_partner_portal", "=", True)])
        grouped_users = {}

        for user in portal_users:
            partner = user.crm_partner_id
            if not partner or not partner.slug:
                continue

            email = self._normalize_portal_email(user.email or user._get_portal_email())
            if not email:
                continue

            grouped_users.setdefault((partner.id, email), []).append(user)

        for (partner_id, email), users in grouped_users.items():
            partner = self.env["partner"].browse(partner_id)
            scoped_login = self._make_portal_login(partner, email)

            users_sorted = sorted(
                users,
                key=lambda record: (
                    record.login == scoped_login,
                    record.active,
                    record.id,
                ),
                reverse=True,
            )
            primary_user = users_sorted[0]
            duplicate_users = users_sorted[1:]

            for duplicate_user in duplicate_users:
                duplicate_login = f"{scoped_login}:archived:{duplicate_user.id}"
                duplicate_vals = {"email": email}
                if duplicate_user.login != duplicate_login:
                    duplicate_vals["login"] = duplicate_login
                if duplicate_user.active:
                    duplicate_vals["active"] = False
                if len(duplicate_vals) > 1 or duplicate_user.active:
                    duplicate_user.write(duplicate_vals)

            primary_vals = {}
            if primary_user.email != email:
                primary_vals["email"] = email
            if primary_user.login != scoped_login:
                primary_vals["login"] = scoped_login
            if primary_vals:
                primary_user.write(primary_vals)

    def _validate_portal_password(self, password):
        self.ensure_one()
        if not password:
            return False

        credential = {
            "login": self.login,
            "password": password,
            "type": "password",
        }
        try:
            auth_info = self.env["res.users"].sudo().authenticate(
                self.env.cr.dbname,
                credential,
                {"interactive": False},
            )
            return auth_info["uid"] == self.id
        except AccessDenied:
            return False

    def _ensure_portal_user(self):
        self.ensure_one()
        if not self.is_partner_portal or not self.crm_partner_id:
            raise ValidationError("This account is not a partner portal user.")

    def update_portal_profile(self, name=None, email=None, current_password=None, password_verified=False):
        self.ensure_one()
        self._ensure_portal_user()

        vals = {}
        if name is not None:
            cleaned_name = name.strip()
            if not cleaned_name:
                raise ValidationError("Name is required.")
            vals["name"] = cleaned_name

        if email is not None:
            if not password_verified and not self._validate_portal_password(current_password):
                raise ValidationError("Current password is incorrect.")

            normalized_email = self._normalize_portal_email(email)
            if not normalized_email:
                raise ValidationError("Email is required.")

            duplicate = self._find_portal_user(self.crm_partner_id, normalized_email)
            if duplicate and duplicate.id != self.id:
                raise ValidationError(
                    f"Email '{normalized_email}' is already used for this partner."
                )

            vals.update({
                "email": normalized_email,
                "login": self._make_portal_login(self.crm_partner_id, normalized_email),
            })

        if vals:
            self.write(vals)

        return self

    def update_portal_password(self, current_password, new_password, password_verified=False):
        self.ensure_one()
        self._ensure_portal_user()

        if len(new_password or "") < 8:
            raise ValidationError("Password must be at least 8 characters.")
        if not password_verified and not self._validate_portal_password(current_password):
            raise ValidationError("Current password is incorrect.")

        self.write({"password": new_password})
        self.env["partner.portal.token"].sudo().revoke_for_user(self)
        return self

    def update_portal_account(
        self,
        name=None,
        email=None,
        current_password=None,
        new_password=None,
    ):
        self.ensure_one()
        self._ensure_portal_user()

        needs_password = email is not None or new_password
        password_verified = False
        if needs_password:
            if not current_password:
                raise ValidationError("Current password is required.")
            password_verified = self._validate_portal_password(current_password)
            if not password_verified:
                raise ValidationError("Current password is incorrect.")

        self.update_portal_profile(
            name=name,
            email=email,
            current_password=current_password,
            password_verified=password_verified,
        )
        if new_password:
            self.update_portal_password(
                current_password,
                new_password,
                password_verified=password_verified,
            )
        return self
