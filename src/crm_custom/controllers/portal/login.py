import json

from odoo import fields, http
from odoo.exceptions import AccessDenied
from odoo.http import request

from ....util.portal_auth import get_portal_user_from_request
from ....util.request import json_response


class PortalLoginController(http.Controller):
    @http.route( "/api/portal/login", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def portal_login(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return json_response(
                {"error": "invalid_json", "message": "Invalid JSON body."},
                status=400,
            )

        email = (payload.get("email") or payload.get("login") or "").strip().lower()
        password = payload.get("password") or ""
        if not email or not password:
            return json_response(
                {"error": "invalid_request", "message": "Email and password are required."},
                status=400,
            )

        credential = {
            "login": email,
            "password": password,
            "type": "password",
        }

        try:
            auth_info = request.env["res.users"].sudo().authenticate(
                request.env.cr.dbname,
                credential,
                {"interactive": False},
            )
        except AccessDenied:
            return json_response(
                {"error": "invalid_credentials", "message": "Invalid email or password."},
                status=401,
            )

        user = request.env["res.users"].sudo().browse(auth_info["uid"])

        if not user.is_partner_portal or not user.crm_partner_id:
            return json_response(
                {
                    "error": "portal_access_denied",
                    "message": "This account cannot access the partner portal.",
                },
                status=403,
            )

        internal_group = request.env.ref("base.group_user")
        if internal_group in user.groups_id:
            return json_response(
                {
                    "error": "portal_access_denied",
                    "message": "Internal users must use Odoo login.",
                },
                status=403,
            )

        portal_token = request.env["partner.portal.token"].sudo().create_for_user(user)
        partner = user.crm_partner_id

        return json_response({
            "token": portal_token.token,
            "expires_at": fields.Datetime.to_string(portal_token.expires_at),
            "user": {
                "name": user.name,
                "email": user.login,
            },
            "partner": {
                "name": partner.name,
                "slug": partner.slug,
                "logo_url": partner.logo,
            },
        })

    @http.route( "/api/portal/me", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def portal_me(self, **kwargs):
        user = get_portal_user_from_request()
        if not user:
            return json_response(
                {"error": "unauthorized", "message": "Invalid or expired token."},
                status=401,
            )

        partner = user.crm_partner_id
        return json_response({
            "user": {
                "name": user.name,
                "email": user.login,
            },
            "partner": {
                "name": partner.name,
                "slug": partner.slug,
                "logo_url": partner.logo,
            },
        })
