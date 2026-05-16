import json

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

from ....util.request import json_response


class RedeemPointController(http.Controller):
    @http.route("/api/partner/<string:slug>/redeem/<string:code>", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def get_redeem(self, slug, code, **kwargs):
        redeem_response = self._get_redeem(slug, code)
        if redeem_response["error"]:
            return redeem_response["error"]

        return json_response({
            "redeem": self._serialize_redeem(redeem_response["redeem"]),
        })

    @http.route("/api/partner/<string:slug>/redeem/<string:code>", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def redeem(self, slug, code, **kwargs):
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return json_response(
                {"error": "invalid_json", "message": "Invalid JSON body."},
                status=400,
            )

        redeem_response = self._get_redeem(slug, code)
        if redeem_response["error"]:
            return redeem_response["error"]

        user_id = payload.get("userId") or payload.get("line_user_id")
        user = request.env["crm.user"].sudo().search(
            [
                ("line_user_id", "=", user_id),
                ("partner_id", "=", redeem_response["partner"].id),
            ],
            limit=1,
        )
        if not user:
            return json_response(
                {"error": "user_not_found", "message": "User not found."},
                status=404,
            )

        try:
            point = redeem_response["redeem"].sudo().redeem_for_user(user)
        except ValidationError as error:
            return json_response(
                {"error": "redeem_not_allowed", "message": str(error)},
                status=400,
            )

        return json_response({
            "point": {
                "id": point.id,
                "name": point.name,
                "value": point.value,
                "type": point.type,
                "given_date": fields.Datetime.to_string(point.given_date),
                "currency": {
                    "id": point.currency_id.id,
                    "name": point.currency_id.name,
                    "is_default": point.currency_id.is_default,
                },
            },
        })

    def _get_redeem(self, slug, code):
        partner = request.env["partner"].sudo().search(
            [("slug", "=", slug)],
            limit=1,
        )
        if not partner:
            return {
                "partner": False,
                "redeem": False,
                "error": json_response(
                    {"error": "partner_not_found", "message": "Partner not found."},
                    status=404,
                ),
            }

        redeem = request.env["crm.partner.point.redeem"].sudo().search(
            [
                ("partner_id", "=", partner.id),
                ("code", "=", code),
            ],
            limit=1,
        )
        if not redeem:
            return {
                "partner": partner,
                "redeem": False,
                "error": json_response(
                    {"error": "redeem_not_found", "message": "Redeem QR not found."},
                    status=404,
                ),
            }

        return {
            "partner": partner,
            "redeem": redeem,
            "error": False,
        }

    def _serialize_redeem(self, redeem):
        return {
            "code": redeem.code,
            "name": redeem.name,
            "value": redeem.value,
            "type": redeem.type,
            "limit_per_user": redeem.limit_per_user,
            "limit_per_qr": redeem.limit_per_qr,
            "redeemed_count": redeem.redeemed_count,
            "expiration_date": fields.Datetime.to_string(redeem.expiration_date),
            "active": redeem.active,
            "currency": {
                "id": redeem.currency_id.id,
                "name": redeem.currency_id.name,
                "is_default": redeem.currency_id.is_default,
            },
        }
