import os

from odoo import fields, http
from odoo.http import request
from ....util.request import json_response


class PartnerConfigController(http.Controller):

    @http.route("/api/partner/<string:slug>", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def get_partner_config(self, slug, **kwargs):
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
                    "message": "ไม่พบ Client ดังกล่าวในระบบ โปรดติดต่อเจ้าหน้าที่",
                },
                status=404,
            )

        return json_response(self._serialize_partner_config(partner))

    def _serialize_partner_config(self, partner):
        return {
            "name": partner.name,
            "slug": partner.slug,
            "description": partner.description,
            "active": partner.active,
            "logo_url": self._get_logo_url(partner),
            "line": {
                "liff_id": partner.partner_line_liff_id,
            },
            "ui": self._serialize_ui_config(partner),
            "ads": self._serialize_active_ads(partner),
            "tier": self._serialize_tier(partner),
        }

    def _serialize_tier(self, partner):
        result = []
        tiers = partner.tier_ids

        for tier in tiers:
            tier_config = {
                "code": tier.code,
                "name": tier.name,
                "min_spending": tier.min_spending,
                "max_spending": tier.max_spending,
                "color": tier.color,
                "image_url": self._get_image_url("partner.tier", tier.id, "image"),
            }
            result.append(tier_config)

        return result

    def _serialize_ui_config(self, partner):
        ui_config = {}

        for field_name, field in partner._fields.items():
            if not field_name.startswith("ui_"):
                continue

            value = partner[field_name]
            key = field_name.removeprefix("ui_")

            if field_name == "ui_custom_field_ids":
                value = self._serialize_custom_fields(value)
                key = "ui_custom_fields"

            if value and field_name == "ui_banner":
                value = self._get_image_url("partner", partner.id, field_name)

            ui_config[key] = value

        return ui_config

    def _serialize_custom_fields(self, custom_fields):
        return [
            {
                "key": custom_field.key,
                "value": custom_field.value,
            }
            for custom_field in custom_fields
        ]

    def _serialize_active_ads(self, partner):
        now = fields.Datetime.now()
        ads = request.env["partner.ads"].sudo().search([
            ("partner_id", "=", partner.id),
            ("active", "=", True),
            ("start_date", "<=", now),
            ("end_date", ">=", now),
        ])

        return [self._serialize_ad(ad) for ad in ads]

    def _serialize_ad(self, ad):
        return {
            "id": ad.id,
            "action": ad.action,
            "image_url": self._get_ad_image_url(ad),
            "start_date": fields.Datetime.to_string(ad.start_date),
            "end_date": fields.Datetime.to_string(ad.end_date),
        }

    def _get_image_url(self, model_name, record_id, field_name):
        image_path = f"/web/image/{model_name}/{record_id}/{field_name}"
        backend_path = os.getenv("BACKEND_PATH")

        if backend_path:
            return f"{backend_path.rstrip('/')}{image_path}"

        return image_path

    def _get_logo_url(self, partner):
        if not partner.logo:
            return False

        return self._get_image_url("partner", partner.id, "logo")

    def _get_ad_image_url(self, ad):
        if not ad.image:
            return False

        return self._get_image_url("partner.ads", ad.id, "image")
