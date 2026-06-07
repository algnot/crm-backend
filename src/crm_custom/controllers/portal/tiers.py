import json

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from psycopg2 import IntegrityError

from ....util.portal_auth import get_portal_user_from_request
from ....util.request import json_response

ALLOWED_TIER_FIELDS = (
    "name",
    "code",
    "color",
    "icon",
    "convert_points",
    "min_spending",
    "max_spending",
    "is_show_in_ui",
)


class PortalTiersController(http.Controller):
    @http.route("/api/portal/tiers", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def list_tiers(self, **kwargs):
        user = get_portal_user_from_request()
        if not user:
            return json_response(
                {"error": "unauthorized", "message": "Invalid or expired token."},
                status=401,
            )

        tiers = request.env["partner.tier"].sudo().search([
            ("partner_id", "=", user.crm_partner_id.id),
        ], order="min_spending asc, id asc")

        return json_response({
            "tiers": [self._serialize_tier(tier) for tier in tiers],
        })

    @http.route("/api/portal/tiers/<int:tier_id>", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def get_tier(self, tier_id, **kwargs):
        user = get_portal_user_from_request()
        if not user:
            return json_response(
                {"error": "unauthorized", "message": "Invalid or expired token."},
                status=401,
            )

        tier_response = self._get_tier(user.crm_partner_id, tier_id)
        if tier_response["error"]:
            return tier_response["error"]

        return json_response({
            "tier": self._serialize_tier(tier_response["tier"]),
        })

    @http.route("/api/portal/tiers", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def create_tier(self, **kwargs):
        user = get_portal_user_from_request()
        if not user:
            return json_response(
                {"error": "unauthorized", "message": "Invalid or expired token."},
                status=401,
            )

        payload, parse_error = self._parse_payload()
        if parse_error:
            return parse_error

        vals = self._extract_tier_vals(payload)
        vals["partner_id"] = user.crm_partner_id.id

        try:
            tier = request.env["partner.tier"].sudo().create(vals)
        except ValidationError as error:
            request.env.cr.rollback()
            return json_response(
                {"error": "tier_not_allowed", "message": str(error)},
                status=400,
            )
        except IntegrityError:
            request.env.cr.rollback()
            return json_response(
                {
                    "error": "tier_not_allowed",
                    "message": "ข้อมูล Tier ไม่ถูกต้อง (code อาจซ้ำ หรือไม่ได้กรอกข้อมูลที่จำเป็น)",
                },
                status=400,
            )

        return json_response({
            "tier": self._serialize_tier(tier),
        }, status=201)

    @http.route("/api/portal/tiers/<int:tier_id>", type="http", auth="public", methods=["PUT"], csrf=False, cors="*")
    def update_tier(self, tier_id, **kwargs):
        user = get_portal_user_from_request()
        if not user:
            return json_response(
                {"error": "unauthorized", "message": "Invalid or expired token."},
                status=401,
            )

        tier_response = self._get_tier(user.crm_partner_id, tier_id)
        if tier_response["error"]:
            return tier_response["error"]

        payload, parse_error = self._parse_payload()
        if parse_error:
            return parse_error

        vals = self._extract_tier_vals(payload)
        if not vals:
            return json_response(
                {"error": "invalid_request", "message": "ไม่มีข้อมูลสำหรับแก้ไข"},
                status=400,
            )

        try:
            tier_response["tier"].sudo().write(vals)
        except ValidationError as error:
            request.env.cr.rollback()
            return json_response(
                {"error": "tier_not_allowed", "message": str(error)},
                status=400,
            )
        except IntegrityError:
            request.env.cr.rollback()
            return json_response(
                {
                    "error": "tier_not_allowed",
                    "message": "ข้อมูล Tier ไม่ถูกต้อง (code อาจซ้ำ หรือไม่ได้กรอกข้อมูลที่จำเป็น)",
                },
                status=400,
            )

        return json_response({
            "tier": self._serialize_tier(tier_response["tier"]),
        })

    def _parse_payload(self):
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return None, json_response(
                {"error": "invalid_json", "message": "Invalid JSON body."},
                status=400,
            )

        return payload, None

    def _extract_tier_vals(self, payload):
        return {
            field: payload[field]
            for field in ALLOWED_TIER_FIELDS
            if field in payload
        }

    def _get_tier(self, partner, tier_id):
        tier = request.env["partner.tier"].sudo().search([
            ("id", "=", tier_id),
            ("partner_id", "=", partner.id),
        ], limit=1)
        if not tier:
            return {
                "tier": False,
                "error": json_response(
                    {"error": "tier_not_found", "message": "ไม่พบ Tier ดังกล่าว"},
                    status=404,
                ),
            }

        return {
            "tier": tier,
            "error": False,
        }

    def _serialize_tier(self, tier):
        return {
            "id": tier.id,
            "code": tier.code,
            "name": tier.name,
            "color": tier.color,
            "image_url": tier.icon or False,
            "convert_points": tier.convert_points,
            "min_spending": tier.min_spending,
            "max_spending": tier.max_spending,
            "is_show_in_ui": tier.is_show_in_ui,
        }
