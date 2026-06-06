from odoo.http import request


def get_bearer_token():
    authorization = request.httprequest.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return False


def get_portal_user_from_request():
    token = get_bearer_token()
    if not token:
        return request.env["res.users"]

    return request.env["partner.portal.token"].sudo().get_user_from_token(token)
