import json

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

from ....util.portal_auth import get_portal_user_from_request
from ....util.request import json_response


class PortalUsersController(http.Controller):
    @http.route("/api/portal/users", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def list_users(self, **kwargs):
        user = get_portal_user_from_request()
        if not user:
            return json_response(
                {"error": "unauthorized", "message": "Invalid or expired token."},
                status=401,
            )

        partner = user.crm_partner_id
        domain = [("partner_id", "=", partner.id)]

        search_term = (kwargs.get("search") or "").strip()
        if search_term:
            domain += [
                "|", "|", "|",
                ("display_name", "ilike", search_term),
                ("line_user_id", "ilike", search_term),
                ("email", "ilike", search_term),
                ("phone", "ilike", search_term),
            ]

        limit = self._parse_int(kwargs.get("limit"))
        offset = self._parse_int(kwargs.get("offset")) or 0

        users = request.env["crm.user"].sudo().search(
            domain,
            limit=limit,
            offset=offset,
            order="create_date desc",
        )
        total = request.env["crm.user"].sudo().search_count(domain)

        return json_response({
            "users": [self._serialize_user(user) for user in users],
            "total": total,
        })

    @http.route("/api/portal/users/<int:user_id>", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def get_user(self, user_id, **kwargs):
        user = get_portal_user_from_request()
        if not user:
            return json_response(
                {"error": "unauthorized", "message": "Invalid or expired token."},
                status=401,
            )

        user_response = self._get_user(user.crm_partner_id, user_id)
        if user_response["error"]:
            return user_response["error"]

        return json_response({
            "user": self._serialize_user(user_response["user"]),
        })

    @http.route("/api/portal/users/<int:user_id>/point", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def adjust_user_point(self, user_id, **kwargs):
        user = get_portal_user_from_request()
        if not user:
            return json_response(
                {"error": "unauthorized", "message": "Invalid or expired token."},
                status=401,
            )

        partner = user.crm_partner_id

        user_response = self._get_user(partner, user_id)
        if user_response["error"]:
            return user_response["error"]

        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return json_response(
                {"error": "invalid_json", "message": "Invalid JSON body."},
                status=400,
            )

        currency_response = self._get_currency(partner, payload.get("currency_id"))
        if currency_response["error"]:
            return currency_response["error"]

        try:
            point = user_response["user"].adjust_point(
                payload.get("value") or 0,
                payload.get("type"),
                currency_response["currency"],
                payload.get("note"),
                payload.get("expiration_date") or None,
            )
        except ValidationError as error:
            request.env.cr.rollback()
            return json_response(
                {"error": "point_not_allowed", "message": str(error)},
                status=400,
            )

        return json_response({
            "point": self._serialize_point(point),
        }, status=201)

    def _parse_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _get_user(self, partner, user_id):
        user = request.env["crm.user"].sudo().search([
            ("id", "=", user_id),
            ("partner_id", "=", partner.id),
        ], limit=1)
        if not user:
            return {
                "user": False,
                "error": json_response(
                    {"error": "user_not_found", "message": "ไม่พบผู้ใช้งานดังกล่าว"},
                    status=404,
                ),
            }

        return {
            "user": user,
            "error": False,
        }

    def _get_currency(self, partner, currency_id):
        if currency_id:
            currency = request.env["crm.partner.currency"].sudo().search([
                ("id", "=", currency_id),
                ("partner_id", "=", partner.id),
            ], limit=1)
            if not currency:
                return {
                    "currency": False,
                    "error": json_response(
                        {"error": "currency_not_found", "message": "ไม่พบ Currency ดังกล่าว"},
                        status=404,
                    ),
                }
            return {"currency": currency, "error": False}

        currency = (
            partner.currency_ids.filtered("is_default")[:1]
            or partner.currency_ids[:1]
        )
        if not currency:
            return {
                "currency": False,
                "error": json_response(
                    {"error": "currency_not_found", "message": "Partner ยังไม่มี Currency"},
                    status=404,
                ),
            }
        return {"currency": currency, "error": False}

    def _serialize_user(self, user):
        return {
            "id": user.id,
            "display_name": user.display_name,
            "picture_url": user.picture_url,
            "line_user_id": user.line_user_id,
            "email": user.email,
            "is_email_verified": user.is_email_verified,
            "phone": user.phone,
            "is_phone_verified": user.is_phone_verified,
            "birth_date": user.birth_date,
            "gender": user.gender,
            "tier": self._serialize_tier(user.tier_id),
            "points": self._serialize_balances(user),
            "create_date": fields.Datetime.to_string(user.create_date),
        }

    def _serialize_tier(self, tier):
        if not tier:
            return False

        return {
            "code": tier.code,
            "name": tier.name,
        }

    def _serialize_balances(self, user):
        balances = []
        for currency in user.partner_id.currency_ids:
            balances.append({
                "currency": {
                    "id": currency.id,
                    "name": currency.name,
                    "is_default": currency.is_default,
                    "is_total_spending": currency.is_total_spending,
                },
                "balance": user._get_currency_balance(currency),
            })
        return balances

    def _serialize_point(self, point):
        return {
            "id": point.id,
            "name": point.name,
            "value": point.value,
            "type": point.type,
            "admin_note": point.admin_note or False,
            "given_date": fields.Datetime.to_string(point.given_date),
            "expiration_date": fields.Datetime.to_string(point.expiration_date),
            "currency": {
                "id": point.currency_id.id,
                "name": point.currency_id.name,
                "is_default": point.currency_id.is_default,
            },
        }
