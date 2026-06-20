import json

from odoo import http
from odoo.http import request
from ....util.request import json_response


class GetOrCreateUserController(http.Controller):

    @http.route("/api/partner/<string:slug>/user", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def get_or_create_user(self, slug, **kwargs):
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return json_response(
                {"error": "invalid_json", "message": "Invalid JSON body."},
                status=400,
            )

        partner = request.env["partner"].sudo().search(
            [
                ("slug", "=", slug),
            ],
            limit=1,
        )

        if not partner:
            return json_response(
                {
                    "error": "partner_not_found",
                    "message": "ไม่พบ Client ดังกล่าวโปรดติดต่อเจ้าหน้าที่",
                },
                status=404,
            )

        display_name = payload.get("displayName")
        picture_url = payload.get("pictureUrl")
        user_id = payload.get("userId")
        user = request.env["crm.user"].search(
            [
                ("line_user_id", "=", user_id),
                ("partner_id", "=", partner.id),
            ],
            limit=1,
        )

        if not user:
            user = request.env["crm.user"].sudo().create({
                "display_name": display_name,
                "picture_url": picture_url,
                "line_user_id": user_id,
                "partner_id": partner.id,
            })

        else:
            user.sudo().write({
                "display_name": display_name,
                "picture_url": picture_url,
            })
            user = request.env["crm.user"].sudo().browse(user.id)

        user._update_tier()
        return json_response(self._serialize_user_response(user, partner))


    def _serialize_user_response(self, user, partner):
        force_verify_phone = not user.is_phone_verified and partner.ui_crm_required_phone
        force_verify_email = not user.is_email_verified and partner.ui_crm_required_email

        has_sms_credit = request.env["crm.otp"].has_sms_otp_credit()
        if not has_sms_credit:
            force_verify_phone = False

        return {
            "display_name": user.display_name,
            "picture_url": user.picture_url,
            "line_user_id": user.line_user_id,
            "email": user.email,
            "phone": user.phone,
            "force_verify_phone": force_verify_phone,
            "force_verify_email": force_verify_email,
            "birth_date": user.birth_date,
            "gender": user.gender,
            "tier": self._serialize_user_tier(user.tier_id),
        }

    def _serialize_user_tier(self, tier):
        if not tier:
            return False

        return {
            "code": tier.code,
            "name": tier.name,
            "min_spending": tier.min_spending,
            "max_spending": tier.max_spending,
            "color": tier.color,
            "image_url": tier.icon or False,
        }
