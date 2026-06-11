from odoo import fields, http
from odoo.http import request

from ....util.portal_auth import get_portal_user_from_request
from ....util.request import json_response


class PortalCouponsController(http.Controller):
    @http.route("/api/portal/coupons", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def list_coupons(self, **kwargs):
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
            domain.append(("name", "ilike", search_term))

        limit = self._parse_int(kwargs.get("limit"))
        offset = self._parse_int(kwargs.get("offset")) or 0

        coupons = request.env["partner.coupon"].sudo().search(
            domain,
            limit=limit,
            offset=offset,
            order="create_date desc",
        )
        total = request.env["partner.coupon"].sudo().search_count(domain)

        return json_response({
            "coupons": [self._serialize_coupon(coupon) for coupon in coupons],
            "total": total,
        })

    def _parse_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _serialize_coupon(self, coupon):
        return {
            "id": coupon.id,
            "name": coupon.name,
            "image_url": coupon.image or False,
            "value": coupon.value,
            "code_source": coupon.code_source,
            "prefix_code": coupon.prefix_code or False,
            "suffix_code": coupon.suffix_code or False,
            "random_range": coupon.random_range,
            "code_expiry_interval": coupon.code_expiry_interval,
            "term_and_condition": coupon.term_and_condition or False,
            "start_time": fields.Datetime.to_string(coupon.start_time),
            "end_time": fields.Datetime.to_string(coupon.end_time),
            "total_code_count": coupon.total_code_count,
            "available_code_count": coupon.available_code_count,
            "redeemed_count": coupon.redeemed_count,
            "used_code_count": coupon.used_code_count,
            "currency": {
                "id": coupon.currency_id.id,
                "name": coupon.currency_id.name,
                "is_default": coupon.currency_id.is_default,
            },
        }
