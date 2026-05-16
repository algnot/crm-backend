import json
import os
from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

from ....util.request import json_response


class CouponController(http.Controller):
    @http.route("/api/partner/<string:slug>/coupon", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def get_coupon(self, slug, **kwargs):
        partner_response = self._get_partner(slug)
        if partner_response["error"]:
            return partner_response["error"]

        now = fields.Datetime.now()
        coupons = request.env["partner.coupon"].sudo().search([
            ("partner_id", "=", partner_response["partner"].id),
            ("start_time", "<=", now),
            "|",
            ("end_time", "=", False),
            ("end_time", ">=", now),
        ])

        return json_response({
            "coupon": [self._serialize_partner_coupon(coupon) for coupon in coupons],
        })

    @http.route("/api/partner/<string:slug>/coupon/<int:coupon_id>", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def get_coupon_by_id(self, slug, coupon_id, **kwargs):
        coupon_response = self._get_coupon(slug, coupon_id)
        if coupon_response["error"]:
            return coupon_response["error"]

        return json_response({
            "coupon": self._serialize_partner_coupon(coupon_response["coupon"]),
        })

    @http.route("/api/partner/<string:slug>/coupon/<int:coupon_id>/redeem", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def redeem_coupon(self, slug, coupon_id, **kwargs):
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return json_response(
                {"error": "invalid_json", "message": "Invalid JSON body."},
                status=400,
            )

        coupon_response = self._get_coupon(slug, coupon_id)
        if coupon_response["error"]:
            return coupon_response["error"]

        user_response = self._get_user(
            coupon_response["partner"],
            payload.get("userId") or payload.get("line_user_id"),
        )
        if user_response["error"]:
            return user_response["error"]

        try:
            user_coupon = coupon_response["coupon"].sudo().redeem_for_user(user_response["user"])
        except ValidationError as error:
            return json_response(
                {"error": "coupon_not_allowed", "message": str(error)},
                status=400,
            )

        return json_response({
            "coupon": self._serialize_user_coupon(user_coupon),
        })

    @http.route("/api/partner/<string:slug>/user/<string:user_id>/coupon", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def get_user_coupon(self, slug, user_id, **kwargs):
        partner_response = self._get_partner(slug)
        if partner_response["error"]:
            return partner_response["error"]

        user_response = self._get_user(partner_response["partner"], user_id)
        if user_response["error"]:
            return user_response["error"]

        coupons = user_response["user"].coupon_ids.sorted(
            key=lambda coupon: coupon.acquired_date,
            reverse=True,
        )
        return json_response({
            "coupon": [self._serialize_user_coupon(coupon) for coupon in coupons],
        })

    @http.route("/api/partner/<string:slug>/user/<string:user_id>/coupon/<string:code>/use", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def use_user_coupon(self, slug, user_id, code, **kwargs):
        partner_response = self._get_partner(slug)
        if partner_response["error"]:
            return partner_response["error"]

        user_response = self._get_user(partner_response["partner"], user_id)
        if user_response["error"]:
            return user_response["error"]

        user_coupon = request.env["crm.user.coupon"].sudo().search([
            ("partner_id", "=", partner_response["partner"].id),
            ("user_id", "=", user_response["user"].id),
            ("code", "=", code),
        ], limit=1)
        if not user_coupon:
            return json_response(
                {"error": "coupon_not_found", "message": "Coupon not found."},
                status=404,
            )

        try:
            user_coupon.action_mark_used()
        except ValidationError as error:
            return json_response(
                {"error": "coupon_not_allowed", "message": str(error)},
                status=400,
            )

        return json_response({
            "coupon": self._serialize_user_coupon(user_coupon),
        })

    def _get_partner(self, slug):
        partner = request.env["partner"].sudo().search([("slug", "=", slug)], limit=1)
        if not partner:
            return {
                "partner": False,
                "error": json_response(
                    {"error": "partner_not_found", "message": "Partner not found."},
                    status=404,
                ),
            }

        return {
            "partner": partner,
            "error": False,
        }

    def _get_coupon(self, slug, coupon_id):
        partner_response = self._get_partner(slug)
        if partner_response["error"]:
            return {
                "partner": False,
                "coupon": False,
                "error": partner_response["error"],
            }

        coupon = request.env["partner.coupon"].sudo().search([
            ("id", "=", coupon_id),
            ("partner_id", "=", partner_response["partner"].id),
        ], limit=1)
        if not coupon:
            return {
                "partner": partner_response["partner"],
                "coupon": False,
                "error": json_response(
                    {"error": "coupon_not_found", "message": "Coupon not found."},
                    status=404,
                ),
            }

        return {
            "partner": partner_response["partner"],
            "coupon": coupon,
            "error": False,
        }

    def _get_user(self, partner, user_id):
        user = request.env["crm.user"].sudo().search([
            ("line_user_id", "=", user_id),
            ("partner_id", "=", partner.id),
        ], limit=1)
        if not user:
            return {
                "user": False,
                "error": json_response(
                    {"error": "user_not_found", "message": "User not found."},
                    status=404,
                ),
            }

        return {
            "user": user,
            "error": False,
        }

    def _serialize_partner_coupon(self, coupon):
        return {
            "id": coupon.id,
            "name": coupon.name,
            "image_url": f"{os.getenv('BACKEND_PATH')}/web/image/partner.coupon/{coupon.id}/image" if coupon.image else False,
            "value": coupon.value,
            "term_and_condition": coupon.term_and_condition,
            "start_time": fields.Datetime.to_string(coupon.start_time),
            "end_time": fields.Datetime.to_string(coupon.end_time),
            "code_expiry_interval": coupon.code_expiry_interval,
            "redeemed_count": coupon.redeemed_count,
            "currency": {
                "id": coupon.currency_id.id,
                "name": coupon.currency_id.name,
                "is_default": coupon.currency_id.is_default,
            },
        }

    def _serialize_user_coupon(self, coupon):
        return {
            "id": coupon.id,
            "name": coupon.name,
            "code": coupon.code,
            "value": coupon.value,
            "acquired_date": fields.Datetime.to_string(coupon.acquired_date),
            "expiration_date": fields.Datetime.to_string(coupon.expiration_date),
            "is_used": coupon.is_used,
            "used_date": fields.Datetime.to_string(coupon.used_date),
            "currency": {
                "id": coupon.currency_id.id,
                "name": coupon.currency_id.name,
                "is_default": coupon.currency_id.is_default,
            },
            "point": {
                "id": coupon.point_id.id,
                "value": coupon.point_id.value,
                "type": coupon.point_id.type,
            } if coupon.point_id else False,
        }
