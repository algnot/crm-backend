import os

from odoo import http
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
            "id": partner.id,
            "name": partner.name,
            "slug": partner.slug,
            "description": partner.description,
            "active": partner.active,
            "logo_url": self._get_logo_url(partner),
            "line": {
                "liff_id": partner.partner_line_liff_id,
            },
            "ui": self._serialize_ui_config(partner),
        }

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

    def _get_logo_url(self, partner):
        if not partner.logo:
            return False

        logo_path = f"/web/image/partner/{partner.id}/logo"
        backend_path = os.getenv("BACKEND_PATH")

        if backend_path:
            return f"{backend_path.rstrip('/')}{logo_path}"

        return logo_path
